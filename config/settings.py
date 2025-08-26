"""
Configuration settings for the Vinyl Recommendation System
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# Environment variables
DISCOGS_USER_TOKEN = os.getenv("DISCOGS_USER_TOKEN")
DISCOGS_USERNAME = os.getenv("DISCOGS_USERNAME") 
DISCOGS_API_RATE_LIMIT = int(os.getenv("DISCOGS_API_RATE_LIMIT", "60"))

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/vinyl_recommendations.db")

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Application Settings
APP_NAME = "Vinyl Recommendation System"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "A content-based vinyl record recommendation system using Discogs data"

# Model Settings
MODEL_CACHE_DIR = BASE_DIR / "models" / "cache"
DATA_CACHE_DIR = BASE_DIR / "data" / "cache"

# Create directories if they don't exist
MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
DATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)