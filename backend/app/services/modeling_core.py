import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error, accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, roc_curve, auc
from sklearn.preprocessing import LabelEncoder

def train_linear_regression(
    df: pd.DataFrame, 
    feature_cols: list[str], 
    target_col: str, 
    test_size: float = 0.2
) -> Dict[str, Any]:
    """
    Train a linear regression model.
    """
    # Prepare data
    X = df[feature_cols].copy()
    y = df[target_col].copy()
    
    # Handle missing values by dropping
    data = pd.concat([X, y], axis=1).dropna()
    X = data[feature_cols]
    y = data[target_col]
    
    if len(X) < 10:
        raise ValueError("Not enough data to train model (minimum 10 samples)")
        
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
    
    # Train
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    # Predict
    y_pred = model.predict(X_test)
    
    # Metrics
    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    
    # Feature Importance (Coefficients)
    coefficients = dict(zip(feature_cols, model.coef_))
    
    # Normalized Importance
    abs_coefs = np.abs(model.coef_)
    total = abs_coefs.sum() if abs_coefs.sum() > 0 else 1.0
    importance = [
        {"feature": f, "importance": float(abs_c / total)}
        for f, abs_c in zip(feature_cols, abs_coefs)
    ]
    
    return {
        "model_type": "LinearRegression",
        "coefficients": coefficients,
        "intercept": float(model.intercept_),
        "r2_score": float(r2),
        "rmse": float(rmse),
        "predictions": y_pred.tolist(),
        "actual": y_test.tolist(),
        "feature_importance": importance,
        "sample_size": len(X)
    }

def train_logistic_regression(
    df: pd.DataFrame, 
    feature_cols: list[str], 
    target_col: str, 
    test_size: float = 0.2
) -> Dict[str, Any]:
    """
    Train a logistic regression model for classification.
    """
    # Prepare data
    X = df[feature_cols].copy()
    y = df[target_col].copy()
    
    # Clean data
    data = pd.concat([X, y], axis=1).dropna()
    X = data[feature_cols]
    y = data[target_col]
    
    if len(X) < 10:
        raise ValueError("Not enough data to train model (minimum 10 samples)")

    # Check if target is categorical/string and encode if necessary
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    classes = le.classes_.tolist()
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=test_size, random_state=42, stratify=y_encoded)
    
    # Train (using liblinear for small datasets standard)
    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)
    
    # Predict
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1] if len(classes) == 2 else None # Only for binary currently
    
    # Metrics
    accuracy = accuracy_score(y_test, y_pred)
    
    metrics = {
        "accuracy": float(accuracy),
        "precision": float(precision_score(y_test, y_pred, average='weighted', zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, average='weighted', zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, average='weighted', zero_division=0))
    }
    
    # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred).tolist()
    
    # Coefficients
    if model.coef_.ndim > 1:
        # Multiclass: coef_ is (n_classes, n_features) - take average abs or max?
        # For simplicity, let's take mean absolute impact
        avg_coef = np.mean(np.abs(model.coef_), axis=0)
        coefficients = dict(zip(feature_cols, avg_coef))
    else:
        coefficients = dict(zip(feature_cols, model.coef_[0]))

    # Feature Importance
    abs_coefs = np.array(list(coefficients.values()))
    total = abs_coefs.sum() if abs_coefs.sum() > 0 else 1.0
    importance = [
        {"feature": f, "importance": float(abs(c) / total)}
        for f, c in coefficients.items()
    ]
    
    # ROC Curve (Binary only)
    roc_data = None
    if len(classes) == 2 and y_prob is not None:
        fpr, tpr, _ = roc_curve(y_test, y_prob)
        roc_auc = auc(fpr, tpr)
        roc_data = {
            "fpr": fpr.tolist(),
            "tpr": tpr.tolist(),
            "auc": float(roc_auc)
        }
        
    return {
        "model_type": "LogisticRegression",
        "classes": classes,
        "coefficients": coefficients,
        "intercept": model.intercept_.tolist(),
        "metrics": metrics,
        "confusion_matrix": cm,
        "roc_curve": roc_data,
        "predictions": le.inverse_transform(y_pred).tolist(), # Return original labels
        "actual": le.inverse_transform(y_test).tolist(),
        "feature_importance": importance,
        "sample_size": len(X)
    }
