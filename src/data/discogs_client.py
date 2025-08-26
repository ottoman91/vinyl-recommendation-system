"""
Discogs API client for fetching user collection data
"""
import time
import logging
from typing import Dict, List, Optional, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import DISCOGS_USER_TOKEN, DISCOGS_USERNAME, DISCOGS_API_RATE_LIMIT


@dataclass
class AlbumData:
    """Data structure for album information from Discogs"""
    id: int
    title: str
    artist: str
    year: Optional[int]
    genres: List[str]
    styles: List[str]
    labels: List[str]
    formats: List[str]
    tracklist: List[Dict]
    notes: Optional[str]
    date_added: Optional[str]
    folder_id: int
    instance_id: int
    basic_information: Dict


class RateLimiter:
    """Rate limiter for API requests"""
    
    def __init__(self, max_requests: int = 60, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        
    def wait_if_needed(self):
        """Wait if we've exceeded the rate limit"""
        now = datetime.now()
        # Remove requests older than the time window
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < timedelta(seconds=self.time_window)]
        
        if len(self.requests) >= self.max_requests:
            # Calculate how long to wait
            oldest_request = min(self.requests)
            wait_time = self.time_window - (now - oldest_request).total_seconds()
            if wait_time > 0:
                logging.info(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)
                
        self.requests.append(now)


class DiscogsClient:
    """Client for interacting with the Discogs API"""
    
    BASE_URL = "https://api.discogs.com"
    
    def __init__(self, user_token: str, username: str, rate_limit: int = 60):
        if not user_token:
            raise ValueError("Discogs user token is required")
        if not username:
            raise ValueError("Discogs username is required")
            
        self.user_token = user_token
        self.username = username
        self.rate_limiter = RateLimiter(max_requests=rate_limit)
        
        # Configure session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set headers
        self.session.headers.update({
            'Authorization': f'Discogs token={user_token}',
            'User-Agent': f'VinylRecommendationSystem/1.0 +{self.BASE_URL}'
        })
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a rate-limited request to the Discogs API"""
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            self.logger.info(f"Making request to {url}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test if we can connect to Discogs API"""
        try:
            data = self._make_request(f"/users/{self.username}")
            self.logger.info(f"Successfully connected to Discogs API for user: {data.get('username')}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Discogs API: {e}")
            return False
    
    def get_collection_folders(self) -> List[Dict]:
        """Get all collection folders for the user"""
        try:
            data = self._make_request(f"/users/{self.username}/collection/folders")
            return data.get('folders', [])
        except Exception as e:
            self.logger.error(f"Failed to get collection folders: {e}")
            return []
    
    def get_collection_items(self, folder_id: int = 0, per_page: int = 100) -> Iterator[AlbumData]:
        """
        Get all items from a collection folder with pagination
        folder_id=0 gets items from 'All' folder
        """
        page = 1
        total_pages = None
        
        while total_pages is None or page <= total_pages:
            try:
                params = {
                    'page': page,
                    'per_page': per_page,
                    'sort': 'added',
                    'sort_order': 'desc'
                }
                
                self.logger.info(f"Fetching collection page {page}")
                data = self._make_request(
                    f"/users/{self.username}/collection/folders/{folder_id}/releases",
                    params=params
                )
                
                if total_pages is None:
                    total_pages = data.get('pagination', {}).get('pages', 1)
                    total_items = data.get('pagination', {}).get('items', 0)
                    self.logger.info(f"Collection has {total_items} items across {total_pages} pages")
                
                releases = data.get('releases', [])
                for release_data in releases:
                    yield self._parse_album_data(release_data)
                
                page += 1
                
            except Exception as e:
                self.logger.error(f"Failed to fetch collection page {page}: {e}")
                break
    
    def get_release_details(self, release_id: int) -> Optional[Dict]:
        """Get detailed information about a specific release"""
        try:
            return self._make_request(f"/releases/{release_id}")
        except Exception as e:
            self.logger.error(f"Failed to get release details for {release_id}: {e}")
            return None
    
    def search_releases(self, query: str, per_page: int = 50) -> List[Dict]:
        """Search for releases by title, artist, etc."""
        try:
            params = {
                'q': query,
                'type': 'release',
                'per_page': per_page
            }
            data = self._make_request("/database/search", params=params)
            return data.get('results', [])
        except Exception as e:
            self.logger.error(f"Failed to search releases for '{query}': {e}")
            return []
    
    def _parse_album_data(self, release_data: Dict) -> AlbumData:
        """Parse release data from API response into AlbumData object"""
        basic_info = release_data.get('basic_information', {})
        
        # Extract artists
        artists = basic_info.get('artists', [])
        artist_names = [artist.get('name', '') for artist in artists]
        primary_artist = artist_names[0] if artist_names else 'Unknown Artist'
        
        # Extract labels
        labels = basic_info.get('labels', [])
        label_names = [label.get('name', '') for label in labels]
        
        # Extract formats
        formats = basic_info.get('formats', [])
        format_names = [fmt.get('name', '') for fmt in formats]
        
        return AlbumData(
            id=basic_info.get('id'),
            title=basic_info.get('title', ''),
            artist=primary_artist,
            year=basic_info.get('year'),
            genres=basic_info.get('genres', []),
            styles=basic_info.get('styles', []),
            labels=label_names,
            formats=format_names,
            tracklist=basic_info.get('tracklist', []),
            notes=release_data.get('notes'),
            date_added=release_data.get('date_added'),
            folder_id=release_data.get('folder_id'),
            instance_id=release_data.get('instance_id'),
            basic_information=basic_info
        )


def create_discogs_client() -> Optional[DiscogsClient]:
    """Factory function to create a Discogs client with configuration"""
    try:
        client = DiscogsClient(
            user_token=DISCOGS_USER_TOKEN,
            username=DISCOGS_USERNAME,
            rate_limit=DISCOGS_API_RATE_LIMIT
        )
        
        if client.test_connection():
            return client
        else:
            return None
            
    except Exception as e:
        logging.error(f"Failed to create Discogs client: {e}")
        return None


# CLI interface for testing
if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Discogs API Client")
    parser.add_argument("command", choices=["test", "sync", "search"])
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--limit", type=int, default=10, help="Limit results")
    
    args = parser.parse_args()
    
    client = create_discogs_client()
    if not client:
        print("❌ Failed to create Discogs client. Check your configuration.")
        exit(1)
    
    if args.command == "test":
        print("✅ Successfully connected to Discogs API!")
        
        # Show collection folders
        folders = client.get_collection_folders()
        print(f"\n📁 Collection folders ({len(folders)}):")
        for folder in folders:
            print(f"  - {folder.get('name')} (ID: {folder.get('id')}, Count: {folder.get('count')})")
    
    elif args.command == "sync":
        print("🎵 Syncing collection...")
        
        count = 0
        for album in client.get_collection_items():
            count += 1
            print(f"{count:3d}. {album.artist} - {album.title} ({album.year})")
            if count >= args.limit:
                break
                
        print(f"\n✅ Processed {count} albums from your collection")
    
    elif args.command == "search":
        if not args.query:
            print("❌ Please provide a search query with --query")
            exit(1)
            
        print(f"🔍 Searching for: {args.query}")
        results = client.search_releases(args.query, per_page=args.limit)
        
        for i, result in enumerate(results, 1):
            print(f"{i:2d}. {result.get('title')} ({result.get('year', 'N/A')})")