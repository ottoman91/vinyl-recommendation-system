"""
Test the feature extraction pipeline on your vinyl collection
"""
import numpy as np
import pandas as pd
from src.data.cached_discogs_client import create_cached_discogs_client
from src.models.feature_extractor import MusicFeatureExtractor, FeatureConfig, analyze_feature_distribution

def test_feature_extraction():
    """Test feature extraction on the real collection"""
    print("🧪 Testing Feature Extraction Pipeline")
    print("=" * 50)
    
    # Load collection
    client = create_cached_discogs_client()
    if not client:
        print("❌ Failed to create Discogs client")
        return
    
    collection = client.get_collection_items()
    print(f"📊 Loaded {len(collection)} albums from collection")
    
    # Create and configure feature extractor
    config = FeatureConfig(
        min_genre_frequency=1,    # Include all genres (small collection)
        max_genres=20,            # Reasonable limit
        min_artist_frequency=1,   # Include all artists
        max_artists=30,           # Most of your artists
        max_tfidf_features=50,    # Text features from titles
        min_df=1,                 # Include rare terms
        max_df=0.9                # Remove very common terms
    )
    
    # Fit feature extractor
    print("\n🔧 Fitting feature extractor...")
    extractor = MusicFeatureExtractor(config)
    extractor.fit(collection)
    
    print(f"✅ Feature extractor fitted with {len(extractor.get_feature_names())} features")
    
    # Transform collection to features
    print("\n🎯 Extracting features...")
    features = extractor.transform(collection)
    print(f"✅ Extracted features: {features.shape[0]} albums × {features.shape[1]} features")
    
    # Analyze feature distribution
    print("\n📊 Analyzing feature distribution...")
    analysis = analyze_feature_distribution(extractor, collection)
    
    print(f"Feature Statistics:")
    print(f"  Total features: {analysis['feature_count']}")
    print(f"  Sparsity: {analysis['sparsity']:.2%} (good for efficiency)")
    print(f"  Non-zero features per category:")
    
    # Count features by type
    feature_names = extractor.get_feature_names()
    feature_types = {}
    for name in feature_names:
        category = name.split('_')[0]
        feature_types[category] = feature_types.get(category, 0) + 1
    
    for category, count in sorted(feature_types.items()):
        active_features = sum(1 for i, name in enumerate(feature_names) 
                             if name.startswith(category) and analysis['non_zero_features'][i] > 0)
        print(f"    {category}: {active_features}/{count} active")
    
    # Show top discriminative features
    print(f"\n🎭 Top 15 most discriminative features:")
    for i, (feature_name, variance) in enumerate(analysis['top_variable_features'][:15], 1):
        print(f"  {i:2d}. {feature_name}: {variance:.3f}")
    
    # Analyze some sample albums in detail
    print(f"\n🎵 Feature analysis for sample albums:")
    sample_albums = collection[:5]  # First 5 albums
    
    for i, album in enumerate(sample_albums, 1):
        print(f"\n{i}. {album.artist} - {album.title} ({album.year})")
        
        # Get features for this album
        album_features = extractor.transform([album])[0]
        feature_importance = extractor.get_feature_importance_for_album(album, album_features)
        
        # Show top features for this album
        top_features = list(feature_importance.items())[:10]
        print(f"   Top features: {', '.join([f'{name}({val:.2f})' for name, val in top_features])}")
        
        # Show raw metadata for comparison
        print(f"   Raw metadata: Genres={album.genres}, Styles={album.styles}")
    
    # Test similarity computation
    print(f"\n🔍 Testing similarity computation...")
    
    # Compare first two albums
    if len(collection) >= 2:
        album1 = collection[0]
        album2 = collection[1]
        
        feat1 = extractor.transform([album1])[0]
        feat2 = extractor.transform([album2])[0]
        
        # Cosine similarity
        similarity = np.dot(feat1, feat2) / (np.linalg.norm(feat1) * np.linalg.norm(feat2))
        
        print(f"Similarity between:")
        print(f"  '{album1.artist} - {album1.title}'")
        print(f"  '{album2.artist} - {album2.title}'")
        print(f"  Cosine similarity: {similarity:.3f}")
        
        # Show shared features
        shared_features = []
        for i, (name, val1, val2) in enumerate(zip(extractor.get_feature_names(), feat1, feat2)):
            if val1 > 0 and val2 > 0:
                shared_features.append((name, val1, val2))
        
        if shared_features:
            print(f"  Shared features ({len(shared_features)}): {', '.join([name for name, _, _ in shared_features[:5]])}")
    
    # Show user preference profile
    print(f"\n👤 Your musical preference profile:")
    prefs = extractor.user_preferences
    
    print(f"  Favorite genres: {', '.join([f'{genre}({count})' for genre, count in prefs['favorite_genres']])}")
    print(f"  Favorite styles: {', '.join([f'{style}({count})' for style, count in prefs['favorite_styles']])}")
    print(f"  Favorite artists: {', '.join([f'{artist}({count})' for artist, count in prefs['favorite_artists'][:5]])}")
    print(f"  Era preference: {prefs['era_preference']}")
    print(f"  Collection diversity: {prefs['diversity_score']:.2f}")
    
    print(f"\n✅ Feature extraction test completed successfully!")
    print(f"🎯 Ready for recommendation model training!")
    
    return extractor, features

if __name__ == "__main__":
    extractor, features = test_feature_extraction()