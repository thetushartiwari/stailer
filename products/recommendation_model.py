# products/recommendation_model.py
import os
import pickle
import pandas as pd
from django.conf import settings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .models import Product, UserPreference

# Predefined fashion colors list
COLOR_KEYWORDS = {
    'red', 'blue', 'green', 'yellow', 'black', 'white', 'grey', 'gray', 'brown', 'pink', 'purple', 'orange',
    'beige', 'navy', 'maroon', 'cream', 'tan', 'olive', 'teal', 'coral', 'gold', 'silver', 'mustard', 'cherry'
}

# Paths to serialized ML outputs
ML_DIR = os.path.join(os.path.dirname(__file__), "ml_artifacts")
VECTORIZER_PATH = os.path.join(ML_DIR, "tfidf_vectorizer.pkl")
SIMILARITY_PATH = os.path.join(ML_DIR, "similarity_matrix.pkl")

# In-memory singletons to avoid even disk-reads on high concurrency requests
_CACHED_DF = None
_CACHED_SIM = None
_CACHED_TFIDF = None

def extract_colors(text):
    text_lower = (text or "").lower()
    return [c for c in COLOR_KEYWORDS if c in text_lower]

def get_color_similarity(colors1, colors2):
    if not colors1 or not colors2: 
        return 0.0
    inter = len(set(colors1) & set(colors2))
    union = len(set(colors1) | set(colors2))
    return inter / union if union else 0.0

def build_similarity_matrix(force_rebuild=False):
    global _CACHED_DF, _CACHED_SIM, _CACHED_TFIDF
    
    # Return in-memory cache if available and not forcing rebuild
    if not force_rebuild and _CACHED_DF is not None and _CACHED_SIM is not None:
        return _CACHED_DF, _CACHED_SIM, _CACHED_TFIDF

    # Check if disk-serialized pickle caches are available
    if not force_rebuild and os.path.exists(VECTORIZER_PATH) and os.path.exists(SIMILARITY_PATH):
        try:
            # Query all products in database
            prods = Product.objects.all().values('id', 'title', 'brand', 'category', 'category_type', 'description', 'gender', 'fit', 'colors', 'style_tags')
            _CACHED_DF = pd.DataFrame(list(prods))
            if not _CACHED_DF.empty:
                _CACHED_DF['text'] = (
                    _CACHED_DF['title'].fillna('') + ' ' + 
                    _CACHED_DF['brand'].fillna('') + ' ' +
                    _CACHED_DF['gender'].fillna('') + ' ' +
                    _CACHED_DF['category'].fillna('') + ' ' + 
                    _CACHED_DF['category_type'].fillna('') + ' ' + 
                    _CACHED_DF['description'].fillna('') + ' ' +
                    _CACHED_DF['fit'].fillna('') + ' ' +
                    _CACHED_DF['colors'].apply(lambda v: ' '.join(v or []) if isinstance(v, list) else '') + ' ' +
                    _CACHED_DF['style_tags'].apply(lambda v: ' '.join(v or []) if isinstance(v, list) else '')
                )
                _CACHED_DF['colors'] = _CACHED_DF['text'].apply(extract_colors)
                
                with open(VECTORIZER_PATH, "rb") as f:
                    _CACHED_TFIDF = pickle.load(f)
                with open(SIMILARITY_PATH, "rb") as f:
                    _CACHED_SIM = pickle.load(f)
                    
                return _CACHED_DF, _CACHED_SIM, _CACHED_TFIDF
        except Exception:
            pass # Fall back to live calculation if loading failed

    # Live computation and serialization pipeline
    prods = Product.objects.all().values('id', 'title', 'brand', 'category', 'category_type', 'description', 'gender', 'fit', 'colors', 'style_tags')
    df = pd.DataFrame(list(prods))
    if df.empty:
        return df, None, None

    df['text'] = (
        df['title'].fillna('') + ' ' + 
        df['brand'].fillna('') + ' ' +
        df['gender'].fillna('') + ' ' +
        df['category'].fillna('') + ' ' + 
        df['category_type'].fillna('') + ' ' + 
        df['description'].fillna('') + ' ' +
        df['fit'].fillna('') + ' ' +
        df['colors'].apply(lambda v: ' '.join(v or []) if isinstance(v, list) else '') + ' ' +
        df['style_tags'].apply(lambda v: ' '.join(v or []) if isinstance(v, list) else '')
    )
    df['colors'] = df['text'].apply(extract_colors)

    # Fit TF-IDF Vectorizer
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(df['text'])
    similarity = cosine_similarity(tfidf_matrix, tfidf_matrix)

    # Save to disk
    os.makedirs(ML_DIR, exist_ok=True)
    try:
        with open(VECTORIZER_PATH, "wb") as f:
            pickle.dump(tfidf, f)
        with open(SIMILARITY_PATH, "wb") as f:
            pickle.dump(similarity, f)
    except Exception:
        pass # Allow soft failure in write-protected environments

    _CACHED_DF = df
    _CACHED_SIM = similarity
    _CACHED_TFIDF = tfidf

    return df, similarity, tfidf

def invalidate_recommendation_cache():
    """Triggered after database changes to rebuild pickled caches."""
    build_similarity_matrix(force_rebuild=True)

def get_recommendations(product_id, user=None, top_n=4, liked=True):
    df, sim_matrix, _ = build_similarity_matrix()
    if df.empty or sim_matrix is None:
        return Product.objects.none()

    # Find row index of target product
    try:
        idx = df.index[df['id'] == product_id][0]
    except IndexError:
        return Product.objects.none()

    target_gender = df.loc[idx, 'gender']
    target_colors = df.loc[idx, 'colors']
    target_category = df.loc[idx, 'category']

    # Strict partition: partition pool by same gender to preserve suitability
    same_gender_idx = df.index[df['gender'] == target_gender].tolist()
    
    # Calculate baseline text cosine similarities
    sim_scores = [(i, sim_matrix[idx][i]) for i in same_gender_idx]

    # Adjust scores dynamically with custom styling weights
    scores_map = {i: s for i, s in sim_scores}
    for i in same_gender_idx:
        if i == idx:
            scores_map[i] = -999.0  # Exclude target product itself
            continue
            
        other_colors = df.loc[i, 'colors']
        other_cat = df.loc[i, 'category']

        color_sim = get_color_similarity(target_colors, other_colors)
        
        if liked:
            # Positive Feedback Boost
            scores_map[i] += 0.35 * color_sim
            if other_cat == target_category:
                scores_map[i] += 0.25
        else:
            # Negative Feedback Penalty
            scores_map[i] -= 0.60 * color_sim
            if other_cat == target_category:
                scores_map[i] -= 0.35
            if color_sim == 0:
                scores_map[i] += 0.15 # Boost disjoint color configurations

    # Personalization: incorporate long-term liked history
    if user and getattr(user, 'is_authenticated', False):
        user_prefs = UserPreference.objects.filter(user=user)
        liked_ids = [p.product.id for p in user_prefs if p.liked]
        disliked_ids = [p.product.id for p in user_prefs if not p.liked]

        for liked_id in liked_ids:
            if liked_id == product_id: 
                continue
            try:
                li = df.index[df['id'] == liked_id][0]
                for i in scores_map:
                    scores_map[i] += 0.18 * sim_matrix[li][i]
            except IndexError:
                pass
                
        for dis_id in disliked_ids:
            try:
                di = df.index[df['id'] == dis_id][0]
                for i in scores_map:
                    scores_map[i] -= 0.20 * sim_matrix[di][i]
            except IndexError:
                pass

    # Sort descending
    sorted_idx = sorted(scores_map.items(), key=lambda x: x[1], reverse=True)
    rec_indices = [i for i, s in sorted_idx if i != idx][:top_n]
    rec_ids = df.loc[rec_indices, 'id'].tolist()
    
    # Retrieve model instances preserving ordering
    preserved = Product.objects.filter(id__in=rec_ids)
    preserved = sorted(preserved, key=lambda p: rec_ids.index(p.id))
    return preserved

def get_similar_products(product, user=None, top_n=4):
    return get_recommendations(product.id, user=user, top_n=top_n, liked=True)

def get_dissimilar_products(product, user=None, top_n=4):
    return get_recommendations(product.id, user=user, top_n=top_n, liked=False)
