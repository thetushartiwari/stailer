from __future__ import annotations

import numpy as np

from products.models import Product, UserPreference, UserProfile
from products.recommendation_model import build_similarity_matrix


def _preference_queryset(profile: UserProfile | None):
    if not profile:
        return UserPreference.objects.none()
    if profile.user:
        return UserPreference.objects.filter(user=profile.user)
    if profile.session_key:
        return UserPreference.objects.filter(session_key=profile.session_key)
    return UserPreference.objects.none()


def feedback_score(product: Product, profile: UserProfile | None) -> tuple[float, list[str]]:
    prefs = list(_preference_queryset(profile).select_related("product"))
    if not prefs:
        return 0.0, []

    df, sim_matrix, _ = build_similarity_matrix()
    if df.empty or sim_matrix is None:
        return 0.0, []

    id_to_idx = {int(row_id): idx for idx, row_id in zip(df.index, df["id"])}
    target_idx = id_to_idx.get(product.id)
    if target_idx is None:
        return 0.0, []

    liked = [pref.product.id for pref in prefs if pref.liked and pref.product_id in id_to_idx]
    disliked = [pref.product.id for pref in prefs if not pref.liked and pref.product_id in id_to_idx]
    liked_scores = [sim_matrix[target_idx][id_to_idx[item_id]] for item_id in liked]
    disliked_scores = [sim_matrix[target_idx][id_to_idx[item_id]] for item_id in disliked]

    liked_mean = float(np.mean(liked_scores)) if liked_scores else 0.0
    disliked_mean = float(np.mean(disliked_scores)) if disliked_scores else 0.0
    score = liked_mean - disliked_mean

    reasons = []
    if liked_mean > 0.12:
        reasons.append("Similar to products you liked")
    if disliked_mean > 0.12:
        reasons.append("Moved away from products you disliked")
    return score, reasons
