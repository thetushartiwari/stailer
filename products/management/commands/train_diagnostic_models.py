# products/management/commands/train_diagnostic_models.py
import os
import pickle
import numpy as np
from django.core.management.base import BaseCommand
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB

class Command(BaseCommand):
    help = "Generates synthetic biometric and age distributions, trains KNN, Logistic Regression & Gaussian Naive Bayes classifiers, and pickles them."

    def handle(self, *args, **options):
        self.stdout.write("Generating ML model training datasets...")
        np.random.seed(42)
        samples_per_class = 250
        
        # 1. GENERATE SKIN COLOR TRAINING DATA (1000 samples)
        # Skin categories: 0: Fair, 1: Medium, 2: Olive, 3: Deep
        fair_base = np.array([246.0, 214.0, 182.0]) # Peach/Fair base
        medium_base = np.array([218.0, 162.0, 117.0]) # Medium base
        olive_base = np.array([170.0, 114.0, 76.0]) # Olive base
        deep_base = np.array([90.0, 48.0, 20.0]) # Deep base

        fair_data = fair_base + np.random.normal(0, 8, (samples_per_class, 3))
        medium_data = medium_base + np.random.normal(0, 8, (samples_per_class, 3))
        olive_data = olive_base + np.random.normal(0, 8, (samples_per_class, 3))
        deep_data = deep_base + np.random.normal(0, 8, (samples_per_class, 3))

        X_skin = np.vstack([fair_data, medium_data, olive_data, deep_data])
        X_skin = np.clip(X_skin, 0, 255)

        y_skin = np.hstack([
            np.zeros(samples_per_class), # 0: Fair
            np.ones(samples_per_class),  # 1: Medium
            np.ones(samples_per_class) * 2, # 2: Olive
            np.ones(samples_per_class) * 3  # 3: Deep
        ]).astype(int)

        self.stdout.write("Training Supervised KNN Skin Tone Classifier...")
        skin_classifier = KNeighborsClassifier(n_neighbors=5, metric='euclidean')
        skin_classifier.fit(X_skin, y_skin)

        # 2. GENERATE ANTHROPOMETRIC BODY DATA
        # Hourglass: high bust/waist, high hips/waist, balanced bust/hips, normal BMI
        hg_feat = np.hstack([
            np.random.normal(1.30, 0.03, (samples_per_class, 1)),
            np.random.normal(1.32, 0.03, (samples_per_class, 1)),
            np.random.normal(0.98, 0.02, (samples_per_class, 1)),
            np.random.normal(21.5, 1.2, (samples_per_class, 1))
        ])

        # Round/Plus-size: medium waist ratios, high BMI (> 27)
        round_feat = np.hstack([
            np.random.normal(1.10, 0.03, (samples_per_class, 1)),
            np.random.normal(1.12, 0.03, (samples_per_class, 1)),
            np.random.normal(1.00, 0.02, (samples_per_class, 1)),
            np.random.normal(29.0, 1.5, (samples_per_class, 1))
        ])

        # Rectangle: low waist ratios, balanced bust/hips, normal BMI
        rect_feat = np.hstack([
            np.random.normal(1.08, 0.02, (samples_per_class, 1)),
            np.random.normal(1.09, 0.02, (samples_per_class, 1)),
            np.random.normal(0.99, 0.01, (samples_per_class, 1)),
            np.random.normal(22.0, 1.0, (samples_per_class, 1))
        ])

        # Athletic/Broad: high bust/waist, low hips/waist, high bust/hips, normal/low BMI
        ath_feat = np.hstack([
            np.random.normal(1.25, 0.03, (samples_per_class, 1)),
            np.random.normal(1.10, 0.03, (samples_per_class, 1)),
            np.random.normal(1.15, 0.03, (samples_per_class, 1)),
            np.random.normal(23.0, 1.1, (samples_per_class, 1))
        ])

        # Petite: smaller frame / low BMI while preserving reasonable body ratios
        petite_feat = np.hstack([
            np.random.normal(1.12, 0.03, (samples_per_class, 1)),
            np.random.normal(1.14, 0.03, (samples_per_class, 1)),
            np.random.normal(0.98, 0.02, (samples_per_class, 1)),
            np.random.normal(17.8, 0.6, (samples_per_class, 1))
        ])

        X_body = np.vstack([hg_feat, round_feat, rect_feat, ath_feat, petite_feat])
        y_body = np.hstack([
            np.zeros(samples_per_class), # 0: Hourglass
            np.ones(samples_per_class),  # 1: Round
            np.ones(samples_per_class) * 2, # 2: Rectangle
            np.ones(samples_per_class) * 3, # 3: Athletic
            np.ones(samples_per_class) * 4  # 4: Petite
        ]).astype(int)

        self.stdout.write("Training Supervised Logistic Regression Body DNA Predictor...")
        body_classifier = LogisticRegression(max_iter=1000, multi_class='multinomial')
        body_classifier.fit(X_body, y_body)

        # 3. SERIALIZE & PICKLE ML MODELS
        ml_artifacts_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
            "ml_artifacts"
        )
        os.makedirs(ml_artifacts_dir, exist_ok=True)

        skin_path = os.path.join(ml_artifacts_dir, "skin_classifier.pkl")
        body_path = os.path.join(ml_artifacts_dir, "body_classifier.pkl")

        self.stdout.write(f"Serializing KNN Skin Classifier to {skin_path}...")
        with open(skin_path, "wb") as f:
            pickle.dump(skin_classifier, f)

        self.stdout.write(f"Serializing Logistic Regression Body DNA Classifier to {body_path}...")
        with open(body_path, "wb") as f:
            pickle.dump(body_classifier, f)

        self.stdout.write(self.style.SUCCESS("All diagnostic ML models successfully trained and serialized! [OK]"))
