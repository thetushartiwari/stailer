# 👗 stAiler - AI-Powered Fashion Styling Studio

stAiler is a premium conversational fashion styling platform that maps a user's biometrics and color DNA to a curated clothing rack. It utilizes a **Single-LLM + Local ML hybrid architecture**:
- **Gemini 3.5 Flash** is called once per search request to parse high-level user intent and output a structured styling plan.
- **Local Machine Learning Models** (Logistic Regression for body shapes, KNN for skin tones, TF-IDF cosine similarity, and gradient-drift online feedback learning) perform all scoring, ranking, and validation in less than 5ms.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation & Setup

1. **Navigate to project directory**
   ```bash
   cd stailer_ecom
   ```

2. **Activate the virtual environment**
   ```bash
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install django pandas scikit-learn numpy pillow requests openpyxl
   ```

4. **Verify Database Migrations**
   ```bash
   python manage.py migrate
   ```

5. **Train Diagnostic Models**
   Fit the local supervised KNN and Logistic Regression classifiers:
   ```bash
   python manage.py train_diagnostic_models
   ```

6. **Start the local server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   Open your browser and navigate to: `http://127.0.0.1:8000/`

---

## 🏗️ Project Structure

```
stailer_ecom/
├── products/                   # Main styling app
│   ├── models.py              # UserProfile, UserPreference database schemas
│   ├── views.py               # View controllers & session blending logic
│   ├── recommendation_model.py # TF-IDF similarities & catalog builders
│   ├── stylist_engine.py      # Local ML classifiers & gradient feedback loops
│   ├── recommender/           # Core Pipeline Modules
│   │   ├── planner.py         # Gemini StylePlan generator
│   │   ├── scoring.py         # Local ML multi-factor scoring
│   │   ├── retrieval.py       # Candidate database retriever
│   │   ├── reranker.py        # Local ranking & confidence clamp
│   │   └── validator.py       # Guardrails, budget, and age checks
│   └── templates/             # Glassmorphic dark mode layout templates
├── stailer/                   # Django project configuration
├── scripts/                   # Automated validation check scripts
└── clothing_dataset.xlsx      # Sample product catalog dataset
```

---

## 📚 Interview & Presentation Preparation Guide

### 1. **How does the recommendation pipeline work?**
"We utilize a Single-LLM + Local ML hybrid pipeline. When a user enters a query, Gemini 3.5 Flash parses the semantic intent once to generate a structured StylePlan schema (such as occasion, formality, colors, and category lists). We then perform candidate retrieval from the SQLite database. Candidates are scored locally using a multi-factor formula weighing TF-IDF similarity, biometric body DNA, skin tone color harmony, historical likes/dislikes, and ratings. Reranking is completed locally in under 5ms, avoiding API latency and token limit issues."

### 2. **How do the body shape and skin tone features work?**
"We use supervised machine learning models trained locally using `scikit-learn` and pickled to `/ml_artifacts/`. 
- **Body Shape DNA:** Uses a Multi-Class Logistic Regression model. It inputs height, weight, bust, waist, and hips to calculate anthropological ratios and predicts the silhouette (Hourglass, Round, Rectangle, Athletic, Petite).
- **Skin Undertone:** Uses a KNN classifier. It samples webcam RGB pixels to predict the color undertone (Fair, Medium, Olive, Deep)."

### 3. **How does the system learn user preferences in real-time?**
"We implemented a dynamic gradient-drift learning algorithm. When a user likes or dislikes a clothing item, a background process updates their profile's style, fit, and color weights (likes drift weights +0.08 closer, dislikes push weights -0.15 further away). The local scorer incorporates these personalized weights on subsequent searches, causing the recommendations to shift dynamically."

### 4. **How do you handle cold start or empty prompts?**
"If the prompt is empty (e.g. landing page load or DNA diagnostic submit), we skip the Gemini API call entirely. The local ranker runs instantly (in <5ms) and relaxes its thresholds to `0.0`, dynamically backfilling the rack with catalog products matching the user's gender and DNA parameters."
