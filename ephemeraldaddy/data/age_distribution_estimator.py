from __future__ import annotations
import math
import random
from dataclasses import dataclass
from typing import List, Tuple, Dict

# ---------- helpers ----------

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def logistic(x: float) -> float:
    # stable-ish logistic
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    else:
        z = math.exp(x)
        return z / (1.0 + z)

def normal_pdf(x: float, mu: float, sigma: float) -> float:
    if sigma <= 0:
        return 0.0
    z = (x - mu) / sigma
    return math.exp(-0.5 * z * z) / (sigma * math.sqrt(2.0 * math.pi))

def truncated_normal_pdf(x: float, mu: float, sigma: float, lo: float, hi: float) -> float:
    # approximate normalization by numeric integration (fast enough for model use)
    # If you need speed, precompute Z on a grid by (mu, sigma, lo, hi).
    if x < lo or x > hi:
        return 0.0
    # numeric Z
    steps = 400
    dx = (hi - lo) / steps
    zsum = 0.0
    for i in range(steps + 1):
        xi = lo + i * dx
        w = 0.5 if (i == 0 or i == steps) else 1.0
        zsum += w * normal_pdf(xi, mu, sigma)
    Z = zsum * dx
    if Z <= 0:
        return 0.0
    return normal_pdf(x, mu, sigma) / Z

def sample_component(weights: Tuple[float, float, float], rng: random.Random) -> int:
    r = rng.random()
    c0 = weights[0]
    c1 = c0 + weights[1]
    return 0 if r < c0 else (1 if r < c1 else 2)

def sample_truncated_normal(mu: float, sigma: float, lo: float, hi: float, rng: random.Random) -> float:
    # rejection sampling (ok because truncation is mild)
    for _ in range(10_000):
        x = rng.gauss(mu, sigma)
        if lo <= x <= hi:
            return x
    # fallback: clamp a draw if rejection fails
    return clamp(rng.gauss(mu, sigma), lo, hi)

# ---------- age-conditioned parameterization ----------

@dataclass(frozen=True)
class AgeMixParams:
    # mixture weights
    w_peer: float
    w_older: float
    w_younger: float
    # component centers in delta-space
    mu_peer: float
    mu_older: float
    mu_younger: float
    # component spreads
    sig_peer: float
    sig_older: float
    sig_younger: float

def generation_gap(user_age: float) -> float:
    """
    Typical parent-child age gap is often modeled ~25-30.
    Let it vary slightly across ego age (weak effect).
    """
    return clamp(27.0 + 0.03 * (user_age - 40.0), 24.0, 31.0)

def age_mix_params(user_age: float) -> AgeMixParams:
    """
    Heuristic, life-course-shaped weights.
    Tunable. Designed to be smooth and sensible without any extra covariates.
    """
    A = user_age
    G = generation_gap(A)

    # Peer dominates early; gradually declines but stays strong.
    # Use a slow logistic to reduce peer share with age.
    peer = 0.80 - 0.20 * logistic((A - 35.0) / 8.0)  # ~0.80 -> ~0.60
    peer = clamp(peer, 0.55, 0.85)

    # Younger-gen rises around typical childbearing/mentoring years.
    younger = 0.02 + 0.18 * logistic((A - 30.0) / 6.0) * (1.0 - logistic((A - 65.0) / 7.0))
    # Older-gen present for most; slightly higher when young (parents) and again late (care ties).
    older = 0.08 + 0.10 * (1.0 - logistic((A - 28.0) / 5.0)) + 0.06 * logistic((A - 70.0) / 6.0)

    # Normalize (and ensure non-negative)
    older = max(0.0, older)
    younger = max(0.0, younger)

    total = peer + older + younger
    w_peer, w_older, w_younger = peer / total, older / total, younger / total

    # Centers in delta (alter - ego)
    mu_peer = 0.0
    mu_older = +G
    mu_younger = -G

    # Spreads: peers widen with age (cohort broadening), intergen relatively tight.
    sig_peer = clamp(2.0 + 0.06 * A, 2.0, 9.0)        # ~2 at 0, ~5.6 at 60, capped
    sig_older = 3.5
    sig_younger = 3.5

    return AgeMixParams(
        w_peer=w_peer, w_older=w_older, w_younger=w_younger,
        mu_peer=mu_peer, mu_older=mu_older, mu_younger=mu_younger,
        sig_peer=sig_peer, sig_older=sig_older, sig_younger=sig_younger
    )

# ---------- public API ----------

def alter_age_pdf(alter_age: float, user_age: float, min_age: float = 0.0, max_age: float = 100.0) -> float:
    """
    Probability density over alter ages for a given user_age.
    Continuous density; convert to discrete probabilities by integrating per year/bin.
    """
    p = age_mix_params(user_age)
    # delta space truncation induced by age bounds
    lo = min_age - user_age
    hi = max_age - user_age
    d = alter_age - user_age

    peer = truncated_normal_pdf(d, p.mu_peer, p.sig_peer, lo, hi)
    oldr = truncated_normal_pdf(d, p.mu_older, p.sig_older, lo, hi)
    yngr = truncated_normal_pdf(d, p.mu_younger, p.sig_younger, lo, hi)

    return p.w_peer * peer + p.w_older * oldr + p.w_younger * yngr

def sample_alter_age(user_age: float, rng: random.Random | None = None,
                     min_age: float = 0.0, max_age: float = 100.0) -> float:
    """
    Draw a single alter age from the model.
    """
    rng = rng or random.Random()
    p = age_mix_params(user_age)

    lo = min_age - user_age
    hi = max_age - user_age

    comp = sample_component((p.w_peer, p.w_older, p.w_younger), rng)
    if comp == 0:
        d = sample_truncated_normal(p.mu_peer, p.sig_peer, lo, hi, rng)
    elif comp == 1:
        d = sample_truncated_normal(p.mu_older, p.sig_older, lo, hi, rng)
    else:
        d = sample_truncated_normal(p.mu_younger, p.sig_younger, lo, hi, rng)

    return user_age + d

def discrete_age_distribution(user_age: float, *,
                              bin_width: int = 1,
                              min_age: int = 0,
                              max_age: int = 100) -> List[Tuple[int, float]]:
    """
    Discretize to per-year (or per-bin) probabilities by midpoint rule.
    Returns list of (bin_start_age, prob).
    """
    bins = []
    for a in range(min_age, max_age + 1, bin_width):
        mid = a + 0.5 * (bin_width - 1 if bin_width > 1 else 0)
        bins.append((a, alter_age_pdf(mid, user_age, min_age, max_age)))

    # normalize to sum to 1 over bins
    s = sum(p for _, p in bins)
    if s > 0:
        bins = [(a, p / s) for a, p in bins]
    return bins

def infer_user_age_from_alter_ages(
    alter_ages: List[float],
    *,
    min_user_age: int = 1,
    max_user_age: int = 110, #assuming...
    min_alter_age: int = 0,
    max_alter_age: int = 110,
) -> float | None:
    """
    Reverse inference: estimate the most likely user age from observed alter ages.

    Uses maximum log-likelihood across a discrete user-age grid under the
    forward model P(alter_age | user_age).
    """
    if not alter_ages:
        return None

    observed = [float(a) for a in alter_ages if min_alter_age <= float(a) <= max_alter_age]
    if not observed:
        return None

    best_age: float | None = None
    best_ll = float("-inf")
    eps = 1e-12

    for candidate_age in range(min_user_age, max_user_age + 1):
        ll = 0.0
        for alter_age in observed:
            density = alter_age_pdf(
                alter_age,
                float(candidate_age),
                min_age=float(min_alter_age),
                max_age=float(max_alter_age),
            )
            ll += math.log(max(density, eps))
        if ll > best_ll:
            best_ll = ll
            best_age = float(candidate_age)

    return best_age
