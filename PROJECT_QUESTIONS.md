# Project Clarification Questions & Responses

## Technical Architecture

### Feature Engineering & Data Sources:
**Question:** Beyond basic Discogs metadata (genres, artists, labels), should the model consider deeper features like production credits, collaborating musicians, recording studios, or even audio features?

**Your Response:**
I am open to this, and also open to the possibility of maybe adding these additional features at a later stage of the development.
Im also fine with adding these additional features during the model deployment and training time when we want to evaluate the performance of the model.

**Question:** Any plans to enrich Discogs data with other sources (MusicBrainz, Last.fm, Spotify APIs) for richer feature vectors?

**Your Response:**
Open to this possibility. I just want to not spend any money on API or data access and ideally want to use publicly available datasets.

### Model Architecture:
**Question:** For the 10-15 second latency constraint: real-time inference vs pre-computing recommendations for popular albums?

**Your Response:**
Open to both. Also open to maybe extending the latency to 25-30 seconds, but not more than that.

**Question:** Individual models per user vs shared model with user embeddings? The latter scales better but individual models might be more accurate.

**Your Response:**

I want to start off with individual model for V1. maybe expand to shared model at a later date.
**Question:** How to handle the cold start problem for users with small collections (<20 records)?

**Your Response:**
Good question.Not sure. any suggestions?

### Scalability Design:
**Question:** What's your target user count for V1? This affects whether individual models per user is feasible.

**Your Response:**
Myself only. Might share it on socials after for more feedback

**Question:** Model serving strategy: edge deployment, centralized inference, or hybrid?

**Your Response:**
Dont know much about either of these. would love to learn.

## Product & UX

### Recommendation Granularity:
**Question:** Just binary yes/no or confidence scores (e.g., "85% match")?

**Your Response:**
Confidence scores sound good.

**Question:** Different recommendation types: "Similar to your Radiohead albums" vs "Genre exploration opportunity" vs "Rare find based on your collection"?

**Your Response:**
This would be great to have, althoigh maybe for v2? For V1, a buy/dont buy score would be great.

### Learning Loop:
**Question:** How will the system learn from your actual purchases and satisfaction? Explicit thumbs up/down or implicit feedback?

**Your Response:**
I can enter both.

**Question:** Plan for handling when users disagree with recommendations?

**Your Response:**
Havent thought about this.

### Edge Cases:
**Question:** What happens when a record isn't in Discogs (especially for V2 barcode scanning)?

**Your Response:**
I dont think this problem will be a major one, because Discogs has a pretty extensive collection of data/meta data of most music.

**Question:** How to handle users with very niche collections where collaborative filtering might fail?

**Your Response:**
Not sure. I think lets not use collaborative filtering for v1?

## Implementation Preferences

### Tech Stack:
**Question:** Any preferences for frontend framework, backend language, ML framework, or cloud provider?

**Your Response:**
No preferences. Ideally I would like to use languages/frameworks that are currently used in data science/machine learning roles such as Python. But I want to use this

**Question:** Database strategy for user collections and model data?

**Your Response:**

Not sure what you mean by database strategy?
### Mobile Strategy:
**Question:** For V2 barcode scanning: PWA with camera access or native app development?

**Your Response:**
not sure what the difference is between these two?

**Question:** Offline capability requirements?

**Your Response:**
Dont think we need these for until v2.

## Final Question:
**Question:** The core challenge is balancing model accuracy with inference speed while scaling to multiple users. What's your gut feeling on starting with individual user models vs a shared architecture?

**Your Response:**
I think lets start with indiviudal model first, because I first want to build it for my own Discogs collection.

---

*Feel free to add any additional thoughts, constraints, or requirements below:*

1. What would be the evaluation metrics during the ML training?
2. How to create the test and validation datasets?
3.
