"""
Caching layer for Discogs API data to avoid repeated API calls
"""
import json
import pickle
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib

from config.settings import DATA_CACHE_DIR
from .discogs_client import AlbumData


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata"""
    key: str
    data: Any
    created_at: datetime
    expires_at: Optional[datetime]
    hit_count: int = 0
    data_size: int = 0


class SQLiteCache:
    """SQLite-based cache for Discogs API data"""
    
    def __init__(self, cache_file: Optional[Path] = None, default_ttl_hours: int = 24):
        self.cache_file = cache_file or DATA_CACHE_DIR / "discogs_cache.db"
        self.default_ttl = timedelta(hours=default_ttl_hours)
        
        # Ensure cache directory exists
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database with cache tables"""
        with sqlite3.connect(self.cache_file) as conn:
            cursor = conn.cursor()
            
            # Create cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key TEXT PRIMARY KEY,
                    data BLOB,
                    created_at TEXT,
                    expires_at TEXT,
                    hit_count INTEGER DEFAULT 0,
                    data_size INTEGER DEFAULT 0
                )
            """)
            
            # Create index on expiration for efficient cleanup
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at)
            """)
            
            conn.commit()
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data for storage"""
        try:
            # Try JSON first for human-readable storage of simple types
            if isinstance(data, (dict, list, str, int, float, bool)) or data is None:
                return json.dumps(data, default=str).encode('utf-8')
        except (TypeError, ValueError):
            pass
        
        # Fall back to pickle for complex objects
        return pickle.dumps(data)
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize data from storage"""
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fall back to pickle
            return pickle.loads(data)
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a consistent cache key from arguments"""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]
    
    def get(self, key: str) -> Optional[Any]:
        """Get data from cache"""
        with sqlite3.connect(self.cache_file) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT data, expires_at, hit_count 
                FROM cache_entries 
                WHERE key = ?
            """, (key,))
            
            result = cursor.fetchone()
            if not result:
                return None
            
            data_blob, expires_at_str, hit_count = result
            
            # Check if expired
            if expires_at_str:
                expires_at = datetime.fromisoformat(expires_at_str)
                if datetime.now() > expires_at:
                    self.delete(key)
                    return None
            
            # Update hit count
            cursor.execute("""
                UPDATE cache_entries 
                SET hit_count = hit_count + 1 
                WHERE key = ?
            """, (key,))
            conn.commit()
            
            try:
                return self._deserialize_data(data_blob)
            except Exception as e:
                self.logger.error(f"Failed to deserialize cache data for key {key}: {e}")
                self.delete(key)
                return None
    
    def set(self, key: str, data: Any, ttl: Optional[timedelta] = None) -> bool:
        """Store data in cache"""
        try:
            serialized_data = self._serialize_data(data)
            data_size = len(serialized_data)
            
            created_at = datetime.now()
            expires_at = created_at + (ttl or self.default_ttl) if ttl != timedelta(0) else None
            
            with sqlite3.connect(self.cache_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO cache_entries 
                    (key, data, created_at, expires_at, hit_count, data_size)
                    VALUES (?, ?, ?, ?, 0, ?)
                """, (
                    key,
                    serialized_data,
                    created_at.isoformat(),
                    expires_at.isoformat() if expires_at else None,
                    data_size
                ))
                conn.commit()
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cache data for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache"""
        with sqlite3.connect(self.cache_file) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted
    
    def clear(self) -> int:
        """Clear all cache entries"""
        with sqlite3.connect(self.cache_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cache_entries")
            count = cursor.fetchone()[0]
            cursor.execute("DELETE FROM cache_entries")
            conn.commit()
            return count
    
    def cleanup_expired(self) -> int:
        """Remove expired entries from cache"""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.cache_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM cache_entries 
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (now,))
            deleted = cursor.rowcount
            conn.commit()
            return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with sqlite3.connect(self.cache_file) as conn:
            cursor = conn.cursor()
            
            # Total entries
            cursor.execute("SELECT COUNT(*) FROM cache_entries")
            total_entries = cursor.fetchone()[0]
            
            # Total size
            cursor.execute("SELECT SUM(data_size) FROM cache_entries")
            total_size = cursor.fetchone()[0] or 0
            
            # Expired entries
            now = datetime.now().isoformat()
            cursor.execute("""
                SELECT COUNT(*) FROM cache_entries 
                WHERE expires_at IS NOT NULL AND expires_at < ?
            """, (now,))
            expired_entries = cursor.fetchone()[0]
            
            # Hit count statistics
            cursor.execute("""
                SELECT AVG(hit_count), MAX(hit_count) 
                FROM cache_entries
            """)
            avg_hits, max_hits = cursor.fetchone()
            
            return {
                'total_entries': total_entries,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / 1024 / 1024,
                'expired_entries': expired_entries,
                'avg_hit_count': avg_hits or 0,
                'max_hit_count': max_hits or 0
            }


class DiscogsCache:
    """High-level cache interface for Discogs API data"""
    
    def __init__(self, cache: Optional[SQLiteCache] = None):
        self.cache = cache or SQLiteCache()
        self.logger = logging.getLogger(__name__)
    
    def get_collection(self, username: str) -> Optional[List[AlbumData]]:
        """Get cached collection data"""
        key = self.cache._generate_key("collection", username)
        cached_data = self.cache.get(key)
        
        if cached_data:
            self.logger.info(f"Cache hit for collection: {username}")
            # Convert back to AlbumData objects if needed
            if isinstance(cached_data, list) and cached_data:
                if isinstance(cached_data[0], dict):
                    return [AlbumData(**item) for item in cached_data]
            return cached_data
        
        self.logger.info(f"Cache miss for collection: {username}")
        return None
    
    def set_collection(self, username: str, collection: List[AlbumData], 
                      ttl_hours: int = 24) -> bool:
        """Cache collection data"""
        key = self.cache._generate_key("collection", username)
        
        # Convert AlbumData objects to dicts for serialization
        serializable_data = [asdict(album) for album in collection]
        
        success = self.cache.set(key, serializable_data, timedelta(hours=ttl_hours))
        
        if success:
            self.logger.info(f"Cached collection for {username}: {len(collection)} albums")
        else:
            self.logger.error(f"Failed to cache collection for {username}")
        
        return success
    
    def get_release_details(self, release_id: int) -> Optional[Dict]:
        """Get cached release details"""
        key = self.cache._generate_key("release", release_id)
        cached_data = self.cache.get(key)
        
        if cached_data:
            self.logger.debug(f"Cache hit for release: {release_id}")
        else:
            self.logger.debug(f"Cache miss for release: {release_id}")
        
        return cached_data
    
    def set_release_details(self, release_id: int, release_data: Dict,
                           ttl_hours: int = 168) -> bool:  # 7 days default
        """Cache release details"""
        key = self.cache._generate_key("release", release_id)
        success = self.cache.set(key, release_data, timedelta(hours=ttl_hours))
        
        if success:
            self.logger.debug(f"Cached release details: {release_id}")
        
        return success
    
    def get_search_results(self, query: str, limit: int = 50) -> Optional[List[Dict]]:
        """Get cached search results"""
        key = self.cache._generate_key("search", query, limit)
        cached_data = self.cache.get(key)
        
        if cached_data:
            self.logger.debug(f"Cache hit for search: {query}")
        else:
            self.logger.debug(f"Cache miss for search: {query}")
        
        return cached_data
    
    def set_search_results(self, query: str, results: List[Dict], 
                          limit: int = 50, ttl_hours: int = 6) -> bool:
        """Cache search results (shorter TTL since they change more frequently)"""
        key = self.cache._generate_key("search", query, limit)
        success = self.cache.set(key, results, timedelta(hours=ttl_hours))
        
        if success:
            self.logger.debug(f"Cached search results: {query} ({len(results)} results)")
        
        return success
    
    def clear_user_data(self, username: str) -> int:
        """Clear all cached data for a specific user"""
        # This is a simple implementation - in practice you might want to track
        # user-specific keys more systematically
        user_keys = [
            self.cache._generate_key("collection", username),
        ]
        
        deleted = 0
        for key in user_keys:
            if self.cache.delete(key):
                deleted += 1
        
        return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return self.cache.get_stats()
    
    def cleanup(self) -> Dict[str, int]:
        """Clean up expired entries"""
        expired = self.cache.cleanup_expired()
        return {"expired_entries_removed": expired}


# Global cache instance
_discogs_cache = None

def get_discogs_cache() -> DiscogsCache:
    """Get the global Discogs cache instance"""
    global _discogs_cache
    if _discogs_cache is None:
        _discogs_cache = DiscogsCache()
    return _discogs_cache


# CLI interface for cache management
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Discogs Cache Management")
    parser.add_argument("command", choices=["stats", "clear", "cleanup"])
    
    args = parser.parse_args()
    
    cache = get_discogs_cache()
    
    if args.command == "stats":
        stats = cache.get_stats()
        print("📊 Cache Statistics:")
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  Total size: {stats['total_size_mb']:.2f} MB")
        print(f"  Expired entries: {stats['expired_entries']}")
        print(f"  Average hits: {stats['avg_hit_count']:.1f}")
        print(f"  Max hits: {stats['max_hit_count']}")
    
    elif args.command == "clear":
        deleted = cache.cache.clear()
        print(f"🗑️  Cleared {deleted} cache entries")
    
    elif args.command == "cleanup":
        result = cache.cleanup()
        print(f"🧹 Cleaned up {result['expired_entries_removed']} expired entries")