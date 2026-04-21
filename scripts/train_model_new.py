#!/usr/bin/env python3
import pandas as pd
from lightgbm import LGBMClassifier
import numpy as np
import joblib
from sklearn.metrics import classification_report

def main():
    print("Loading updated features...")
    data = pd.read_csv("../processed/features.csv")

    # Sanitize data to prevent math errors
    data["density"] = data["density"].fillna(0).astype(int)
    data["log_density"] = np.log1p(data["density"])

    X = data[["density", "log_density"]]
    
    # Define active prefix threshold (adjust the > 10 threshold if needed)
    y = (data["density"] > 10).astype(int)

    print("Training LightGBM Classifier...")
    model = LGBMClassifier(
        n_estimators=300,
        max_depth=-1,
        learning_rate=0.05,
        class_weight="balanced",
        random_state=42 # Ensures repeatable results for your final report
    )

    model.fit(X, y)

    print("\n--- Model Performance Benchmark ---")
    y_pred = model.predict(X)
    print(classification_report(y, y_pred, target_names=["Inactive Prefix", "Active Prefix"]))
    print("-----------------------------------\n")

    joblib.dump(model, "../models/prefix_model_new.pkl")
    print("Model successfully trained and saved to ../models/prefix_model_new.pkl")

if __name__ == "__main__":
    main()
