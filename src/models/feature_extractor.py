"""
Feature extraction pipeline for vinyl recommendation system

This module transforms raw Discogs album data into ML-ready features that capture
musical taste patterns for content-based filtering.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import StandardScaler, LabelEncoder
import logging
from dataclasses import dataclass

from src.data.discogs_client import AlbumData


@dataclass
class FeatureConfig:
    """Configuration for feature extraction"""
    # Genre/Style features
    min_genre_frequency: int = 2  # Minimum frequency for genre to be included
    max_genres: int = 50  # Maximum number of genre features
    
    # Artist features  
    min_artist_frequency: int = 1  # Minimum frequency for artist similarity
    max_artists: int = 100  # Maximum number of artist features
    
    # Label features
    min_label_frequency: int = 1  # Minimum frequency for label features
    max_labels: int = 50  # Maximum number of label features
    
    # TF-IDF features
    max_tfidf_features: int = 100  # Maximum TF-IDF features from titles/descriptions
    min_df: int = 1  # Minimum document frequency for TF-IDF
    max_df: float = 0.8  # Maximum document frequency for TF-IDF
    
    # Year normalization
    year_reference: int = 2024  # Reference year for normalization
    year_weight: float = 0.1  # Weight for year-based similarity


class MusicFeatureExtractor:
    """
    Extracts features from album data for content-based recommendation
    
    Features extracted:
    1. Genre/Style one-hot encoding with frequency filtering
    2. Artist similarity based on collection patterns  
    3. Label preference scoring based on user collection
    4. Year-based features (decade, era, recency)
    5. TF-IDF features from album titles and descriptions
    6. Format preferences
    7. Collection-based preference weights
    """
    
    def __init__(self, config: Optional[FeatureConfig] = None):
        self.config = config or FeatureConfig()
        self.logger = logging.getLogger(__name__)
        
        # Fitted components (set during fit)
        self.genre_encoder = None
        self.style_encoder = None
        self.artist_encoder = None
        self.label_encoder = None
        self.tfidf_vectorizer = None
        self.scaler = None
        
        # Collection-based statistics (set during fit)
        self.genre_frequencies = None
        self.style_frequencies = None
        self.artist_frequencies = None
        self.label_frequencies = None
        self.user_preferences = None
        
        # Feature names for interpretability
        self.feature_names = []
        
    def fit(self, collection: List[AlbumData]) -> 'MusicFeatureExtractor':
        """
        Fit the feature extractor on user's collection
        
        Args:
            collection: List of AlbumData from user's collection
            
        Returns:
            Self for method chaining
        """
        self.logger.info(f"Fitting feature extractor on {len(collection)} albums")
        
        # Extract all categorical values from collection
        all_genres = []
        all_styles = []
        all_artists = []
        all_labels = []
        all_texts = []
        
        for album in collection:
            all_genres.extend(album.genres)
            all_styles.extend(album.styles)
            all_artists.append(album.artist)
            all_labels.extend(album.labels)
            
            # Combine title and notes for text features
            text = f"{album.title} {album.notes or ''}"
            all_texts.append(text.lower())
        
        # Calculate frequencies for filtering
        self.genre_frequencies = Counter(all_genres)
        self.style_frequencies = Counter(all_styles)
        self.artist_frequencies = Counter(all_artists)
        self.label_frequencies = Counter(all_labels)
        
        # Filter by minimum frequency and limit maximum features
        top_genres = [genre for genre, freq in self.genre_frequencies.most_common(self.config.max_genres) 
                     if freq >= self.config.min_genre_frequency]
        top_styles = [style for style, freq in self.style_frequencies.most_common(self.config.max_genres) 
                     if freq >= self.config.min_genre_frequency]
        top_artists = [artist for artist, freq in self.artist_frequencies.most_common(self.config.max_artists) 
                      if freq >= self.config.min_artist_frequency]
        top_labels = [label for label, freq in self.label_frequencies.most_common(self.config.max_labels) 
                     if freq >= self.config.min_label_frequency]
        
        self.logger.info(f"Selected features: {len(top_genres)} genres, {len(top_styles)} styles, "
                        f"{len(top_artists)} artists, {len(top_labels)} labels")
        
        # Fit encoders
        self.genre_encoder = self._fit_multi_label_encoder(top_genres)
        self.style_encoder = self._fit_multi_label_encoder(top_styles)
        self.artist_encoder = self._fit_single_label_encoder(top_artists)
        self.label_encoder = self._fit_multi_label_encoder(top_labels)
        
        # Fit TF-IDF vectorizer on album titles and descriptions
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=self.config.max_tfidf_features,
            min_df=self.config.min_df,
            max_df=self.config.max_df,
            stop_words='english',
            ngram_range=(1, 2)  # Unigrams and bigrams
        )
        self.tfidf_vectorizer.fit(all_texts)
        
        # Calculate user preferences based on collection
        self.user_preferences = self._calculate_user_preferences(collection)
        
        # Build feature names for interpretability
        self._build_feature_names()
        
        self.logger.info(f"Feature extractor fitted with {len(self.feature_names)} total features")
        return self
    
    def transform(self, albums: List[AlbumData]) -> np.ndarray:
        """
        Transform albums into feature vectors
        
        Args:
            albums: List of AlbumData to transform
            
        Returns:
            Feature matrix of shape (n_albums, n_features)
        """
        if not self._is_fitted():
            raise ValueError("Feature extractor must be fitted before transform")
        
        features_list = []
        
        for album in albums:
            album_features = []
            
            # 1. Genre features (one-hot encoded)
            genre_features = self._encode_multi_label(album.genres, self.genre_encoder)
            album_features.extend(genre_features)
            
            # 2. Style features (one-hot encoded)
            style_features = self._encode_multi_label(album.styles, self.style_encoder)
            album_features.extend(style_features)
            
            # 3. Artist features (preference-weighted)
            artist_features = self._encode_artist_features(album.artist)
            album_features.extend(artist_features)
            
            # 4. Label features (preference-weighted)
            label_features = self._encode_label_features(album.labels)
            album_features.extend(label_features)
            
            # 5. Year-based features
            year_features = self._encode_year_features(album.year)
            album_features.extend(year_features)
            
            # 6. TF-IDF features from title and description
            text = f"{album.title} {album.notes or ''}".lower()
            tfidf_features = self.tfidf_vectorizer.transform([text]).toarray()[0]
            album_features.extend(tfidf_features)
            
            # 7. Format features
            format_features = self._encode_format_features(album.formats)
            album_features.extend(format_features)
            
            features_list.append(album_features)
        
        feature_matrix = np.array(features_list, dtype=np.float32)
        
        # Normalize features if scaler is fitted
        if self.scaler is not None:
            feature_matrix = self.scaler.transform(feature_matrix)
        
        self.logger.debug(f"Transformed {len(albums)} albums into {feature_matrix.shape} feature matrix")
        return feature_matrix
    
    def fit_transform(self, collection: List[AlbumData]) -> np.ndarray:
        """
        Fit the extractor on collection and transform it
        
        Args:
            collection: User's album collection
            
        Returns:
            Feature matrix for the collection
        """
        return self.fit(collection).transform(collection)
    
    def get_feature_names(self) -> List[str]:
        """Get names of all features for interpretability"""
        return self.feature_names.copy()
    
    def get_feature_importance_for_album(self, album: AlbumData, 
                                       feature_vector: Optional[np.ndarray] = None) -> Dict[str, float]:
        """
        Get feature importance scores for a specific album for interpretability
        
        Args:
            album: Album to analyze
            feature_vector: Pre-computed feature vector (optional)
            
        Returns:
            Dictionary mapping feature names to their values/importance
        """
        if feature_vector is None:
            feature_vector = self.transform([album])[0]
        
        feature_importance = {}
        for i, (name, value) in enumerate(zip(self.feature_names, feature_vector)):
            if value > 0:  # Only include non-zero features
                feature_importance[name] = float(value)
        
        return dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
    
    def _fit_multi_label_encoder(self, categories: List[str]) -> Dict[str, int]:
        """Create mapping from category names to indices for multi-label encoding"""
        return {category: i for i, category in enumerate(sorted(categories))}
    
    def _fit_single_label_encoder(self, categories: List[str]) -> Dict[str, int]:
        """Create mapping from category names to indices for single-label encoding"""
        return {category: i for i, category in enumerate(sorted(categories))}
    
    def _encode_multi_label(self, labels: List[str], encoder: Dict[str, int]) -> List[float]:
        """Encode list of labels as multi-hot vector"""
        encoded = [0.0] * len(encoder)
        for label in labels:
            if label in encoder:
                encoded[encoder[label]] = 1.0
        return encoded
    
    def _encode_artist_features(self, artist: str) -> List[float]:
        """Encode artist with preference weighting based on collection frequency"""
        encoded = [0.0] * len(self.artist_encoder)
        
        if artist in self.artist_encoder:
            idx = self.artist_encoder[artist]
            # Weight by frequency in user's collection (preference strength)
            frequency = self.artist_frequencies.get(artist, 1)
            encoded[idx] = min(frequency / 3.0, 1.0)  # Normalize to [0, 1] range
        
        return encoded
    
    def _encode_label_features(self, labels: List[str]) -> List[float]:
        """Encode labels with preference weighting"""
        encoded = [0.0] * len(self.label_encoder)
        
        for label in labels:
            if label in self.label_encoder:
                idx = self.label_encoder[label]
                # Weight by frequency in user's collection
                frequency = self.label_frequencies.get(label, 1)
                encoded[idx] = min(frequency / 5.0, 1.0)  # Normalize to [0, 1] range
        
        return encoded
    
    def _encode_year_features(self, year: Optional[int]) -> List[float]:
        """Encode year-based features: decade, era, recency"""
        features = []
        
        if year and year > 1900:
            # Decade features (one-hot for major decades)
            decades = [1960, 1970, 1980, 1990, 2000, 2010, 2020]
            decade = (year // 10) * 10
            for dec in decades:
                features.append(1.0 if decade == dec else 0.0)
            
            # Era features
            if year < 1980:
                era = [1.0, 0.0, 0.0]  # Classic era
            elif year < 2000:
                era = [0.0, 1.0, 0.0]  # Modern era
            else:
                era = [0.0, 0.0, 1.0]  # Contemporary era
            features.extend(era)
            
            # Recency feature (newer albums get higher scores)
            recency = max(0.0, 1.0 - (self.config.year_reference - year) / 50.0)
            features.append(recency)
            
        else:
            # Unknown year - all zeros
            features = [0.0] * (len([1960, 1970, 1980, 1990, 2000, 2010, 2020]) + 3 + 1)
        
        return features
    
    def _encode_format_features(self, formats: List[str]) -> List[float]:
        """Encode format preferences (vinyl vs others)"""
        vinyl_weight = 1.0 if any('vinyl' in fmt.lower() for fmt in formats) else 0.0
        cd_weight = 1.0 if any('cd' in fmt.lower() for fmt in formats) else 0.0
        digital_weight = 1.0 if any(fmt.lower() in ['digital', 'file', 'mp3'] for fmt in formats) else 0.0
        
        return [vinyl_weight, cd_weight, digital_weight]
    
    def _calculate_user_preferences(self, collection: List[AlbumData]) -> Dict[str, any]:
        """Calculate user preferences based on collection patterns"""
        preferences = {
            'favorite_genres': self.genre_frequencies.most_common(5),
            'favorite_styles': self.style_frequencies.most_common(5),
            'favorite_artists': self.artist_frequencies.most_common(10),
            'favorite_labels': self.label_frequencies.most_common(10),
            'era_preference': self._calculate_era_preference(collection),
            'diversity_score': self._calculate_diversity_score(collection)
        }
        
        return preferences
    
    def _calculate_era_preference(self, collection: List[AlbumData]) -> Dict[str, float]:
        """Calculate user's era preferences"""
        years = [album.year for album in collection if album.year and album.year > 1900]
        if not years:
            return {}
        
        era_counts = Counter()
        for year in years:
            if year < 1980:
                era_counts['classic'] += 1
            elif year < 2000:
                era_counts['modern'] += 1
            else:
                era_counts['contemporary'] += 1
        
        total = sum(era_counts.values())
        return {era: count / total for era, count in era_counts.items()}
    
    def _calculate_diversity_score(self, collection: List[AlbumData]) -> float:
        """Calculate how diverse the user's collection is"""
        if not collection:
            return 0.0
        
        # Diversity based on unique genres per album
        unique_genres = len(self.genre_frequencies)
        total_albums = len(collection)
        
        return min(unique_genres / total_albums, 1.0)
    
    def _build_feature_names(self):
        """Build list of feature names for interpretability"""
        self.feature_names = []
        
        # Genre features
        for genre in sorted(self.genre_encoder.keys()):
            self.feature_names.append(f"genre_{genre}")
        
        # Style features  
        for style in sorted(self.style_encoder.keys()):
            self.feature_names.append(f"style_{style}")
        
        # Artist features
        for artist in sorted(self.artist_encoder.keys()):
            self.feature_names.append(f"artist_{artist}")
        
        # Label features
        for label in sorted(self.label_encoder.keys()):
            self.feature_names.append(f"label_{label}")
        
        # Year features
        decades = [1960, 1970, 1980, 1990, 2000, 2010, 2020]
        for decade in decades:
            self.feature_names.append(f"decade_{decade}s")
        
        self.feature_names.extend(['era_classic', 'era_modern', 'era_contemporary', 'year_recency'])
        
        # TF-IDF features
        if self.tfidf_vectorizer and hasattr(self.tfidf_vectorizer, 'feature_names_out_'):
            tfidf_names = self.tfidf_vectorizer.get_feature_names_out()
            for name in tfidf_names:
                self.feature_names.append(f"text_{name}")
        
        # Format features
        self.feature_names.extend(['format_vinyl', 'format_cd', 'format_digital'])
    
    def _is_fitted(self) -> bool:
        """Check if the feature extractor has been fitted"""
        return (self.genre_encoder is not None and 
                self.style_encoder is not None and 
                self.artist_encoder is not None and 
                self.label_encoder is not None and 
                self.tfidf_vectorizer is not None)


# Utility functions for testing and analysis
def analyze_feature_distribution(extractor: MusicFeatureExtractor, 
                                collection: List[AlbumData]) -> Dict[str, any]:
    """Analyze the distribution of extracted features"""
    if not extractor._is_fitted():
        raise ValueError("Feature extractor must be fitted")
    
    features = extractor.transform(collection)
    feature_names = extractor.get_feature_names()
    
    analysis = {
        'feature_count': features.shape[1],
        'non_zero_features': np.count_nonzero(features, axis=0),
        'feature_means': np.mean(features, axis=0),
        'feature_stds': np.std(features, axis=0),
        'sparsity': 1.0 - np.count_nonzero(features) / features.size
    }
    
    # Top features by variance (most discriminative)
    feature_vars = np.var(features, axis=0)
    top_features_idx = np.argsort(feature_vars)[-20:]  # Top 20 most variable features
    analysis['top_variable_features'] = [
        (feature_names[i], feature_vars[i]) for i in reversed(top_features_idx)
    ]
    
    return analysis


def create_feature_extractor_for_collection(collection: List[AlbumData], 
                                          config: Optional[FeatureConfig] = None) -> MusicFeatureExtractor:
    """
    Convenience function to create and fit a feature extractor for a collection
    
    Args:
        collection: User's album collection
        config: Optional configuration for feature extraction
        
    Returns:
        Fitted MusicFeatureExtractor
    """
    extractor = MusicFeatureExtractor(config)
    return extractor.fit(collection)