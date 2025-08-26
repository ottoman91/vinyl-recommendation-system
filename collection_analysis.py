"""
Quick analysis of your Discogs collection to understand data patterns
"""
import pandas as pd
from collections import Counter
from src.data.cached_discogs_client import create_cached_discogs_client

def analyze_collection():
    """Analyze the collection data to understand patterns"""
    client = create_cached_discogs_client()
    if not client:
        print("❌ Failed to create client")
        return
    
    print("📊 Analyzing your vinyl collection...")
    collection = client.get_collection_items()
    
    if not collection:
        print("❌ No collection data found")
        return
    
    print(f"\n🎵 Collection Overview:")
    print(f"  Total Albums: {len(collection)}")
    
    # Artist analysis
    artists = [album.artist for album in collection]
    artist_counts = Counter(artists)
    print(f"\n🎤 Top Artists:")
    for artist, count in artist_counts.most_common(10):
        print(f"  {artist}: {count} albums")
    
    # Genre analysis
    all_genres = []
    for album in collection:
        all_genres.extend(album.genres)
    genre_counts = Counter(all_genres)
    print(f"\n🎸 Genre Distribution:")
    for genre, count in genre_counts.most_common():
        print(f"  {genre}: {count} albums")
    
    # Style analysis
    all_styles = []
    for album in collection:
        all_styles.extend(album.styles)
    style_counts = Counter(all_styles)
    print(f"\n🎭 Top Styles:")
    for style, count in style_counts.most_common(10):
        print(f"  {style}: {count} albums")
    
    # Year analysis
    years = [album.year for album in collection if album.year and album.year > 1900]
    if years:
        print(f"\n📅 Year Range:")
        print(f"  Earliest: {min(years)}")
        print(f"  Latest: {max(years)}")
        print(f"  Average: {sum(years) / len(years):.1f}")
        
        # Decade distribution
        decades = [(year // 10) * 10 for year in years]
        decade_counts = Counter(decades)
        print(f"\n📆 Decade Distribution:")
        for decade, count in sorted(decade_counts.items()):
            print(f"  {decade}s: {count} albums")
    
    # Label analysis
    all_labels = []
    for album in collection:
        all_labels.extend(album.labels)
    label_counts = Counter(all_labels)
    print(f"\n🏷️  Top Labels:")
    for label, count in label_counts.most_common(10):
        print(f"  {label}: {count} albums")
    
    # Format analysis
    all_formats = []
    for album in collection:
        all_formats.extend(album.formats)
    format_counts = Counter(all_formats)
    print(f"\n💿 Format Distribution:")
    for format_type, count in format_counts.most_common():
        print(f"  {format_type}: {count} albums")
    
    # Sample some albums for detailed inspection
    print(f"\n🔍 Sample Album Details:")
    for i, album in enumerate(collection[:5], 1):
        print(f"\n{i}. {album.artist} - {album.title} ({album.year})")
        print(f"   Genres: {', '.join(album.genres)}")
        print(f"   Styles: {', '.join(album.styles)}")
        print(f"   Labels: {', '.join(album.labels)}")
        print(f"   Formats: {', '.join(album.formats)}")
        if album.notes:
            print(f"   Notes: {album.notes}")
    
    return collection

if __name__ == "__main__":
    analyze_collection()