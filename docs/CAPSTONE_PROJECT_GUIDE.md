# stAiler AI Styling Studio: Capstone Project & Presentation Defense Guide

This guide serves as your comprehensive reference manual to explain, present, and defend **stAiler** for your capstone project defense or technical presentation.

---

## 1. Project Vision, Problem Statement & Solution

### A. The Problem Statement (The E-Commerce Gap)
- **Generic Grid Paradigms:** Standard e-commerce platforms (like Myntra or Amazon) present users with massive, generic grids of products. They rely on search keyword indexing, which fails to capture subjective styling intents (e.g. *"something sleek for a fancy birthday dinner"*).
- **The Cold-Start Problem:** When a new user lands on a site, the system has no historical clicks to personalize recommendations. Most collaborative filtering engines fail here.
- **Physical & Aesthetic Disconnect:** Traditional recommenders do not take into account the user's specific **body DNA proportions** (structural silhouette shape, height, and weight/BMI scale) or **skin tone palette**, leading to items that look good on a flat screen but do not suit the customer in real life.
- **High Latency & Costs of LLMs:** Running raw large language models (LLMs) to scan and recommend thousands of catalog items live is slow, cost-prohibitive, and frequently fails due to API timeouts.

### B. The stAiler Solution
stAiler is a premium, conversational fashion diagnostic studio. It replaces the product grid on landing with a **diagnostic console** that maps user DNA to a **Curated Wardrobe Rack** using a **Hybrid Single-LLM + Local ML Architecture**:
- **Privacy-First Diagnostics:** Samples webcam pixels (skin tone) and biometrics (body shape) locally without saving photos or personal data to the database.
- **Decoupled Biometrics:** Evaluates structural skeletal proportions (e.g., Hourglass, Rectangle, V-Taper) independently from scale (BMI categories: Thin, Normal, Overweight, Obese) and height vertical draping constraints.
- **Kids-Optimized Experience**: Dynamically detects kids onboarding and skips irrelevant adult biometric scanning forms, streamlining the user experience.
- **Conversational Memory:** Uses Django session memory context blending to understand follow-up queries.
- **Micro-Scoring Engine:** A fast local machine learning algorithm that scores, ranks, and serves recommendations in less than 5ms.
- **Live AI Query Planning:** Calls Gemini 3.5 Flash once per search request strictly to parse user intent and construct a structured styling plan, achieving high uptime and fast responses.
- **Strictly Curated Display**: Enforces a strict limit of exactly 6 recommendations, locked to the user's onboarded gender, with a robust two-pass fallback backfill mechanism to guarantee rack filling.

---

## 2. Technical System Architecture & Code Flow

The application divides duties between the **Cloud LLM (Gemini 3.5 Flash)** and **Local ML Classifiers/Math**:

```
 ┌────────────────────────────────────────────────────────┐
 │                     User Input                         │
 │  (Prompt: "clothes for college" + Biometric DNA Form)  │
 └──────────────────────────┬─────────────────────────────┘
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │            Django View: recommendations_page()         │
 └──────────────────────────┬─────────────────────────────┘
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │       LLM Intent Parser: create_style_plan()           │
 │ - Calls Gemini 3.5 Flash via REST HTTP API             │
 │ - Outputs structured JSON StylePlan schema             │
 └──────────────────────────┬─────────────────────────────┘
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │      Candidate Retrieval: retrieve_candidates()        │
 │ - Filters SQLite database by gender & budget           │
 │ - Restricts pool to Gemini's targeted categories       │
 └──────────────────────────┬─────────────────────────────┘
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │        Local ML Scoring: score_candidates()            │
 │ - TF-IDF text similarity against query (36%)           │
 │ - Metadata planned category matches (22%)              │
 │ - Body Shape & Silhouette Match (16%)                  │
 │ - Skin Tone Color Harmony (10%)                        │
 │ - Bayesian Average Catalog Ratings (10%)               │
 │ - User Like/Dislike Feedback Logs (6%)                 │
 └──────────────────────────┬─────────────────────────────┘
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │            Local Reranking: local_rerank()             │
 │ - Sorts, validates (budget, category rules), and       │
 │   selects exactly 6 products                           │
 │ - Runs a second pass backfill if results are < 6       │
 │ - Returns curated rack instantly in < 5ms              │
 └────────────────────────────────────────────────────────┘
```

---

## 3. Codebase File Directory Walkthrough

Here is a directory of the core files you developed and their responsibilities:

### A. Core Django Web App
- [models.py](file:///c:/Users/tushx/Desktop/Documents/Projects/stailer_ecom/products/models.py): Establishes database tables:
  - `Product`: Catalog items containing name, brand, category, category type, price, image, rating, fit, colors, and style tags.
  - `UserProfile`: Saves diagnosed biometric variables (height, weight, bust, waist, hips), predicted body type, predicted BMI category, onboarded gender, and skin tone.
  - `UserPreference`: Logs AJAX likes and dislikes (❤️/💔) mapped to a user session.
- [views.py](file:///c:/Users/tushx/Desktop/Documents/Projects/stailer_ecom/products/views.py): Web controllers:
  - `diagnose_dna()`: Captures form biometrics, runs local classifiers, saves BMI category and gender, and redirects. Handles Kids flow logic bypassing.
  - `recommendations_page()`: Assembles context history, calls the recommendation service, locks filters to the profile's gender, and serves the curated rack.
  - `refine_prompt()`: Blends follow-up conversation prompts in session memory, fetches new recommendations (exactly 6), and returns JSON to frontend.
  - `toggle_like()`: Handles dynamic affinity updates and returns 6 fresh recommendations.

### B. Core Recommendation Service (`products/recommender/`)
- [planner.py](file:///c:/Users/tushx/Desktop/Documents/Projects/stailer_ecom/products/recommender/planner.py): Handles styling plans. Calls Gemini 3.5 Flash live with strict JSON schema constraints. Instructs Gemini to use biometric DNA traits (skin tone, body shape, BMI category, height) when determining color directions and styling fit strategies. Contains a local keyword-similarity fallback mechanism if offline.
- [retrieval.py](file:///c:/Users/tushx/Desktop/Documents/Projects/stailer_ecom/products/recommender/retrieval.py): Pulls candidate products from the database, applying filters, and executes a local TF-IDF similarity calculation.
- [scoring.py](file:///c:/Users/tushx/Desktop/Documents/Projects/stailer_ecom/products/recommender/scoring.py): The local multi-factor scorer. Combines semantic vector similarity, body shape match, scale/BMI category drape checks, height draping guidelines, skin tone harmony, catalog rating, and user feedback logs into a consolidated score.
- [explanations.py](file:///c:/Users/tushx/Desktop/Documents/Projects/stailer_ecom/products/recommender/explanations.py): Prioritizes explainable AI (XAI) feedback badges so that body DNA, proportions, height draping, and user preferences appear first, ahead of general text matches.
- [reranker.py](file:///c:/Users/tushx/Desktop/Documents/Projects/stailer_ecom/products/recommender/reranker.py): Sorts candidates by their ML scores and enforces dynamic confidence filters.
- [service.py](file:///c:/Users/tushx/Desktop/Documents/Projects/stailer_ecom/products/recommender/service.py): Coordinates the pipeline and runs the **two-pass backfilling mechanism** to guarantee exactly 6 recommendations.
- [validator.py](file:///c:/Users/tushx/Desktop/Documents/Projects/stailer_ecom/products/recommender/validator.py): Protects recommendation integrity (checks budget maximums, blocks adult clothes for kids profiles, and flags audience contradictions).

### C. Offline ML Pipelines
- [stylist_engine.py](file:///c:/Users/tushx/Desktop/Documents/Projects/stailer_ecom/products/stylist_engine.py): Manages local machine learning classifiers. Contains the body shape predictor (Logistic Regression) and the skin tone predictor (KNN). Houses the gradient-drift online preference learning algorithm.
- [recommendation_model.py](file:///c:/Users/tushx/Desktop/Documents/Projects/stailer_ecom/products/recommendation_model.py): Manages the TF-IDF representation, constructs similarity matrices, and saves/loads in-memory singletons.
- [train_diagnostic_models.py](file:///c:/Users/tushx/Desktop/Documents/Projects/stailer_ecom/products/management/commands/train_diagnostic_models.py): Management command to train, evaluate, and pickle classifiers (`body_classifier.pkl` and `skin_classifier.pkl`).

---

## 4. The AI/ML Formulations

You must be prepared to write down these mathematical formulations during a project defense:

### A. Body Silhouette Softmax Classifier (Logistic Regression)
Inputs are mapped to a biometric vector $\mathbf{x} = [r_{\text{bw}}, r_{\text{hw}}, r_{\text{bh}}, \text{BMI}]$.
We calculate class probabilities for structural body shapes using the Softmax function:
$$P(y = k \mid \mathbf{x}) = \frac{e^{\mathbf{w}_k^T \mathbf{x} + b_k}}{\sum_{j=1}^{K} e^{\mathbf{w}_j^T \mathbf{x} + b_j}}$$

### B. Decoupled BMI Scale (Scale) & Height Rules (Stature)
1. **BMI Category**: Calculated independently from silhouette:
   $$\text{BMI} = \frac{\text{Weight (kg)}}{\text{Height (m)}^2}$$
   * $\text{BMI} < 18.5$: *Thin*
   * $18.5 \le \text{BMI} < 25.0$: *Normal*
   * $25.0 \le \text{BMI} < 30.0$: *Overweight*
   * $\text{BMI} \ge 30.0$: *Obese*
2. **Height Draping**: Applied to enforce vertical styling guidelines:
   * $\text{Height} < 158\text{cm}$: *Petite* (favors cropped cuts, monochrome fits, vertical elements to elongate stature)
   * $\text{Height} > 175\text{cm}$: *Tall* (favors maxi lengths, oversized layers, and tunics to complement long lines)

### C. Skin Undertone Classifier (K-Nearest Neighbors)
We sample the webcam target area RGB values as $\mathbf{x}_{\text{skin}} = [R, G, B]$. The classification assigns the mode category of its closest neighbors:
$$\hat{y} = \text{Mode}(\{y_i \mid \mathbf{x}_i \in N_k(\mathbf{x}_{\text{skin}})\})$$

### D. Self-Learning Preference Drift (Online Gradient Descent)
User preference affinity is a continuous weight vector $\mathbf{U}_t = [\mathbf{W}_{\text{style}}, \mathbf{W}_{\text{fit}}, \mathbf{W}_{\text{color}}]$. On Like/Dislike action on product features $\mathbf{V}_i$, the vector drifts dynamically:
$$\mathbf{U}_{t+1} = \mathbf{U}_t + \eta \cdot \mathbf{V}_i$$
* $\eta = +0.08$ for Likes (positive update gradient).
* $\eta = -0.15$ for Dislikes (negative penalty gradient).

### E. Cosine Similarity Formula (TF-IDF Vector Space)
Calculates semantic matching between the text search query vector $\mathbf{q}$ and the product text vector $\mathbf{d}_i$:
$$\text{CosineSimilarity}(\mathbf{q}, \mathbf{d}_i) = \frac{\mathbf{q} \cdot \mathbf{d}_i}{\|\mathbf{q}\| \|\mathbf{d}_i\|} = \frac{\sum_{j=1}^{V} q_j d_{i,j}}{\sqrt{\sum_{j=1}^{V} q_j^2} \sqrt{\sum_{j=1}^{V} d_{i,j}^2}}$$

---

## 5. Potential Panel Q&A (Defense Preparation)

### Q1: Why did you choose a hybrid LLM + Local ML architecture instead of letting the LLM do all the recommendations?
**A:** "A full LLM flow requires sending our entire product catalog descriptions over the network. This creates a massive payload, leading to high latencies (3-5+ seconds) and API timeout/truncation errors. Furthermore, LLMs cannot query database state live. By splitting duties—using Gemini strictly once to parse search intent into a structured schema (the style plan) and using local Python models (TF-IDF, KNN, Logistic Regression) to retrieve and score candidates—we reduced latency to under 1 second, eliminated token truncation, and ensured the app works offline."

### Q2: What happens if a user submits an empty query prompt? Does the AI fail?
**A:** "No. If the prompt is empty, the planner detects the empty state and bypasses the Gemini API call completely to avoid wasting network tokens. It falls back to our local ML scoring engine. We scale the minimum score thresholds to `0.0` to dynamically fill the rack with catalog products matching the user's predicted body DNA silhouette and skin undertone."

### Q3: How do you protect user privacy when sampling skin tone from the webcam?
**A:** "The webcam feed is processed entirely ephemerally. The in-browser JavaScript samples the RGB coordinates of the center canvas frame and sends only the 3 numerical integers `[R, G, B]` to the Django backend. No images, videos, or camera files are sent to the cloud or saved to the server's disk, ensuring complete user privacy."

### Q4: How does the system handle cold-starts for new users?
**A:** "Through biometric input. Before showing any products, the user completes the diagnostic form. Our Logistic Regression and KNN models predict their body DNA and skin color undertone. This gives us immediate styling filters (colors, fits) to curate recommendations without requiring any historical shopping data."

### Q5: How would you scale this catalog from 920 products to 1,000,000 products?
**A:** "In a production setting, we would replace the local Django ORM queries with a **Vector Database** (like Pinecone or Milvus). We would precompute product text embeddings using a sentence transformer model (like BERT or CLIP) and index them. Stage 1 retrieval would fetch the top 100 closest vector matches from the vector DB, and our local ML scorers would rank only those 100 items, keeping the search latency under 50ms at scale."

### Q6: Why did you decouple body silhouette shape and BMI categories?
**A:** "A person's structural body silhouette (e.g. Hourglass shape) is defined by their structural skeletal proportions (ratios of bust, waist, hips), not their weight class. A person can have an hourglass shape whether they are thin or overweight. By separating structural shape from BMI categories, stAiler can recommend silhouettes that flatter their proportions (e.g., waist definition) while adapting the garment's fit and drape (e.g., relaxed vs. slim cuts) based on their height and BMI, ensuring the recommendations are highly tailored and body-positive."

### Q7: Why skip the biometric diagnostic step for kids onboarding?
**A:** "Standard biometric styling indices (bust-to-waist, hips-to-waist ratios) are developed adult metrics and do not apply to children's garments. For kids, sizing is age/height dependent rather than contour-dependent. Skipping Step 3 (the webcam color sampling is kept for color matching, but the body-shape scanning is skipped) stream-lines onboarding for parents, proceeding directly to the styling prompt and locking results to kids' categories."

### Q8: Why did you restrict the recommendation rack to exactly 6 items and a locked gender curation badge?
**A:** "stAiler is a bespoke styling studio, not a massive discount warehouse. Presenting endless rows of mixed clothing dilutes the luxury 'curated rack' experience. Enforcing a strict 6-product limit keeps the presentation clean and highly focused. Standard gender tabs were removed because switching genders in the middle of a personalized styling session breaks the personalization premise. Locking the feed to the onboarded profile gender and using a two-pass backfilling algorithm ensures the user always gets exactly 6 highly relevant, gender-consistent recommendations."

---

## 6. Deep Dive: Biometric & Color DNA Recommendation Mechanics (Logic & Match)

This section explains the core design logic and matching mechanics of how biometric measurements and skin tone data actually influence styling recommendations, and how the explanations shown below the items are dynamically generated based on active matches.

### A. Skin Tone (Matching Color DNA)
1. **The Logic**:
   - **Harmony Mapping**: Every skin tone (Fair, Medium, Olive, Deep) is mapped to a curated set of harmonious color palettes based on professional styling guidelines:
     - **Fair**: Cool undertones like `Pastel Blue`, `Lavender`, `Pink`, `Cherry`, `Silver`, `Black`, `White`.
     - **Medium**: Warm earth undertones like `Mustard`, `Gold`, `Cream`, `Tan`, `Rust Red`, `Teal`, `Navy Blue`, `Beige`, `Brown`.
     - **Olive**: Warm/Neutral undertones like `Peach`, `Burgundy`, `Charcoal`, `Gold`, `Beige`, `Cream`, `Tan`, `Brown`.
     - **Deep**: Vibrant rich tones like `Crimson Red`, `Gold`, `Royal Blue`, `Emerald Green`, `Deep Purple`, `Orange`, `Yellow`, `Black`, `White`.
   - **Dynamic Token Matching**: Rather than relying on simple exact string comparisons (which fail when comparing database color tokens like `["olive", "green"]` with styling keywords like `"olive green"`), the system tokenizes the palettes dynamically to intersect single-word keywords.
2. **The Match**:
   - The engine extracts product colors from the catalog item's title, style tags, and description.
   - It performs a Jaccard Similarity intersection to check if any extracted colors match the user's color DNA.
   - If a match is found, the item receives a priority scoring boost.
   - The engine dynamically identifies *exactly* which colors matched and prints a customized badge:
     * *Example:* **`"The Olive Green tones match your Medium Skin DNA"`** (replaces hardcoded strings).

### B. Body Shape & Weight (Matching Silhouette & Scale)
1. **The Logic**:
   - **Silhouette Structure (Bone Structure & Proportions)**: Structural body frames look best in specific cuts and tailoring:
     - **Hourglass**: Flattered by `Tailored`, `Fit`, `Flare`, `Saree`, `Lehenga`, `Bodycon` cuts that accentuate the waist.
     - **V-Taper**: Flattered by `Structured`, `Tailored`, `Slim`, `Blazer`, `Suit`, `Double-Breasted` cuts that complement the upper torso.
     - **Trapezoid**: Flattered by `Regular`, `Slim`, `Chinos`, `Classic` cuts.
   - **Scale (BMI & Weight Drape)**: Weight categories (Thin, Normal, Overweight, Obese) determine clothing volume:
     - **Thin**: Favors `Slim`, `Fitted`, `Cropped`, `Bodycon`, `Tight` cuts to prevent the body from looking swallowed by fabric.
     - **Overweight/Obese**: Favors `Relaxed`, `Loose`, `Straight`, `Flowy`, `Vertical Stripe` drapes to provide structured comfort.
2. **The Match**:
   - The system checks if the product title, category, description, fit, or style tags contain any of these terms.
   - Matching products receive a scoring boost.
   - The engine lists the matched terms dynamically:
     * *Example (Silhouette):* **`"The Fit, Flare detailing flatters your Hourglass Body DNA"`**
     * *Example (Scale):* **`"The Relaxed drape fits your overweight proportions"`**

### C. Height (Matching Length & Proportions)
1. **The Logic**:
   - Height governs structural length and vertical spacing.
   - **Petite (< 158cm)**: Rules favor shorter lengths (`Short`, `Cropped`, `Vertical`, `Monochrome`, `Slim`) to visually elongate the legs and torso.
   - **Tall (> 175cm)**: Rules favor elongated lengths (`Maxi`, `Oversized`, `Layered`, `Long`, `Tunic`, `Draped`) to balance taller statures.
2. **The Match**:
   - The system checks the garment's fit and descriptions for these height-suiting elements.
   - Matching items get prioritized.
   - It prints a dynamic explanation:
     * *Example (Petite):* **`"The Cropped cut visually flatters petite stature"`**
     * *Example (Tall):* **`"The Oversized, Layered proportions fit tall stature"`**

