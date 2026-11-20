"""Dependence-aware descriptive uncertainty; no independence claim for hourly rows."""
import numpy as np


def block_indices(n, rng, block=7):
    if n < block:
        raise ValueError("Insufficient daily history for block bootstrap")
    starts = rng.integers(0, n - block + 1, size=int(np.ceil(n / block)))
    return np.concatenate([np.arange(s, s + block) for s in starts])[:n]


def daily_ratio_ci(numerator, denominator, repetitions=500, seed=42):
    numerator, denominator = np.asarray(numerator), np.asarray(denominator)
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(repetitions):
        ix = block_indices(len(numerator), rng)
        den = denominator[ix].sum()
        if den:
            draws.append(numerator[ix].sum() / den)
    return np.quantile(draws, [.025, .975])
