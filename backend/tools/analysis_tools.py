"""
Analysis tools — statistical computations using Pandas, NumPy, SciPy.
Exposes real calculation capabilities that agents can invoke.
"""
import os
import sys
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def run_correlation_analysis(data: dict, x_col: str, y_col: str) -> dict[str, Any]:
    """
    Compute Pearson correlation between two numeric columns.
    Returns correlation coefficient, p-value, interpretation.
    """
    df = pd.DataFrame(data.get("rows", []))
    if df.empty or x_col not in df.columns or y_col not in df.columns:
        return {"error": "Insufficient data for correlation analysis"}

    df = df[[x_col, y_col]].dropna()
    if len(df) < 3:
        return {"error": "Not enough data points for correlation (need ≥ 3)"}

    r, p_value = stats.pearsonr(df[x_col].astype(float), df[y_col].astype(float))

    interpretation = (
        "Very strong positive correlation" if r > 0.9 else
        "Strong positive correlation" if r > 0.7 else
        "Moderate positive correlation" if r > 0.5 else
        "Weak positive correlation" if r > 0.3 else
        "Very strong negative correlation" if r < -0.9 else
        "Strong negative correlation" if r < -0.7 else
        "No significant correlation"
    )

    return {
        "x_column": x_col,
        "y_column": y_col,
        "pearson_r": round(r, 4),
        "p_value": round(p_value, 6),
        "significant": p_value < 0.05,
        "interpretation": interpretation,
        "n_observations": len(df)
    }


def detect_trend_change(dates: list, values: list, change_date: str = None) -> dict[str, Any]:
    """
    Detect if there's a statistically significant change in a time series.
    Optionally tests at a specific date (change-point detection).
    """
    if len(values) < 4:
        return {"error": "Need at least 4 data points"}

    values_arr = np.array(values, dtype=float)
    n = len(values_arr)

    if change_date and dates:
        # Split at change point if given
        split_idx = next((i for i, d in enumerate(dates) if d >= change_date), n // 2)
        split_idx = max(2, min(split_idx, n - 2))
    else:
        split_idx = n // 2

    before = values_arr[:split_idx]
    after = values_arr[split_idx:]

    # Mann-Whitney U test (non-parametric)
    u_stat, p_value = stats.mannwhitneyu(before, after, alternative='two-sided')

    before_mean = float(np.mean(before))
    after_mean = float(np.mean(after))
    change_magnitude = (after_mean - before_mean) / before_mean if before_mean != 0 else 0

    return {
        "split_date": dates[split_idx] if dates else f"index_{split_idx}",
        "before_mean": round(before_mean, 4),
        "after_mean": round(after_mean, 4),
        "change_magnitude_pct": round(change_magnitude * 100, 2),
        "mann_whitney_u": round(u_stat, 2),
        "p_value": round(p_value, 6),
        "statistically_significant": p_value < 0.05,
        "interpretation": (
            f"Statistically significant change detected (p={p_value:.4f}). "
            f"Mean increased by {change_magnitude*100:.1f}% after {dates[split_idx] if dates else 'split point'}."
            if p_value < 0.05 else
            "No statistically significant change detected."
        )
    }


def detect_anomalies(data: dict, column: str, threshold_std: float = 2.0) -> dict[str, Any]:
    """
    Z-score based anomaly detection. Flags values beyond threshold standard deviations.
    """
    df = pd.DataFrame(data.get("rows", []))
    if df.empty or column not in df.columns:
        return {"error": f"Column '{column}' not found"}

    series = df[column].astype(float).dropna()
    mean = float(series.mean())
    std = float(series.std())

    if std == 0:
        return {"mean": mean, "std": 0, "anomalies": [], "anomaly_count": 0}

    z_scores = (series - mean) / std
    anomaly_mask = z_scores.abs() > threshold_std
    anomaly_indices = df.index[series.index[anomaly_mask]]

    anomalies = []
    for idx in anomaly_indices:
        if idx < len(df):
            row = df.iloc[idx].to_dict()
            row["z_score"] = round(float(z_scores.iloc[list(series.index).index(idx)]), 2)
            anomalies.append(row)

    return {
        "column": column,
        "mean": round(mean, 4),
        "std": round(std, 4),
        "threshold_std": threshold_std,
        "anomaly_count": len(anomalies),
        "anomalies": anomalies[:10],  # Cap at 10
        "interpretation": (
            f"Found {len(anomalies)} anomalous readings in '{column}' (>{threshold_std}σ from mean)."
            if anomalies else
            f"No anomalies detected in '{column}'."
        )
    }


def compute_defect_statistics(defect_rates: list) -> dict[str, Any]:
    """Compute descriptive statistics for defect rate data."""
    arr = np.array(defect_rates, dtype=float)
    return {
        "count": len(arr),
        "mean": round(float(arr.mean()), 4),
        "std": round(float(arr.std()), 4),
        "min": round(float(arr.min()), 4),
        "max": round(float(arr.max()), 4),
        "median": round(float(np.median(arr)), 4),
        "p25": round(float(np.percentile(arr, 25)), 4),
        "p75": round(float(np.percentile(arr, 75)), 4),
        "p95": round(float(np.percentile(arr, 95)), 4),
    }


def run_hypothesis_test(group_a: list, group_b: list, hypothesis: str) -> dict[str, Any]:
    """
    Independent samples t-test to compare two groups.
    Used to test hypotheses like "M17 defect rate is different from M02".
    """
    a = np.array(group_a, dtype=float)
    b = np.array(group_b, dtype=float)

    t_stat, p_value = stats.ttest_ind(a, b, equal_var=False)

    return {
        "hypothesis": hypothesis,
        "group_a_mean": round(float(a.mean()), 4),
        "group_b_mean": round(float(b.mean()), 4),
        "t_statistic": round(float(t_stat), 4),
        "p_value": round(float(p_value), 6),
        "significant": p_value < 0.05,
        "conclusion": (
            f"SUPPORTED (p={p_value:.4f} < 0.05): {hypothesis}"
            if p_value < 0.05 else
            f"NOT SUPPORTED (p={p_value:.4f} ≥ 0.05): {hypothesis}"
        )
    }

def simulate_thermal_stress(hardness_rating: float, rpm: float) -> dict[str, Any]:
    """
    Mock physics simulation for a machine spindle cutting alloy.
    Calculates temperature increase based on material hardness and machine RPM.
    """
    base_temp = 25.0 # Ambient
    # Frictional heating model (simplified)
    friction_coefficient = hardness_rating / 80.0
    heating_rate = friction_coefficient * (rpm / 1000.0) * 4.2
    
    peak_temp = base_temp + heating_rate
    
    threshold = 80.0
    exceeds = peak_temp > threshold
    
    return {
        "simulation": "Spindle Thermal Stress Model",
        "inputs": {"hardness_rating": hardness_rating, "rpm": rpm},
        "peak_temperature_c": round(peak_temp, 2),
        "threshold_c": threshold,
        "exceeds_threshold": exceeds,
        "risk_level": "HIGH" if exceeds else "LOW",
        "conclusion": f"Cutting material with hardness {hardness_rating} at {rpm} RPM results in {peak_temp:.1f}°C. {'DANGER: Exceeds threshold!' if exceeds else 'Safe.'}"
    }
