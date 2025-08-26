# Vinyl Recommendation System

A content-based vinyl record recommendation system that analyzes your Discogs collection to predict whether you'll like new albums.

## 🚀 Quick Start

1. **Clone and setup environment:**
   ```bash
   git clone <repository-url>
   cd vinyl_recommendation_project
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure Discogs API:**
   ```bash
   cp .env.example .env
   # Edit .env and add your Discogs user token and username
   ```

3. **Run the application:**
   ```bash
   python -m src.api.main
   ```

## 🏗️ Project Structure

```
vinyl_recommendation_project/
├── src/
│   ├── data/          # Data processing and API integration
│   ├── models/        # ML models and recommendation algorithms  
│   ├── api/          # FastAPI backend
│   └── frontend/     # React frontend (future)
├── tests/            # Unit and integration tests
├── notebooks/        # Jupyter notebooks for exploration
├── config/           # Configuration files
├── data/             # Data storage (gitignored)
└── models/           # Trained models (gitignored)
```

## 📊 Features

- **V1 Features:**
  - Sync with Discogs collection
  - Content-based album recommendations
  - Confidence scoring for buy/don't buy decisions
  - Mobile-first web interface
  - Individual personalized model

- **Future (V2) Features:**
  - Barcode scanning
  - Multi-user support
  - Recommendation explanations
  - Advanced feedback learning

## 🛠️ Development

- **Lint:** `black src/ && flake8 src/`
- **Test:** `pytest tests/`
- **Type check:** `mypy src/`

## 📝 Documentation

- [Project Plan](PROJECT_PLAN.md) - Detailed implementation roadmap
- [Project Questions](PROJECT_QUESTIONS.md) - Requirements and clarifications
- [Claude Instructions](CLAUDE.md) - AI assistant context