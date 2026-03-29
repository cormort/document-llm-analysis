"""統計測試模組 Tests."""

import numpy as np
import pandas as pd
import pytest

from app.services.statistical_tests import (
    detect_outliers_iqr,
    run_anova,
    run_correlation_matrix,
    run_kruskal,
    run_mannwhitneyu,
    run_shapiro_wilk,
    run_ttest,
    suggest_test,
)


class TestRunTTest:
    def test_ttest_basic(self):
        group1 = pd.Series([1, 2, 3, 4, 5])
        group2 = pd.Series([6, 7, 8, 9, 10])
        result = run_ttest(group1, group2)

        assert "t_statistic" in result
        assert "p_value" in result
        assert "mean1" in result
        assert "mean2" in result
        assert result["mean1"] == 3.0
        assert result["mean2"] == 8.0

    def test_ttest_with_nan(self):
        group1 = pd.Series([1, 2, None, 4, 5])
        group2 = pd.Series([6, 7, 8, None, 10])
        result = run_ttest(group1, group2)

        assert result["n1"] == 4
        assert result["n2"] == 4

    def test_ttest_insufficient_data(self):
        group1 = pd.Series([1])
        group2 = pd.Series([2])
        result = run_ttest(group1, group2)

        assert "error" in result
        assert result["t_statistic"] is None


class TestRunANOVA:
    def test_anova_basic(self):
        g1 = pd.Series([1, 2, 3])
        g2 = pd.Series([4, 5, 6])
        g3 = pd.Series([7, 8, 9])
        result = run_anova(g1, g2, g3)

        assert "f_statistic" in result
        assert "p_value" in result


class TestRunShapiroWilk:
    def test_shapiro_basic(self):
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        result = run_shapiro_wilk(data)

        assert "statistic" in result
        assert "p_value" in result
        assert "is_normal" in result


class TestDetectOutliersIQR:
    def test_detect_outliers_basic(self):
        data = pd.Series([1, 2, 3, 4, 5, 100])
        result = detect_outliers_iqr(data)

        assert "outlier_values" in result
        assert "q1" in result
        assert "q3" in result
        assert "iqr" in result
        assert 100 in result["outlier_values"]

    def test_detect_outliers_no_outliers(self):
        data = pd.Series([1, 2, 3, 4, 5])
        result = detect_outliers_iqr(data)

        assert len(result["outlier_values"]) == 0
        assert result["n_outliers"] == 0


class TestRunCorrelationMatrix:
    def test_correlation_matrix_basic(self):
        df = pd.DataFrame(
            {
                "a": [1, 2, 3, 4, 5],
                "b": [2, 4, 6, 8, 10],
                "c": [5, 4, 3, 2, 1],
            }
        )
        result = run_correlation_matrix(df)

        assert result is not None

    def test_correlation_perfect_positive(self):
        df = pd.DataFrame(
            {
                "a": [1, 2, 3, 4, 5],
                "b": [2, 4, 6, 8, 10],
            }
        )
        result = run_correlation_matrix(df)

        assert result is not None


class TestRunMannWhitneyU:
    def test_mannwhitneyu_basic(self):
        group1 = pd.Series([1, 2, 3, 4, 5])
        group2 = pd.Series([6, 7, 8, 9, 10])
        result = run_mannwhitneyu(group1, group2)

        assert "statistic" in result
        assert "p_value" in result


class TestRunKruskal:
    def test_kruskal_basic(self):
        g1 = pd.Series([1, 2, 3])
        g2 = pd.Series([4, 5, 6])
        g3 = pd.Series([7, 8, 9])
        result = run_kruskal(g1, g2, g3)

        assert "statistic" in result
        assert "p_value" in result


class TestSuggestTest:
    def test_suggest_test_two_groups(self):
        g1 = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        g2 = pd.Series([2, 3, 4, 5, 6, 7, 8, 9, 10, 11])
        result = suggest_test([g1, g2])

        assert "suggestion" in result
        assert "recommended_func" in result
