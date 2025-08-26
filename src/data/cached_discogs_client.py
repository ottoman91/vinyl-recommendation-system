"""
Cached Discogs API client that combines API calls with intelligent caching
"""
import logging
from typing import List, Optional, Dict, Iterator
from datetime import timedelta

from .discogs_client import DiscogsClient, AlbumData, create_discogs_client
from .cache import DiscogsCache, get_discogs_cache


class CachedDiscogsClient:
    """
    Discogs API client with intelligent caching
    
    This client wraps the basic DiscogsClient and adds caching for:
    - User collections (cached for 24 hours)
    - Release details (cached for 7 days)
    - Search results (cached for 6 hours)
    """
    
    def __init__(self, discogs_client: Optional[DiscogsClient] = None, 
                 cache: Optional[DiscogsCache] = None):
        self.client = discogs_client or create_discogs_client()
        self.cache = cache or get_discogs_cache()
        self.logger = logging.getLogger(__name__)
        
        if not self.client:
            raise RuntimeError("Failed to create Discogs client. Check your configuration.")
    
    def test_connection(self) -> bool:
        """Test connection to Discogs API"""
        return self.client.test_connection()
    
    def get_collection_items(self, folder_id: int = 0, 
                           use_cache: bool = True,
                           cache_ttl_hours: int = 24) -> List[AlbumData]:
        """
        Get all collection items, with caching support
        
        Args:
            folder_id: Collection folder ID (0 for all)
            use_cache: Whether to use cached data if available
            cache_ttl_hours: How long to cache the results
        
        Returns:
            List of AlbumData objects
        """
        username = self.client.username
        
        # Try cache first if enabled
        if use_cache:
            cached_collection = self.cache.get_collection(username)
            if cached_collection:
                self.logger.info(f"Using cached collection data ({len(cached_collection)} albums)")
                return cached_collection
        
        # Fetch from API
        self.logger.info("Fetching collection from Discogs API...")
        collection = list(self.client.get_collection_items(folder_id))
        
        self.logger.info(f"Fetched {len(collection)} albums from Discogs API")
        
        # Cache the results
        if use_cache and collection:
            self.cache.set_collection(username, collection, cache_ttl_hours)
        
        return collection
    
    def get_release_details(self, release_id: int, 
                          use_cache: bool = True,
                          cache_ttl_hours: int = 168) -> Optional[Dict]:
        """
        Get detailed release information, with caching
        
        Args:
            release_id: Discogs release ID
            use_cache: Whether to use cached data if available
            cache_ttl_hours: How long to cache the results (default 7 days)
        
        Returns:
            Release details dictionary or None
        """
        # Try cache first if enabled
        if use_cache:
            cached_release = self.cache.get_release_details(release_id)
            if cached_release:
                self.logger.debug(f"Using cached release details for {release_id}")
                return cached_release
        
        # Fetch from API
        self.logger.debug(f"Fetching release details for {release_id} from API")
        release_data = self.client.get_release_details(release_id)
        
        # Cache the results
        if use_cache and release_data:
            self.cache.set_release_details(release_id, release_data, cache_ttl_hours)
        
        return release_data
    
    def search_releases(self, query: str, per_page: int = 50,
                       use_cache: bool = True,
                       cache_ttl_hours: int = 6) -> List[Dict]:
        """
        Search for releases, with caching
        
        Args:
            query: Search query
            per_page: Results per page
            use_cache: Whether to use cached data if available
            cache_ttl_hours: How long to cache results (default 6 hours)
        
        Returns:
            List of search result dictionaries
        """
        # Try cache first if enabled
        if use_cache:
            cached_results = self.cache.get_search_results(query, per_page)
            if cached_results:
                self.logger.debug(f"Using cached search results for '{query}'")
                return cached_results
        
        # Fetch from API
        self.logger.debug(f"Searching Discogs API for '{query}'")
        results = self.client.search_releases(query, per_page)
        
        # Cache the results
        if use_cache and results:
            self.cache.set_search_results(query, results, per_page, cache_ttl_hours)
        
        return results
    
    def sync_collection(self, force_refresh: bool = False) -> Dict[str, any]:
        """
        Sync user collection with optional cache refresh
        
        Args:
            force_refresh: If True, ignore cache and fetch fresh data
        
        Returns:
            Dictionary with sync statistics
        """
        start_time = self.logger.info("Starting collection sync...")
        
        # Get collection (forcing refresh if requested)
        collection = self.get_collection_items(use_cache=not force_refresh)
        
        # Gather statistics
        stats = {
            'total_albums': len(collection),
            'unique_artists': len(set(album.artist for album in collection)),
            'unique_genres': len(set(genre for album in collection for genre in album.genres)),
            'unique_labels': len(set(label for album in collection for label in album.labels)),
            'year_range': {
                'earliest': min((album.year for album in collection if album.year), default=None),
                'latest': max((album.year for album in collection if album.year), default=None)
            },
            'cache_used': not force_refresh
        }
        
        self.logger.info(f"Collection sync complete: {stats['total_albums']} albums")
        return stats
    
    def get_album_by_title_artist(self, title: str, artist: str) -> Optional[AlbumData]:
        """
        Find a specific album in your collection by title and artist
        
        Args:
            title: Album title
            artist: Artist name
        
        Returns:
            AlbumData if found in collection, None otherwise
        """
        collection = self.get_collection_items()
        
        title_lower = title.lower()
        artist_lower = artist.lower()
        
        for album in collection:
            if (title_lower in album.title.lower() and 
                artist_lower in album.artist.lower()):
                return album
        
        return None
    
    def clear_cache(self) -> Dict[str, int]:
        """Clear all cached data for this user"""
        return self.cache.clear_user_data(self.client.username)
    
    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics"""
        return self.cache.get_stats()


def create_cached_discogs_client() -> Optional[CachedDiscogsClient]:
    """Factory function to create a cached Discogs client"""
    try:
        return CachedDiscogsClient()
    except Exception as e:
        logging.error(f"Failed to create cached Discogs client: {e}")
        return None


# CLI interface for testing the cached client
if __name__ == "__main__":
    import argparse
    import json
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="Cached Discogs API Client")
    parser.add_argument("command", choices=["test", "sync", "search", "stats", "clear-cache"])
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--limit", type=int, default=10, help="Limit results")
    parser.add_argument("--force-refresh", action="store_true", 
                       help="Force refresh (ignore cache)")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    client = create_cached_discogs_client()
    if not client:
        print("❌ Failed to create cached Discogs client. Check your configuration.")
        exit(1)
    
    if args.command == "test":
        if client.test_connection():
            print("✅ Successfully connected to Discogs API!")
            
            # Show cache stats
            stats = client.get_cache_stats()
            print(f"\n📊 Cache Stats:")
            print(f"  Entries: {stats['total_entries']}")
            print(f"  Size: {stats['total_size_mb']:.2f} MB")
            print(f"  Expired: {stats['expired_entries']}")
        else:
            print("❌ Failed to connect to Discogs API")
    
    elif args.command == "sync":
        print("🎵 Syncing collection...")
        stats = client.sync_collection(force_refresh=args.force_refresh)
        
        print(f"\n📊 Collection Statistics:")
        print(f"  Total albums: {stats['total_albums']}")
        print(f"  Unique artists: {stats['unique_artists']}")
        print(f"  Unique genres: {stats['unique_genres']}")
        print(f"  Unique labels: {stats['unique_labels']}")
        
        year_range = stats['year_range']
        if year_range['earliest'] and year_range['latest']:
            print(f"  Year range: {year_range['earliest']} - {year_range['latest']}")
        
        print(f"  Cache used: {'No (forced refresh)' if not stats['cache_used'] else 'Yes'}")
        
        # Show some sample albums
        collection = client.get_collection_items()
        print(f"\n🎵 Sample albums:")
        for i, album in enumerate(collection[:args.limit], 1):
            genres_str = ', '.join(album.genres[:2])  # Show first 2 genres
            print(f"  {i:2d}. {album.artist} - {album.title} ({album.year}) [{genres_str}]")
    
    elif args.command == "search":
        if not args.query:
            print("❌ Please provide a search query with --query")
            exit(1)
            
        print(f"🔍 Searching for: {args.query}")
        results = client.search_releases(args.query, per_page=args.limit)
        
        print(f"\n📊 Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            year = result.get('year', 'N/A')
            genre = ', '.join(result.get('genre', [])[:2])  # First 2 genres
            print(f"  {i:2d}. {result.get('title')} ({year}) [{genre}]")
    
    elif args.command == "stats":
        stats = client.get_cache_stats()
        print("📊 Cache Statistics:")
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  Total size: {stats['total_size_mb']:.2f} MB")
        print(f"  Expired entries: {stats['expired_entries']}")
        print(f"  Average hits: {stats['avg_hit_count']:.1f}")
        print(f"  Max hits: {stats['max_hit_count']}")
    
    elif args.command == "clear-cache":
        result = client.clear_cache()
        print(f"🗑️  Cleared cache data")
        
        # Show updated stats
        stats = client.get_cache_stats()
        print(f"📊 Cache now has {stats['total_entries']} entries")