"""
Tests for Discogs API client functionality
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import requests

from src.data.discogs_client import DiscogsClient, AlbumData, RateLimiter
from src.data.cache import SQLiteCache, DiscogsCache
from src.data.cached_discogs_client import CachedDiscogsClient


class TestRateLimiter:
    """Test the rate limiting functionality"""
    
    def test_rate_limiter_init(self):
        limiter = RateLimiter(max_requests=10, time_window=60)
        assert limiter.max_requests == 10
        assert limiter.time_window == 60
        assert len(limiter.requests) == 0
    
    @patch('src.data.discogs_client.time.sleep')
    def test_rate_limiter_allows_requests_under_limit(self, mock_sleep):
        limiter = RateLimiter(max_requests=5, time_window=60)
        
        # Should allow first 5 requests without sleeping
        for _ in range(5):
            limiter.wait_if_needed()
        
        mock_sleep.assert_not_called()
        assert len(limiter.requests) == 5
    
    @patch('src.data.discogs_client.time.sleep')
    @patch('src.data.discogs_client.datetime')
    def test_rate_limiter_sleeps_when_limit_exceeded(self, mock_datetime, mock_sleep):
        # Mock datetime to have consistent timing
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        limiter = RateLimiter(max_requests=2, time_window=60)
        
        # Add 2 requests at the limit
        for _ in range(2):
            limiter.wait_if_needed()
        
        # The third request should trigger sleep
        limiter.wait_if_needed()
        
        # Should have called sleep since we exceeded the limit
        mock_sleep.assert_called()


class TestDiscogsClient:
    """Test the basic Discogs API client"""
    
    @pytest.fixture
    def mock_client(self):
        with patch('src.data.discogs_client.requests.Session') as mock_session:
            client = DiscogsClient("test_token", "test_user")
            client.session = mock_session.return_value
            return client
    
    def test_discogs_client_init(self):
        client = DiscogsClient("test_token", "test_user")
        assert client.user_token == "test_token"
        assert client.username == "test_user"
        assert client.rate_limiter is not None
    
    def test_discogs_client_requires_token(self):
        with pytest.raises(ValueError, match="Discogs user token is required"):
            DiscogsClient("", "test_user")
    
    def test_discogs_client_requires_username(self):
        with pytest.raises(ValueError, match="Discogs username is required"):
            DiscogsClient("test_token", "")
    
    def test_make_request_success(self, mock_client):
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {"test": "data"}
        mock_response.raise_for_status = Mock()
        mock_client.session.get.return_value = mock_response
        
        result = mock_client._make_request("/test")
        
        assert result == {"test": "data"}
        mock_client.session.get.assert_called_once()
        mock_response.raise_for_status.assert_called_once()
    
    def test_make_request_handles_errors(self, mock_client):
        # Mock API error
        mock_client.session.get.side_effect = requests.exceptions.RequestException("API Error")
        
        with pytest.raises(requests.exceptions.RequestException):
            mock_client._make_request("/test")
    
    def test_parse_album_data(self, mock_client):
        # Sample Discogs API response data
        release_data = {
            "basic_information": {
                "id": 123456,
                "title": "Test Album",
                "year": 2023,
                "genres": ["Rock", "Alternative"],
                "styles": ["Indie Rock"],
                "artists": [{"name": "Test Artist"}],
                "labels": [{"name": "Test Label"}],
                "formats": [{"name": "Vinyl"}],
                "tracklist": [{"title": "Track 1", "duration": "3:00"}]
            },
            "notes": "Test notes",
            "date_added": "2023-01-01T12:00:00-08:00",
            "folder_id": 0,
            "instance_id": 789
        }
        
        album = mock_client._parse_album_data(release_data)
        
        assert isinstance(album, AlbumData)
        assert album.id == 123456
        assert album.title == "Test Album"
        assert album.artist == "Test Artist"
        assert album.year == 2023
        assert album.genres == ["Rock", "Alternative"]
        assert album.styles == ["Indie Rock"]
        assert album.labels == ["Test Label"]
        assert album.formats == ["Vinyl"]
        assert album.notes == "Test notes"


class TestSQLiteCache:
    """Test the SQLite caching functionality"""
    
    @pytest.fixture
    def temp_cache(self, tmp_path):
        cache_file = tmp_path / "test_cache.db"
        return SQLiteCache(cache_file, default_ttl_hours=1)
    
    def test_cache_init(self, temp_cache):
        assert temp_cache.cache_file.exists()
        
        # Test that tables were created
        stats = temp_cache.get_stats()
        assert stats['total_entries'] == 0
    
    def test_cache_set_and_get(self, temp_cache):
        test_data = {"test": "data", "number": 42}
        
        # Set data
        success = temp_cache.set("test_key", test_data)
        assert success
        
        # Get data
        retrieved_data = temp_cache.get("test_key")
        assert retrieved_data == test_data
    
    def test_cache_get_nonexistent_key(self, temp_cache):
        result = temp_cache.get("nonexistent_key")
        assert result is None
    
    def test_cache_delete(self, temp_cache):
        temp_cache.set("test_key", "test_data")
        
        # Verify it exists
        assert temp_cache.get("test_key") == "test_data"
        
        # Delete it
        deleted = temp_cache.delete("test_key")
        assert deleted
        
        # Verify it's gone
        assert temp_cache.get("test_key") is None
    
    def test_cache_stats(self, temp_cache):
        # Initially empty
        stats = temp_cache.get_stats()
        assert stats['total_entries'] == 0
        assert stats['total_size_bytes'] == 0
        
        # Add some data
        temp_cache.set("key1", "data1")
        temp_cache.set("key2", {"data": 2})
        
        # Check stats
        stats = temp_cache.get_stats()
        assert stats['total_entries'] == 2
        assert stats['total_size_bytes'] > 0


class TestDiscogsCache:
    """Test the high-level Discogs cache interface"""
    
    @pytest.fixture
    def temp_discogs_cache(self, tmp_path):
        cache_file = tmp_path / "test_discogs_cache.db"
        sqlite_cache = SQLiteCache(cache_file)
        return DiscogsCache(sqlite_cache)
    
    def test_collection_caching(self, temp_discogs_cache):
        # Create test collection
        test_collection = [
            AlbumData(
                id=1, title="Album 1", artist="Artist 1", year=2023,
                genres=["Rock"], styles=["Indie"], labels=["Label 1"],
                formats=["Vinyl"], tracklist=[], notes="", 
                date_added="2023-01-01", folder_id=0, instance_id=1,
                basic_information={}
            )
        ]
        
        username = "test_user"
        
        # Initially no cached data
        assert temp_discogs_cache.get_collection(username) is None
        
        # Cache the collection
        success = temp_discogs_cache.set_collection(username, test_collection)
        assert success
        
        # Retrieve cached collection
        cached_collection = temp_discogs_cache.get_collection(username)
        assert cached_collection is not None
        assert len(cached_collection) == 1
        assert cached_collection[0].title == "Album 1"
        assert cached_collection[0].artist == "Artist 1"
    
    def test_release_details_caching(self, temp_discogs_cache):
        release_id = 12345
        release_data = {"id": release_id, "title": "Test Release", "year": 2023}
        
        # Initially no cached data
        assert temp_discogs_cache.get_release_details(release_id) is None
        
        # Cache the release details
        success = temp_discogs_cache.set_release_details(release_id, release_data)
        assert success
        
        # Retrieve cached release details
        cached_release = temp_discogs_cache.get_release_details(release_id)
        assert cached_release == release_data
    
    def test_search_results_caching(self, temp_discogs_cache):
        query = "test query"
        search_results = [
            {"id": 1, "title": "Result 1"},
            {"id": 2, "title": "Result 2"}
        ]
        
        # Initially no cached results
        assert temp_discogs_cache.get_search_results(query) is None
        
        # Cache the search results
        success = temp_discogs_cache.set_search_results(query, search_results)
        assert success
        
        # Retrieve cached results
        cached_results = temp_discogs_cache.get_search_results(query)
        assert cached_results == search_results


class TestCachedDiscogsClient:
    """Test the cached Discogs client integration"""
    
    @pytest.fixture
    def mock_cached_client(self, tmp_path):
        # Create mocks
        mock_discogs_client = Mock(spec=DiscogsClient)
        mock_discogs_client.username = "test_user"
        mock_discogs_client.test_connection.return_value = True
        
        # Create real cache with temp file
        cache_file = tmp_path / "test_cached_client.db"
        sqlite_cache = SQLiteCache(cache_file)
        discogs_cache = DiscogsCache(sqlite_cache)
        
        return CachedDiscogsClient(mock_discogs_client, discogs_cache)
    
    def test_cached_client_uses_cache_for_collection(self, mock_cached_client):
        # Mock collection data
        test_collection = [
            AlbumData(
                id=1, title="Cached Album", artist="Cached Artist", year=2023,
                genres=["Rock"], styles=[], labels=[], formats=["Vinyl"],
                tracklist=[], notes="", date_added="2023-01-01",
                folder_id=0, instance_id=1, basic_information={}
            )
        ]
        
        # Pre-populate cache
        mock_cached_client.cache.set_collection("test_user", test_collection)
        
        # Get collection - should use cache
        result = mock_cached_client.get_collection_items()
        
        assert result == test_collection
        # Should not have called the underlying client
        mock_cached_client.client.get_collection_items.assert_not_called()
    
    def test_cached_client_fetches_when_no_cache(self, mock_cached_client):
        # Mock API response
        test_collection = [
            AlbumData(
                id=2, title="API Album", artist="API Artist", year=2023,
                genres=["Pop"], styles=[], labels=[], formats=["CD"],
                tracklist=[], notes="", date_added="2023-01-01",
                folder_id=0, instance_id=2, basic_information={}
            )
        ]
        mock_cached_client.client.get_collection_items.return_value = test_collection
        
        # Get collection - should fetch from API
        result = mock_cached_client.get_collection_items()
        
        assert result == test_collection
        # Should have called the underlying client
        mock_cached_client.client.get_collection_items.assert_called_once()


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing"""
    with patch.dict('os.environ', {
        'DISCOGS_USER_TOKEN': 'test_token',
        'DISCOGS_USERNAME': 'test_user'
    }):
        yield