
"""
05_supervised_model.py
Supervised Learning: dự đoán cổ phiếu thuộc nhóm sinh lời tốt hay không.
Nhãn đơn giản cho BTL:
- Target = 1 nếu RET > median(RET)
- Target = 0 nếu RET <= median(RET)
"""
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, roc_auc_score, classification_report
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from config import CLUSTER_FILE, ML_PRED_FILE, FEATURE_COLUMNS, MODELS, DATA_OUTPUT, RANDOM_STATE


def safe_auc(y_true, y_prob):
    try:
        return float(roc_auc_score(y_true, y_prob))
    except Exception:
        return None


def run_supervised(input_path=CLUSTER_FILE):
    df = pd.read_csv(input_path)
    features = [c for c in FEATURE_COLUMNS if c in df.columns]
    if "RET" not in df.columns:
        raise ValueError("Thiếu cột RET để tạo nhãn supervised learning.")

    y = (df["RET"] > df["RET"].median()).astype(int)
    X = df[features].copy()

    # Với dataset nhỏ, dùng stratify để tránh lệch lớp.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_STATE, stratify=y
    )

    models = {
        "RandomForest": RandomForestClassifier(
            n_estimators=300,
            max_depth=5,
            min_samples_leaf=3,
            random_state=RANDOM_STATE,
            class_weight="balanced",
        ),
        "GradientBoosting": GradientBoostingClassifier(random_state=RANDOM_STATE),
    }

    results = {}
    best_name = None
    best_auc = -1
    best_model = None

    for name, model in models.items():
        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("model", model),
        ])
        pipe.fit(X_train, y_train)
        pred = pipe.predict(X_test)
        if hasattr(pipe.named_steps["model"], "predict_proba"):
            prob = pipe.predict_proba(X_test)[:, 1]
        else:
            prob = pred

        auc = safe_auc(y_test, prob)
        results[name] = {
            "accuracy": float(accuracy_score(y_test, pred)),
            "balanced_accuracy": float(balanced_accuracy_score(y_test, pred)),
            "macro_f1": float(f1_score(y_test, pred, average="macro")),
            "roc_auc": auc,
            "classification_report": classification_report(y_test, pred, output_dict=True, zero_division=0),
        }

        model_score = auc if auc is not None else results[name]["macro_f1"]
        if model_score > best_auc:
            best_auc = model_score
            best_name = name
            best_model = pipe

    # Fit lại best model trên toàn bộ dataset để lấy xác suất cho tất cả mã.
    best_model.fit(X, y)
    df["Target_Good_Return"] = y
    df["ML_Probability"] = best_model.predict_proba(X)[:, 1]
    df["ML_Model"] = best_name

    # Feature importance nếu model hỗ trợ.
    estimator = best_model.named_steps["model"]
    if hasattr(estimator, "feature_importances_"):
        imp = pd.DataFrame({
            "Feature": features,
            "Importance": estimator.feature_importances_,
        }).sort_values("Importance", ascending=False)
        imp.to_csv(DATA_OUTPUT / "feature_importance.csv", index=False)

    MODELS.mkdir(parents=True, exist_ok=True)
    DATA_OUTPUT.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, MODELS / "best_supervised_model.joblib")
    df.to_csv(ML_PRED_FILE, index=False)

    report = {
        "target_definition": "1 nếu RET > median(RET), 0 nếu ngược lại",
        "best_model": best_name,
        "results": results,
        "features": features,
    }
    (DATA_OUTPUT / "supervised_metrics.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("Best model:", best_name)
    print("Saved:", ML_PRED_FILE)
    return df


if __name__ == "__main__":
    run_supervised()
