# 👗 stAiler – AI-Powered Fashion Styling Studio

stAiler is a premium conversational fashion styling platform that maps a user's biometrics and color DNA to a curated clothing rack using a **Single-LLM + Local ML hybrid architecture**:

- **Gemini Flash** is called once per search request to parse high-level user intent and output a structured styling plan.
- **Local Machine Learning Models** (Logistic Regression for body shapes, KNN for skin tones, TF-IDF cosine similarity, and gradient-drift online feedback learning) perform all scoring, ranking, validation, and rendering in < 5ms.

---

## ✨ Core Features

| Feature | Description |
|---|---|
| **Studio Diagnostic Console** | Glassmorphic, dark-mode landing screen with a multi-step biometric wizard and a quick-search bypass bar |
| **Natural Language Biometrics** | Users can type `"I'm 5'8, medium skin, hourglass"` directly in the search bar — stAiler extracts and applies the DNA automatically |
| **Webcam Skin Scanner** | Ephemerally samples camera RGB values and runs a local KNN classifier to map users to Fair, Medium, Olive, or Deep palettes |
| **Decoupled Biometric Engine** | Structural body silhouette (shape proportions) evaluated independently from BMI scale (weight drape) and height (vertical draping) |
| **Dynamic XAI Badges** | Specific match reasons injected per product — never hardcoded. E.g. *"Olive Green tones match your Medium Skin DNA"*, *"Tailored cut flatters Hourglass Body DNA"* |
| **Gender-Locked Curation** | Recommendations strictly locked to the user's onboarded gender with cross-gender query blocking |
| **Conversational Session Memory** | Blends dialogue context using Django session history — follow-up queries maintain previous context |
| **Two-Pass Backfill** | Guarantees exactly 6 recommendations even when catalog inventory is sparse |
| **Online Drift Learning** | Like/dislike clicks dynamically shift style, fit, and color affinity weights in real time |
| **Reset & Direct Query** | Users can reset their DNA and query from the recommendations page directly — NLP extraction active in this state |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- pip

### Installation & Setup

```bash
# 1. Navigate to project directory
cd stailer_ecom

# 2. Activate virtual environment
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# 3. Install dependencies
pip install django pandas scikit-learn numpy pillow requests openpyxl

# 4. Apply database migrations
python manage.py migrate

# 5. Train local diagnostic classifiers
python manage.py train_diagnostic_models

# 6. Start the server
python manage.py runserver

# 7. Open in browser
# http://127.0.0.1:8000/
```

---

## 🎯 Two Entry Paths

### Path 1 — Full Diagnostic Wizard (4 Steps)
```
Landing Hero
  → Step 1: Identity (Name, Age, Height, Weight, Gender)
  → Step 2: Skin Tone (Webcam scan or manual selector)
  → Step 3: Body Silhouette (Measurements or manual chip)
  → Step 4: Style Query ("wedding outfit", "casual summer")
  → /recommendations/ with full DNA scoring active
```

### Path 2 — Quick Bar Bypass (Natural Language)
```
Landing Hero Quick Bar:
  "I'm 5'8, medium skin, hourglass — women's wedding outfits under ₹2000"
  ↓
  NLP Biometric Extractor runs automatically:
    height_cm = 172.72  ← parsed from "5'8"
    skin_tone = "Medium" ← parsed from "medium skin"
    body_type = "Hourglass" ← parsed from "hourglass"
  ↓
  /recommendations/ with full DNA scoring active
```

### Path 3 — Post-Reset Direct Query
```
User clicks "Reset Styling DNA"
  → Profile wiped (all biometrics, preferences cleared)
  → /recommendations/ shows All/Men/Women/Kids gender tabs
  → Refine bar shows: "e.g. I'm 5'6, fair skin, pear shape — casual ethnic wear"
  → NLP extraction active: biometrics extracted from chat query
  → First match triggers full DNA scoring
```

---

## 🏗️ Project Structure

```
stailer_ecom/
├── products/                        # Main styling app
│   ├── models.py                    # UserProfile, UserPreference database schemas
│   ├── views.py                     # View controllers + NLP biometric patch logic
│   ├── stylist_engine.py            # Local ML classifiers + gradient feedback loops
│   ├── recommendation_model.py      # TF-IDF similarity + catalog builders
│   └── recommender/                 # Core Pipeline Modules
│       ├── biometric_extractor.py   # NLP natural language biometric parser [NEW]
│       ├── planner.py               # Gemini StylePlan generator + local fallback
│       ├── scoring.py               # Multi-factor local ML scorer
│       ├── retrieval.py             # Candidate DB retriever (TF-IDF + filters)
│       ├── explanations.py          # XAI badge prioritization engine
│       ├── reranker.py              # Local ranking + confidence clamping
│       ├── service.py               # Recommendation coordinator + two-pass backfill
│       └── validator.py             # Guardrails: budget, age, gender checks
├── templates/products/
│   ├── base.html                    # Shared nav (logo/Stylist Studio → /reset/)
│   ├── landing.html                 # Wizard + Quick Bypass Bar
│   └── recommendations.html        # Curated Rack + Conditional refine bar
├── stailer/                         # Django project configuration
├── docs/                            # Technical documentation + defense guides
│   ├── plan.md                      # System Architecture & API Blueprint
│   ├── PROJECT_ANALYSIS.md          # Technical summaries and algorithm deep-dives
│   └── CAPSTONE_PROJECT_GUIDE.md    # Capstone defense Q&A reference manual
└── clothing_dataset.xlsx            # Sample product catalog dataset (~920 items)
```

---

## 🧠 NLP Biometric Extractor

The `biometric_extractor.py` module parses natural language to extract biometric signals:

| Signal | Example Phrases | Output |
|--------|----------------|--------|
| Height | `"5'8"`, `"5 feet 8"`, `"172cm"`, `"1.65m"` | `height_cm: 172.72` |
| Skin tone | `"medium skin"`, `"fair complexion"`, `"olive"`, `"deep tone"` | `skin_tone: "Medium"` |
| Body type | `"hourglass"`, `"pear shaped"`, `"v-taper"`, `"athletic build"` | `body_type: "Hourglass"` |
| Weight | `"60kg"`, `"132 lbs"`, `"60 kilos"` | `weight_kg: 60.0` |

**Non-destructive:** Only fills fields that weren't already set by the wizard form. Wizard data always takes priority.

---

## 📊 Scoring Weights

| Factor | Weight | What it measures |
|--------|--------|-----------------|
| TF-IDF Semantic Match | 36% | Cosine similarity of prompt vs. product text |
| Metadata Category Match | 22% | Planned categories & style types vs. product |
| Body Shape & Scale | 16% | Structural silhouette + BMI drape + height fit |
| Skin Tone Color Harmony | 10% | Jaccard similarity of skin palette vs. product colors |
| Catalog Rating | 10% | Bayesian average product rating |
| Like/Dislike Feedback | 6% | Dynamic affinity drift from user actions |

---

## 🔒 Gender Lock Behaviour

| State | Behaviour |
|-------|-----------|
| Diagnosed (wizard/quick bar) | Locked to profile gender. Cross-gender queries return 0 results with explanation |
| Post-reset (undiagnosed) | All/Men/Women/Kids tabs visible. No lock active |
| Clicking logo or "Stylist Studio" | Full reset — profile wiped, redirected to landing |

---

## 🧪 Running Tests

```bash
# NLP extractor smoke test
python scripts/verify_recommender.py

# Full integration test (all scenarios)
python scripts/verify_stylist.py
```
