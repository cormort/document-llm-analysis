"""
Core statistical testing functions.

This module contains pure statistical functions with no UI dependencies,
making them easy to test and reuse across different contexts.
"""

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


def run_ttest(group1: pd.Series, group2: pd.Series) -> dict[str, Any]:
    """
    Execute independent samples T-test.

    Args:
        group1: First group data
        group2: Second group data

    Returns:
        Dictionary containing t_statistic, p_value, mean1, mean2, and is_significant
    """
    g1_clean = group1.dropna()
    g2_clean = group2.dropna()

    if len(g1_clean) < 2 or len(g2_clean) < 2:
        return {
            "error": "Each group must have at least 2 samples",
            "t_statistic": None,
            "p_value": None,
        }

    t_stat, p_val = stats.ttest_ind(g1_clean, g2_clean)

    return {
        "t_statistic": float(t_stat),
        "p_value": float(p_val),
        "mean1": float(g1_clean.mean()),
        "mean2": float(g2_clean.mean()),
        "n1": len(g1_clean),
        "n2": len(g2_clean),
        "is_significant": p_val < 0.05,
    }


def run_anova(*groups: pd.Series) -> dict[str, Any]:
    """
    Execute one-way ANOVA test.

    Args:
        *groups: Variable number of group data series

    Returns:
        Dictionary containing f_statistic, p_value, and is_significant
    """
    cleaned_groups = [g.dropna() for g in groups if len(g.dropna()) >= 2]

    if len(cleaned_groups) < 2:
        return {
            "error": "Need at least 2 groups with 2+ samples each",
            "f_statistic": None,
            "p_value": None,
        }

    f_stat, p_val = stats.f_oneway(*cleaned_groups)

    return {
        "f_statistic": float(f_stat),
        "p_value": float(p_val),
        "n_groups": len(cleaned_groups),
        "group_sizes": [len(g) for g in cleaned_groups],
        "is_significant": p_val < 0.05,
    }


def run_shapiro_wilk(data: pd.Series) -> dict[str, Any]:
    """
    Execute Shapiro-Wilk normality test.

    Args:
        data: Data series to test

    Returns:
        Dictionary containing statistic, p_value, and is_normal
    """
    clean_data = data.dropna()

    if len(clean_data) < 3:
        return {
            "error": "Need at least 3 samples for normality test",
            "statistic": None,
            "p_value": None,
        }

    if len(clean_data) > 5000:
        # Shapiro-Wilk works best with n <= 5000
        clean_data = clean_data.sample(5000, random_state=42)

    stat, p_val = stats.shapiro(clean_data)

    return {
        "statistic": float(stat),
        "p_value": float(p_val),
        "n_samples": len(clean_data),
        "is_normal": p_val > 0.05,
    }


def detect_outliers_iqr(
    data: pd.Series, multiplier: float = 1.5
) -> dict[str, Any]:
    """
    Detect outliers using the IQR method.

    Args:
        data: Data series to analyze
        multiplier: IQR multiplier for bounds (default 1.5)

    Returns:
        Dictionary containing bounds, outlier indices, and outlier values
    """
    clean_data = data.dropna()

    if len(clean_data) < 4:
        return {
            "error": "Need at least 4 samples for IQR calculation",
            "lower_bound": None,
            "upper_bound": None,
        }

    q1 = clean_data.quantile(0.25)
    q3 = clean_data.quantile(0.75)
    iqr = q3 - q1

    lower_bound = q1 - multiplier * iqr
    upper_bound = q3 + multiplier * iqr

    outlier_mask = (clean_data < lower_bound) | (clean_data > upper_bound)
    outlier_indices = clean_data[outlier_mask].index.tolist()
    outlier_values = clean_data[outlier_mask].values.tolist()

    return {
        "q1": float(q1),
        "q3": float(q3),
        "iqr": float(iqr),
        "lower_bound": float(lower_bound),
        "upper_bound": float(upper_bound),
        "n_outliers": int(outlier_mask.sum()),
        "outlier_percentage": float(outlier_mask.sum() / len(clean_data) * 100),
        "outlier_indices": outlier_indices,
        "outlier_values": outlier_values,
    }


def run_correlation_matrix(
    df: pd.DataFrame, method: str = "pearson"
) -> pd.DataFrame:
    """
    Calculate correlation matrix for numeric columns.

    Args:
        df: DataFrame with numeric columns
        method: Correlation method ('pearson', 'spearman', 'kendall')

    Returns:
        Correlation matrix as DataFrame
    """
    num_df = df.select_dtypes(include=[np.number])
    return num_df.corr(method=method)


def run_mannwhitneyu(group1: pd.Series, group2: pd.Series) -> dict[str, Any]:
    """Execute Mann-Whitney U test (non-parametric alternative to T-test)."""
    g1_clean = group1.dropna()
    g2_clean = group2.dropna()

    if len(g1_clean) < 2 or len(g2_clean) < 2:
        return {"error": "Insufficient data"}

    statistic, p_val = stats.mannwhitneyu(g1_clean, g2_clean, alternative="two-sided")

    return {
        "statistic": float(statistic),
        "p_value": float(p_val),
        "median1": float(g1_clean.median()),
        "median2": float(g2_clean.median()),
        "is_significant": p_val < 0.05,
        "method": "Mann-Whitney U"
    }


def run_kruskal(*groups: pd.Series) -> dict[str, Any]:
    """Execute Kruskal-Wallis H-test (non-parametric alternative to ANOVA)."""
    cleaned_groups = [g.dropna() for g in groups if len(g.dropna()) >= 2]

    if len(cleaned_groups) < 2:
        return {"error": "Insufficient groups"}

    statistic, p_val = stats.kruskal(*cleaned_groups)

    return {
        "statistic": float(statistic),
        "p_value": float(p_val),
        "n_groups": len(cleaned_groups),
        "is_significant": p_val < 0.05,
        "method": "Kruskal-Wallis"
    }

def run_wilcoxon(group1: pd.Series, group2: pd.Series) -> dict[str, Any]:
    """Execute Wilcoxon Signed-Rank Test (paired non-parametric)."""
    # Ensure same length and ignore NaNs pair-wise
    df = pd.DataFrame({"g1": group1, "g2": group2}).dropna()
    
    if len(df) < 2:
        return {"error": "Insufficient paired data"}
        
    statistic, p_val = stats.wilcoxon(df["g1"], df["g2"])
    
    return {
        "statistic": float(statistic),
        "p_value": float(p_val),
        "median_diff": float((df["g1"] - df["g2"]).median()),
        "is_significant": p_val < 0.05,
        "method": "Wilcoxon Signed-Rank"
    }


def run_chi_square(series1: pd.Series, series2: pd.Series) -> dict[str, Any]:
    """Execute Chi-Square Test of Independence for categorical variables."""
    # Create contingency table
    crosstab = pd.crosstab(series1, series2)
    
    stat, p_val, dof, expected = stats.chi2_contingency(crosstab)
    
    return {
        "statistic": float(stat),
        "p_value": float(p_val),
        "dof": int(dof),
        "is_significant": p_val < 0.05,
        "crosstab": crosstab.to_dict(),
        "method": "Chi-Square Test"
    }

def suggest_test(groups: list[pd.Series]) -> dict[str, Any]:
    """
    Check normality assumptions and suggest best statistical test.
    """
    results = {"normality": [], "suggestion": ""}

    is_all_normal = True
    for i, g in enumerate(groups):
        norm_res = run_shapiro_wilk(g)
        is_normal = norm_res.get("is_normal", False)
        results["normality"].append({"group": i, "is_normal": is_normal})
        if not is_normal:
            is_all_normal = False

    if len(groups) == 2:
        if is_all_normal:
            results["suggestion"] = "T-Test (參數檢定)"
            results["recommended_func"] = "ttest"
        else:
            results["suggestion"] = "Mann-Whitney U (非參數檢定)"
            results["recommended_func"] = "mannwhitney"
    elif len(groups) > 2:
        if is_all_normal:
            results["suggestion"] = "ANOVA (參數檢定)"
            results["recommended_func"] = "anova"
        else:
            results["suggestion"] = "Kruskal-Wallis (非參數檢定)"
            results["recommended_func"] = "kruskal"

    return results

def run_pca(df: pd.DataFrame, features: list[str], n_components: int = 2) -> dict[str, Any]:
    """Execute Principal Component Analysis (PCA)."""
    data = df[features].dropna()
    
    if len(data) < max(3, n_components):
        return {"error": "Insufficient data for PCA"}
    
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(data)
    
    pca = PCA(n_components=n_components)
    components = pca.fit_transform(scaled_data)
    
    explained_variance = pca.explained_variance_ratio_.tolist()
    
    feature_weights = {}
    for i in range(n_components):
        feature_weights[f"PC{i+1}"] = pca.components_[i].tolist()
        
    points = []
    for i in range(len(components)):
        point = {"id": int(data.index[i])}
        for j in range(n_components):
            point[f"PC{j+1}"] = float(components[i, j])
        points.append(point)
        
    return {
        "success": True,
        "n_components": n_components,
        "explained_variance": [float(v) for v in explained_variance],
        "feature_weights": feature_weights,
        "data": points,
        "features_used": features
    }

def run_kmeans(df: pd.DataFrame, features: list[str], n_clusters: int = 3) -> dict[str, Any]:
    """Execute K-Means Clustering."""
    data = df[features].dropna()
    
    if len(data) < max(3, n_clusters):
        return {"error": "Insufficient data for K-Means Clustering"}
        
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(data)
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(scaled_data)
    
    cluster_centers = {}
    data_with_labels = data.copy()
    data_with_labels["Cluster"] = labels
    
    for c in range(n_clusters):
        cluster_data = data_with_labels[data_with_labels["Cluster"] == c]
        if len(cluster_data) > 0:
            center_dict = cluster_data[features].mean().to_dict()
            cluster_centers[f"Cluster {c}"] = {k: float(v) for k, v in center_dict.items()}
        else:
            cluster_centers[f"Cluster {c}"] = {f: 0.0 for f in features}
            
    # PCA to 2D just for visualization of clusters
    pca = PCA(n_components=min(2, len(features)))
    components = pca.fit_transform(scaled_data) if len(features) >= 2 else scaled_data
    
    points = []
    for i in range(len(components)):
        point = {
            "id": int(data.index[i]),
            "cluster": int(labels[i]),
            "x": float(components[i, 0]),
            "y": float(components[i, 1]) if components.shape[1] > 1 else 0.0
        }
        for f in features:
            point[f] = float(data.iloc[i][f])
        points.append(point)
        
    return {
        "success": True,
        "n_clusters": n_clusters,
        "cluster_centers": cluster_centers,
        "data": points,
        "features_used": features
    }

