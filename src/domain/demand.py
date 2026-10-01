"""One-day-ahead supervised demand benchmark, isolated from production pricing.

Numpy ridge regression is deliberately small and inspectable. Temporal splits,
train-only scaling and frozen holdout evaluation are part of the model contract.
"""
from datetime import date
import hashlib
import json
import math
import platform
from statistics import mean
from typing import Literal

import numpy as np
from pydantic import Field, model_validator
from src.domain.models import Contract, Identifier, Money

FEATURES = ("log_price", "log_competitor_price", "promotion", "trend_years",
            "weekday_sin", "weekday_cos", "log_recent_units")
VERSION = "daily-ridge-1"


class SalesDay(Contract):
    day: date
    price_gross: Money
    competitor_price_gross: Money
    units: int = Field(ge=0, le=100000)
    promotion: bool = False
    fully_in_stock: bool = True


class DemandHistory(Contract):
    product_id: Identifier
    origin: Literal["synthetic", "merchant"]
    rows: list[SalesDay] = Field(min_length=180, max_length=1095)

    @model_validator(mode="after")
    def daily_history(self):
        dates = sorted(r.day for r in self.rows)
        if len(set(dates)) != len(dates):
            raise ValueError("Only one row per day and product is allowed")
        if any((b-a).days != 1 for a, b in zip(dates, dates[1:])):
            raise ValueError("Daily history must be continuous; represent zero-sales days explicitly")
        if dates[-1] > date.today():
            raise ValueError("Training history cannot contain future sales")
        return self


def features(row, past, start):
    """No current/future units enter X. Features must be known before sale begins."""
    return [math.log(float(row.price_gross)), math.log(float(row.competitor_price_gross)),
            float(row.promotion), (row.day-start).days/365,
            math.sin(2*math.pi*row.day.weekday()/7), math.cos(2*math.pi*row.day.weekday()/7),
            math.log1p(mean(r.units for r in past[-7:]))]


def fit(x, y, alpha):
    x = np.asarray(x, dtype=float)
    center, scale = x.mean(axis=0), x.std(axis=0)
    scale[scale < 1e-8] = 1
    design = np.column_stack([np.ones(len(x)), (x-center)/scale])
    penalty = np.eye(design.shape[1])*alpha
    penalty[0, 0] = 0  # Never penalize the intercept.
    target = np.log1p(y)
    weights = np.linalg.solve(design.T@design+penalty, design.T@target)
    # Training-only smearing corrects the log transform's retransformation bias.
    smear = float(np.mean(np.exp(np.clip(target-design@weights, -20, 20))))
    return dict(center=center, scale=scale, weights=weights, smear=smear)


def predict(model, x):
    design = np.column_stack([np.ones(len(x)), (np.asarray(x)-model["center"])/model["scale"]])
    return np.maximum(0, np.exp(np.clip(design@model["weights"], -20, math.log(100001)))*model["smear"]-1).clip(0, 100000)


def metrics(actual, predicted):
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    error = predicted-actual
    volume = float(actual.sum())
    return {"mae": round(float(np.abs(error).mean()), 4),
            "rmse": round(float(np.sqrt(np.mean(error**2))), 4),
            "wape": round(float(np.abs(error).sum())/volume, 4) if volume else None,
            "bias_units": round(float(error.mean()), 4)}


def evaluate(history: DemandHistory):
    rows = sorted(history.rows, key=lambda r: r.day)
    # Fixed blocks: training / model selection / calibration / untouched test.
    bounds = (len(rows)-84, len(rows)-56, len(rows)-28)
    records = [(i, features(r, rows[:i], rows[0].day), r.units)
               for i, r in enumerate(rows) if i >= 7 and r.fully_in_stock]
    blocks = [[z for z in records if lo <= z[0] < hi]
              for lo, hi in zip((7, *bounds), (*bounds, len(rows))) ]
    train, validation, calibration, test = blocks
    if len(train) < 56 or any(len(b) < 14 for b in blocks[1:]):
        raise ValueError("Need 56 in-stock training days and 14 in-stock days in each final 28-day block")
    if sum(z[2] for z in train) == 0:
        raise ValueError("Training history has no observed sales; no learned model can be evaluated")
    def xy(block):
        return [z[1] for z in block], [z[2] for z in block]
    trials = []
    for alpha in (.1, 1., 10., 100.):
        model = fit(*xy(train), alpha)
        trials.append((metrics(xy(validation)[1], predict(model, xy(validation)[0]))["mae"], alpha))
    _, alpha = min(trials)
    model = fit(*xy(train+validation), alpha)
    calibration_error = np.abs(predict(model, xy(calibration)[0])-np.asarray(xy(calibration)[1]))
    # Finite-sample quantile; exchangeability is NOT assumed for retail time series.
    rank = min(len(calibration_error), math.ceil((len(calibration_error)+1)*.8))
    radius = float(sorted(calibration_error)[rank-1])
    predicted = predict(model, xy(test)[0])
    actual = xy(test)[1]
    recent = [mean(r.units for r in rows[i-7:i]) for i, _, _ in test]
    seasonal = [rows[i-7].units for i, _, _ in test]
    scores = {"ridge": metrics(actual, predicted), "recent_7d": metrics(actual, recent),
              "same_weekday": metrics(actual, seasonal)}
    coverage = mean(bool(max(0, p-radius) <= y <= p+radius) for y, p in zip(actual, predicted))
    fit_indices = [z[0] for z in train+validation]
    fit_prices = [float(rows[i].price_gross) for i in fit_indices]
    out_of_range = sum(not min(fit_prices) <= float(rows[i].price_gross) <= max(fit_prices) for i, _, _ in test)
    best_baseline = min(scores["recent_7d"]["mae"], scores["same_weekday"]["mae"])
    improvement = 1-scores["ridge"]["mae"]/best_baseline if best_baseline else None
    warnings = ["Observational price associations are not causal elasticity; never optimize live prices from this benchmark.",
                "One-day-ahead evaluation uses actual prior-day sales as they become available; this is not a 28-day forecast.",
                "Calibration bands are empirical. Time dependence and regime shifts can invalidate nominal 80% coverage.",
                "Price, competitor snapshot and promotion must be known at prediction time."]
    excluded = sum(not r.fully_in_stock for r in rows)
    if excluded:
        warnings.append(f"{excluded} stock-constrained days excluded as targets; their recorded sales remain in lag features.")
    if len(set(fit_prices)) < 5 or max(fit_prices)/min(fit_prices) < 1.05:
        warnings.append("Insufficient price variation to interpret a price response.")
    if out_of_range:
        warnings.append(f"{out_of_range} holdout days have prices outside the fitting range.")
    if history.origin == "synthetic":
        warnings.insert(0, "Synthetic benchmark: results demonstrate a pipeline, not retailer performance or ROI.")
    payload = {"product_id": history.product_id, "origin": history.origin,
               "rows": [r.model_dump(mode="json") for r in rows]}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    names = ("training", "validation", "calibration", "test")
    split = {name: {"start": str(rows[lo].day), "end": str(rows[hi-1].day), "usable_days": len(block)}
             for name, lo, hi, block in zip(names, (7, *bounds), (*bounds, len(rows)), blocks)}
    return {"model_version": VERSION, "dataset_sha256": digest, "origin": history.origin,
            "runtime": {"python": platform.python_version(), "numpy": np.__version__},
            "product_id": history.product_id, "rows": len(rows), "excluded_stockout_days": excluded,
            "selected_alpha": alpha, "selection_trials": [{"alpha": a, "validation_mae": v} for v, a in trials],
            "split": split, "metrics": scores, "mae_improvement_vs_best_baseline": improvement,
            "empirical_interval": {"nominal_coverage": .8, "observed_test_coverage": coverage, "radius_units": radius},
            "status": "research_only", "live_pricing_allowed": False,
            "beats_both_baselines": scores["ridge"]["mae"] < best_baseline,
            "features": list(FEATURES),
            "standardized_coefficients": dict(zip(FEATURES, map(float, model["weights"][1:]))),
            "warnings": warnings,
            "holdout": [{"day": str(rows[i].day), "actual": y, "predicted": round(float(p), 3),
                         "lower": round(max(0, float(p)-radius), 3), "upper": round(float(p)+radius, 3),
                         "recent_7d": round(r, 3), "same_weekday": s}
                        for (i, _, y), p, r, s in zip(test, predicted, recent, seasonal)]}
