# stAiler AI Styling Studio: Complete End-to-End System Design & Final Implementation

This document provides the final, verified **AI/ML and Software Engineering Blueprint** for **stAiler**, a premium conversational fashion styling studio utilizing a hybrid single-LLM + local ML architecture.

---

## 1. System Architecture & Routing Flow

Instead of a generic e-commerce grid, **stAiler** is structured around a **diagnostic-to-curated-rack** pipeline. The catalog is hidden on landing, establishing the premium feel of a bespoke digital styling studio.

```
[ LANDING PAGE (/) ]
- Capture Webcam Skin Tone (Base64 Stream)
- Input Biometrics (Height, Weight, Bust, Waist, Hips)
- Enter Initial Prompt ("What are we styling today?")
       │
       ▼ (POST Diagnostic Payload & Save to UserProfile)
[ RECOMMENDATIONS VIEW (/recommendations/) ]
- Renders Curated Wardrobe Rack (Exactly 6 items)
- Displays diagnosed Style DNA tags in Sticky Banner
- Locked to Onboarded Gender Curation Badge
- Floating Refiner Prompt Bar (Follow-up messages)
       │
       ├──► User Clicks Like (❤️) ──► AJAX Recalculates Affinities ──► Rack Refreshes
       ├──► User Clicks Dislike (💔) ──► AJAX Demotes & Slides Card Out ──► New Product In
       └──► User Enters Refinement ──► Blends with Session Memory ──► Rack Refreshes
```

---

## 2. Page & Component Specifications

### A. Landing Page (`/` - The "Studio Diagnostic Console")
* **Visual Theme**: Dark mode, glassmorphic layout, high contrast glowing accent colors (cyan, magenta, gold). **Contains no products.**
* **Pillar 1: Skin Tone Webcam Scanner**:
  * Camera video container with a circular target overlay.
  * Javascript color sampler running in-browser canvas frame analysis.
  * Triggers KNN classifier on the backend to predict: **Fair, Medium, Olive, or Deep**.
  * Shows corresponding color palette preview.
* **Pillar 2: Body Silhouette & Height Diagnostic**:
  * Clean form fields prompting for: **Height (cm), Weight (kg), Bust (in), Waist (in), and Hips (in)**.
  * Inputs are analyzed by a local styling engine to predict structural silhouette class and BMI category independently.
  * **Adaptive Kids Flow**: If the selected gender is "Kids", the Step 3 biometric body-shape scanner/estimation step is skipped dynamically. The step indicator dot is hidden, and the wizard proceeds directly to Step 4 (Style Query), since adult proportions do not apply to children.
* **Pillar 3: Primary Prompt Console**:
  * A centered, glowing conversational input bar: *"What are we styling today? (e.g. minimalist casual outfit, traditional wedding guest look...)"*
* **Pillar 4: Begin Styling Button**:
  * Compiles all parameters, updates `UserProfile`, and redirects to `/recommendations/`.

### B. Recommendations Page (`/recommendations/` - The "Curated Wardrobe")
* **Sticky DNA Status Banner**:
  * Visual chips reflecting diagnosed traits: `[🎨 Olive Skin]` `[👤 Hourglass Shape / Normal Proportions]` `[📏 Average Height]`.
* **Curation Restriction (Gender Locking)**:
  * Interactive gender selector tabs are removed to protect styling context.
  * Renders a static, glowing curation badge (e.g., `Men's Curation`, `Women's Curation`, `Kids' Curation`) aligning to the onboarded profile gender.
  * Django views enforce fallback to the user's saved profile gender if no explicit gender param is passed.
* **Refiner prompt Console**:
  * Smaller, floating search console at the top of the feed: *"Refine your style (e.g. 'not this, softer colors', 'add matching trousers')."*
* **Personalized Wardrobe Rack (Grid)**:
  * **Strict Limit**: Exactly 6 curated clothing cards matching their query. If the inventory of matching items is low, a **two-pass backfilling mechanism** relaxes the minimum confidence check to ensure the rack is always populated with 6 items.
  * **Explainable AI (XAI) Badges**: Glow-chips explaining recommendation weights (e.g., *"Silhouette structure aligns with hourglass body shape"*, *"Garment drape fits normal proportions"*).
  * **XAI Badge Prioritization**: Explanations display up to 3 badges, sorted by priority. High-priority biometric tags (body shape shape, skin tone, height proportions, and user feedback) are placed first, ensuring the user gets clear transparency into their Diagnosed DNA matches over generic search matches.
  * **Interactive Actions**:
    * **Like (❤️)**: Triggers dynamic affinity drift and re-ranks feed via AJAX.
    * **Dislike (💔)**: Triggers a CSS slide-out animation to remove card; pulls a new recommended item from backend to replace it.
    * **Add to Cart (🛒)**: Session-based shopping cart increment.

---

## 3. Conversational Session Memory Pipeline

To support follow-up adjustments (e.g. knowing that *"more softer colors"* refers to the previously searched *"wedding sherwani"*), stAiler implements **Django Session Context Blending**:

```
[ User Prompt: "softer colors" ]
         │
         ▼
[ Read request.session['stylist_history'] ]
(E.g., "Query 1: wedding sherwani")
         │
         ▼
[ Feed Context + New Prompt to Gemini API ]
         │
         ▼
[ Gemini blends context and returns Combined Intent JSON ]
{
   "audience": "women",
   "categories": ["kurtas"], 
   "occasion": "festive", 
   "colors": ["cream", "beige", "pastel"], 
   "stylist_response": "I've softened the color palette to pastels and creams while keeping the ethnic wedding look."
}
         │
         ▼
[ Pass JSON to recommend_for_profile() ] ──► [ Refresh Recommendations Page ]
```

### Context Blending Workflow:
1. **History List**: Django stores dialogue state in `request.session['stylist_history']` as:
   ```json
   [
     {"query": "wedding sherwani", "intent": {"category": "kurtas", "occasion": "festive"}}
   ]
   ```
2. **Context Merger**:
   * **Gemini LLM Pipeline**: Sends prompt history + new query. Gemini combines context to output a single consolidated schema JSON:
     * *Prompt 1: "I need a wedding sherwani"*
     * *Prompt 2: "softer colors"*
     * *Merged Intent: Category = kurtas, Occasion = festive, Colors = [cream, beige, pastel]*
   * **Local Fallback Pipeline**: Concatenates string inputs (`combined = f"{previous} {new}"`) and runs a local regex keyword parsing logic with dynamic synonyms.

---

## 4. The AI/ML Mathematical Formulations

The system runs a series of machine learning models in `scikit-learn` and maps scores to a comprehensive **Hybrid Ranking Formula**.

### A. Webcam Skin Tone Classifier (KNN)
* **Privacy-First Ephemeral Flow**: Image frames are processed in-memory. **No photos are saved to disk.**
* **KNN Skin Classifier (Supervised Classification)**: The dominant face center cluster $\mathbf{x}_{\text{skin}} = [R, G, B]$ is classified by a K-Nearest Neighbors model trained on skin-tone distributions to predict: *Fair, Medium, Olive, or Deep*.
  $$\hat{y} = \text{Mode}(\{y_i \mid \mathbf{x}_i \in N_k(\mathbf{x}_{\text{skin}})\})$$

### B. Anthropometric Body DNA Predictor (Softmax Multi-Class Logistic Regression & Decoupled BMI)
* User provides metrics: Height, Weight, Bust, Waist, and Hips.
* We engineer a biometric feature vector $\mathbf{x} = [r_{\text{bw}}, r_{\text{hw}}, r_{\text{bh}}, \text{BMI}]$ based on standard Wharton anthropological ratios:
  * $r_{\text{bw}} = \frac{\text{Bust}}{\text{Waist}}$, $r_{\text{hw}} = \frac{\text{Hips}}{\text{Waist}}$, $r_{\text{bh}} = \frac{\text{Bust}}{\text{Hips}}$, $\text{BMI} = \frac{\text{Weight}}{\text{Height}^2} \times 10,000$
* **Structural Shape Classifier**: We train a **Multi-Class Logistic Regression Model** in `scikit-learn` to calculate class probability using Softmax:
  $$P(y = k \mid \mathbf{x}) = \frac{e^{\mathbf{w}_k^T \mathbf{x} + b_k}}{\sum_{j=1}^{K} e^{\mathbf{w}_j^T \mathbf{x} + b_j}}$$
  Classifies the body shape into structural types: **Hourglass**, **Pear**, **Apple**, **Rectangle**, **V-Taper**, **Trapezoid**, **Triangle**, or **Oval**.
* **Scale Classification (Decoupled BMI)**: Predicts BMI category independently:
  * $\text{BMI} < 18.5$: **Thin** (prioritizes tight/fitted silhouettes to avoid looking swallowed)
  * $18.5 \le \text{BMI} < 25.0$: **Normal**
  * $25.0 \le \text{BMI} < 30.0$: **Overweight** (prioritizes draping and relaxed lines)
  * $\text{BMI} \ge 30.0$: **Obese** (prioritizes draping and relaxed lines)
* **Height Vertical Draping Rules**: Height is analyzed to enforce vertical styling guidelines:
  * $\text{Height} < 158\text{cm}$: **Petite** (favors cropped cuts, monochrome fits, vertical elements to elongate stature)
  * $\text{Height} > 175\text{cm}$: **Tall** (favors maxi lengths, oversized layers, and tunics to complement long lines)
* **Regex Word-Boundary Matching**: To prevent false-positive substring matches (e.g. matching `"fit"` inside `"outfit"`), stAiler uses regular expression word boundaries (`\b`) to matches styling silhouette terms against product metadata.

### C. Self-Learning Click Adaptation (Online Drift)
* User's preference affinities are continuous weights: $\mathbf{U}_t = [\mathbf{W}_{\text{style}}, \mathbf{W}_{\text{fit}}, \mathbf{W}_{\text{color}}]$.
* On Like/Dislike click of garment $i$ with features $\mathbf{V}_i$, the vector drifts dynamically:
  $$\mathbf{U}_{t+1} = \mathbf{U}_t + 0.08 \cdot \mathbf{V}_i \quad (\text{for Likes})$$
  $$\mathbf{U}_{t+1} = \mathbf{U}_t - 0.15 \cdot \mathbf{V}_i \quad (\text{for Dislikes})$$

### D. The Consolidated Hybrid Ranking Equation
For each product $i$, the engine computes:
$$S_i = w_1 \cdot \text{CosineSimilarity}(\mathbf{q}, \mathbf{p}_i) + w_2 \cdot \text{MetadataScore}(i, \text{Plan}) + w_3 \cdot \text{BodyScore}(i, \text{Profile}) + w_4 \cdot \text{ColorSimilarity}(\mathbf{c}_{\text{skin}}, \mathbf{c}_i) + w_5 \cdot \text{Rating}_i + w_6 \cdot \text{Feedback}_i$$
* **$\text{CosineSimilarity}(\mathbf{q}, \mathbf{p}_i)$**: Semantic match of blended prompt TF-IDF vectors.
* **$\text{MetadataScore}(i, \text{Plan})$**: Bonus for planned categories and styling types.
* **$\text{BodyScore}(i, \text{Profile})$**: Compatibility match with diagnosed body DNA (averages silhouette, scale/BMI, and height components).
* **$\text{ColorSimilarity}(\mathbf{c}_{\text{skin}}, \mathbf{c}_i)$**: Jaccard similarity index measuring skin-tone color compatibility.
  * *URL Color Extraction*: Parses color keywords from `product_url` (e.g. `"-maroon-"`) to maximize color catalog coverage.
  * *Skin-Tone Fallback*: For products with empty color lists, the engine assigns a neutral compatibility score (`0.6`) and displays: `"Color palette suits [skin tone] skin tone"`.
* **$\text{Rating}_i$**: Normalized catalog rating.
* **$\text{Feedback}_i$**: Dynamic adjustments based on Likes/Dislikes history.

---

## 5. Verified Architecture
- **Single-LLM Execution:** Gemini is called once per request to construct the structured `StylePlan` intent, keeping latency extremely low (<1s).
- **Local ML Reranking:** Final selections, scoring, and XAI badges are computed entirely locally in Python (5ms), ensuring high uptime, no token truncations, and no dependency bottlenecks.
- **Two-Pass Catalog Backfill**: Guarantees exactly 6 recommendations on the curated rack. If filtering or confidence constraints return less than 6 items, a second pass relaxes confidence score thresholds to backfill the rack using the closest relevant items.
- **Gender Consistency Guard**: Ensures that recommendations match the user's selected gender (Men, Women, or Kids) at all times, with strict filters and fallback logic preventing leakage of other categories.
