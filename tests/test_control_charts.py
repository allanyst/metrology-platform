from __future__ import annotations
import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from models.predictive import predict_days_to_failure


def test_linear_drift_detected():
    errors = np.linspace(0, 0.0001, 365)
    result = predict_days_to_failure(errors, tolerance=0.0002)
    assert result["trend"] == "INCREASING"
    assert result["days_to_failure"] is not None
    assert result["days_to_failure"] > 0


def test_stable_instrument_low_risk():
    rng = np.random.default_rng(42)
    errors = rng.normal(0, 0.00001, 365)
    result = predict_days_to_failure(errors, tolerance=0.0002)
    assert result["risk_level"] == "LOW"


def test_already_out_of_tolerance():
    errors = np.linspace(0, 0.0005, 365)
    result = predict_days_to_failure(errors, tolerance=0.0002)
    assert result["days_to_failure"] == 0


def test_decreasing_drift_no_failure():
    errors = np.linspace(0.0001, 0, 365)
    result = predict_days_to_failure(errors, tolerance=0.0002)
    assert result["trend"] == "DECREASING"
    assert result["days_to_failure"] is None or result["days_to_failure"] > 365


def test_risk_levels():
    errors_critical = np.linspace(0, 0.00019, 365)
    result = predict_days_to_failure(errors_critical, tolerance=0.0002)
    assert result["risk_level"] in ["CRITICAL", "HIGH", "MEDIUM"]

    errors_low = np.linspace(0, 0.00001, 365)
    result_low = predict_days_to_failure(errors_low, tolerance=0.0002)
    assert result_low["risk_level"] == "LOW"