import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
DISCLAIMER = "Learning-level model. Not medical advice. Please consult a doctor."

_art = {}


def load_artifacts():
    if _art:
        return
    for name in ["disease_model", "heart_model", "heart_scaler",
                 "diabetes_model", "diabetes_scaler"]:
        _art[name] = joblib.load(MODELS_DIR / f"{name}.pkl")
    for name in ["disease", "heart", "diabetes"]:
        with open(MODELS_DIR / f"meta_{name}.json", encoding="utf-8") as f:
            _art[f"meta_{name}"] = json.load(f)


def get_symptom_list():
    load_artifacts()
    return _art["meta_disease"]["symptom_list"]


def _clean_symptom(s: str) -> str:
    return s.strip().lower().replace(" ", "_")


def predict_disease(symptoms):
    load_artifacts()
    model, meta = _art["disease_model"], _art["meta_disease"]
    sym_list = meta["symptom_list"]
    idx = {s: i for i, s in enumerate(sym_list)}

    x = np.zeros((1, len(sym_list)))
    unknown = []
    for s in symptoms:
        c = _clean_symptom(s)
        if c in idx:
            x[0, idx[c]] = 1
        else:
            unknown.append(s)
    if x.sum() == 0:
        raise ValueError("No recognised symptoms. Use names from /symptoms.")

    proba = model.predict_proba(pd.DataFrame(x, columns=sym_list))[0]
    top = np.argsort(proba)[::-1][:3]

    results = []
    for i in top:
        name = str(meta["classes"][int(model.classes_[i])]).strip()
        results.append({
            "disease": name,
            "probability": round(float(proba[i]), 4),
            "description": meta["descriptions"].get(name, ""),
            "precautions": meta["precautions"].get(name, []),
        })
    return {"top_predictions": results, "unrecognised_symptoms": unknown,
            "disclaimer": DISCLAIMER}


def predict_heart(payload: dict):
    load_artifacts()
    model, scaler, meta = _art["heart_model"], _art["heart_scaler"], _art["meta_heart"]
    feats = meta["features"]
    df = pd.DataFrame([payload])[feats].astype(float)

    # same cleaning as the notebook: impossible codes become NaN
    df.loc[df["ca"] == 4, "ca"] = np.nan
    df.loc[df["thal"] == 0, "thal"] = np.nan

    p = float(model.predict_proba(scaler.transform(df))[0, 1])
    thr = float(meta.get("threshold", 0.30))
    return {"probability": round(p, 4), "threshold": thr,
            "high_risk": p >= thr, "disclaimer": DISCLAIMER}


def predict_diabetes(payload: dict):
    load_artifacts()
    model, scaler, meta = _art["diabetes_model"], _art["diabetes_scaler"], _art["meta_diabetes"]
    feats = meta["features"]
    df = pd.DataFrame([payload])[feats].astype(float)

    # zeros that are impossible -> NaN -> saved medians
    for col in ["Glucose", "BloodPressure", "SkinThickness", "Insulin", "BMI"]:
        df.loc[df[col] == 0, col] = np.nan
    df = df.fillna(meta["medians"])

    p = float(model.predict_proba(scaler.transform(df))[0, 1])
    thr = float(meta.get("threshold", 0.35))
    return {"probability": round(p, 4), "threshold": thr,
            "high_risk": p >= thr, "disclaimer": DISCLAIMER}