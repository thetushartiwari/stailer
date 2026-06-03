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
