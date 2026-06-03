# Complete Technical Analysis: Stailer AI Styling Studio

## 1. COMPLETE TECHNICAL SUMMARY

### Core Idea
stAiler is a premium conversational fashion styling studio that maps a user's biometrics and color DNA to a curated clothing rack. The system uses a **Single-LLM + Local ML hybrid architecture**:
1. An LLM (Gemini 3.5 Flash) is called **once** per search request to parse high-level user intent and output a structured `StylePlan` schema.
2. A fast, local multi-factor ML algorithm ranks, scores, and filters products in less than 5ms based on body shapes, skin undertones, TF-IDF cosine similarity, and real-time user feedback.

---

### Workflow

**User Interaction Flow:**
1. **Landing Page Diagnostic (`/`)**:
   - Capture user height, weight, bust, waist, and hips.
   - Sample webcam RGB pixels for skin undertone.
   - Input initial search prompt.
2. **Post DNA Diagnostic**:
   - Save biometrics to `UserProfile` table.
   - **Local ML Body Classifier** (`body_classifier.pkl` Logistic Regression) predicts body silhouette.
   - **Local ML Skin Classifier** (`skin_classifier.pkl` KNN) predicts skin undertone.
   - Redirects to curated rack (`/recommendations/`).
3. **Conversational Refiner Console**:
   - Displays diagnosed Style DNA chips in a sticky header.
   - User types follow-up styling commands (e.g. `"softer colors"`, `"add denim"`).
   - Server blends dialogue context using Django session memory, translates intent, and refreshes the recommendations grid via AJAX.
4. **Interactive Action Loop**:
   - Clicking Like (❤️) or Dislike (💔) runs a local gradient-drift self-learning algorithm that shifts the user's style, fit, and color weights.
   - Card displays Explainable AI (XAI) glow-badges detailing why the item matches their DNA.

---

### Recommendation Generation Flow

1. **Intent Translation (LLM - Gemini 3.5 Flash)**:
   - Takes prompt and biometrics, outputs `StylePlan` JSON detailing targets: categories, category types, colors, occasion, and custom stylist message.
2. **Candidate Retrieval (Database)**:
   - Queries SQLite `Product` table filtering by gender and budget.
   - Restricts candidates to Gemini's targeted categories and types.
3. **Local Scoring Engine (Real-Time ML/Math)**:
   - Runs TF-IDF similarity between query and product descriptions.
   - Computes color palette compatibility with the user's skin undertone.
   - Matches silhouette styling guidelines with the user's body shape.
   - Incorporates historical feedback (likes/dislikes) and catalog quality ratings.
4. **Local Reranking**:
   - Sorts candidate products by consolidated score and takes the top 12.
   - Bypasses any second LLM call, eliminating token limitations and latency.

---

### Algorithms Used

#### 1. Biometric DNA Predictor (Softmax Multi-Class Logistic Regression)
- **Model**: Trained in `scikit-learn` on engineered body features: Bust/Waist, Hips/Waist, Bust/Hips, and BMI.
- **Classes**: Hourglass, Round, Rectangle, Athletic, and Petite.
- **Location**: `predict_body_shape()` in `products/stylist_engine.py` (loads `body_classifier.pkl`).

#### 2. Skin Color Classifier (KNN)
- **Model**: K-Nearest Neighbors model trained on skin RGB distributions.
- **Classes**: Fair, Medium, Olive, and Deep.
- **Location**: `predict_skin_tone_from_rgb()` in `products/stylist_engine.py` (loads `skin_classifier.pkl`).

#### 3. Semantic Search Vectorizer (TF-IDF & Cosine Similarity)
- **Model**: `sklearn.feature_extraction.text.TfidfVectorizer`
- **Location**: `build_similarity_matrix()` in `products/recommendation_model.py` (loads `tfidf_vectorizer.pkl`).
- **Purpose**: Computes mathematical cosine similarities on product texts, handling keyword search locally in 5ms.

#### 4. Jaccard Similarity (Color Matching)
- **Formula**: `intersection(colors1, colors2) / union(colors1, colors2)`
- **Purpose**: Measures color overlap between products and skin-tone palettes.

#### 5. Online Statistical Learning (Dynamic Affinity Drift)
- **Learning Step Coefficients**: Likes pull style/fit weights (+0.08); dislikes push weights away (-0.15).
- **Location**: `update_preferences()` in `products/stylist_engine.py`.

---

### Exact Tech Stack
- **Backend**: Python 3.12, Django 5.2.7 (MVT, ORM, Django Sessions)
- **ML & Data**: scikit-learn 1.7.2, pandas 2.3.3, numpy 2.3.3
- **LLM API**: Gemini 3.5 Flash (via REST Requests, JSON Schema Enforcement)
- **Frontend**: Vanilla JavaScript (AJAX Fetch API), HTML5 Canvas, CSS Grid (Dark Mode Glassmorphism)
- **Database**: SQLite3
