import pandas as pd
from lightgbm import LGBMClassifier
import numpy as np
import joblib

data = pd.read_csv("../processed/features.csv")

data["log_density"] = np.log1p(data["density"])

X = data[["density", "log_density"]]
y = (data["density"] > 10).astype(int)

model = LGBMClassifier(
    n_estimators=300,
    max_depth=-1,
    learning_rate=0.05,
    class_weight="balanced"
)

model.fit(X, y)

joblib.dump(model, "../models/prefix_model.pkl")

print("Model trained")
                    
