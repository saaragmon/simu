"""
Sampling functions for Queuechella simulation.
All samples are derived from U(0,1) using inverse transform, Box-Muller, or acceptance-rejection.

Distribution fitting results (from samples_for_simulation.xlsx):
  - FriendsGroup arrival intervals: Exponential(mean=1.371 min)  [n=100, mean=1.37, std=1.19, CV≈0.87]
  - MainStage concert duration:     Normal(mu=45.9, sigma=8.97)  [n=100, mean=45.9, std=8.97]
"""

import math
import random


def u01() -> float:
    return random.random()


# ─── Inverse Transform ───────────────────────────────────────────────────────

def sample_exponential(mean: float) -> float:
    """F^-1(u) = -mean * ln(1-u)"""
    return -mean * math.log(1.0 - u01())


def sample_uniform_continuous(a: float, b: float) -> float:
    """F^-1(u) = a + (b-a)*u"""
    return a + (b - a) * u01()


def sample_uniform_discrete(a: int, b: int) -> int:
    """Discrete uniform on {a, ..., b}"""
    return math.floor(a + (b - a + 1) * u01())


# ─── Box-Muller for Normal ────────────────────────────────────────────────────

_bm_spare: float | None = None


def sample_normal(mu: float, sigma: float) -> float:
    """Box-Muller transform produces two standard normals per pair of uniforms."""
    global _bm_spare
    if _bm_spare is not None:
        z = _bm_spare
        _bm_spare = None
        return mu + sigma * z
    while True:
        u1, u2 = u01(), u01()
        if u1 > 0:
            break
    mag = math.sqrt(-2.0 * math.log(u1))
    z0 = mag * math.cos(2.0 * math.pi * u2)
    z1 = mag * math.sin(2.0 * math.pi * u2)
    _bm_spare = z1
    return mu + sigma * z0


def sample_normal_positive(mu: float, sigma: float) -> float:
    """Sample normal, rejecting non-positive values."""
    while True:
        v = sample_normal(mu, sigma)
        if v > 0:
            return v


# ─── Acceptance-Rejection: DJStage stay duration ─────────────────────────────
# f(x) = (x-20)/600          20 ≤ x ≤ 40
#         (60-x)/600 + 1/30   40 < x ≤ 50
#         (60-x)/600          50 < x ≤ 60
# Maximum at x=40⁺: (60-40)/600 + 1/30 = 20/600 + 20/600 = 1/15
# Proposal: Uniform[20,60], g(x)=1/40
# M = max f(x)/g(x) = (1/15)/(1/40) = 40/15

def _dj_pdf(x: float) -> float:
    if 20.0 <= x <= 40.0:
        return (x - 20.0) / 600.0
    elif 40.0 < x <= 50.0:
        return (60.0 - x) / 600.0 + 1.0 / 30.0
    elif 50.0 < x <= 60.0:
        return (60.0 - x) / 600.0
    return 0.0


_DJ_M = 40.0 / 15.0  # = max f / g where g = 1/40


def sample_dj_stay() -> float:
    """Acceptance-rejection for DJStage stay time (minutes, range [20,60])."""
    while True:
        x = sample_uniform_continuous(20.0, 60.0)
        if u01() <= _dj_pdf(x) * 40.0 / _DJ_M:
            return x


# ─── Composition: PhotoStation service duration ───────────────────────────────
# f(x) = x/6          1 ≤ x < 2
#         x/5 + 1/8   2 ≤ x < 3
#         1/8         3 ≤ x < 4
# CDF breakpoints: F(2) = (4-1)/12 = 1/4 = 0.25
#                  F(3) = 1/4 + [t²/10+t/8]₂³ = 7/8 = 0.875
#                  F(4) = 1.0

def sample_photo_duration() -> float:
    """Inverse CDF via piecewise integration for photo service time (minutes)."""
    p = u01()
    if p < 0.25:
        # F(x)=(x²-1)/12 => x=sqrt(12p+1)
        return math.sqrt(12.0 * p + 1.0)
    elif p < 0.875:
        # 4x² + 5x - (40p+16) = 0
        disc = 25.0 + 16.0 * (40.0 * p + 16.0)
        return (-5.0 + math.sqrt(disc)) / 8.0
    else:
        # F(x)=7/8+(x-3)/8 => x=3+8(p-7/8)
        return 3.0 + 8.0 * (p - 0.875)


# ─── Inverse Transform: ChargingStation duration ──────────────────────────────
# b = battery level (Normal(40,15), clipped to [0,99])
# α = 100/(100-b)
# f(t) = α/40^α * (40-t)^(α-1)  0 ≤ t ≤ 40
# CDF: F(t) = 1 - ((40-t)/40)^α
# F^-1(u) = 40 - 40*(1-u)^(1/α)

def sample_battery_level() -> float:
    b = sample_normal(40.0, 15.0)
    return max(0.0, min(99.9, b))


def sample_charging_duration(b: float) -> float:
    """Inverse transform for charging time given battery level b (%)."""
    alpha = 100.0 / (100.0 - b)
    return 40.0 - 40.0 * ((1.0 - u01()) ** (1.0 / alpha))


# ─── Fitted distributions ─────────────────────────────────────────────────────

def sample_friends_arrival_interval() -> float:
    """Exponential fitted to data: mean=1.371 min."""
    return sample_exponential(1.371)


def sample_mainstage_duration() -> float:
    """Normal fitted to data: mu=45.9, sigma=8.97 min. Clamped positive."""
    return sample_normal_positive(45.9, 8.97)


# ─── Other simulation distributions ──────────────────────────────────────────

def sample_sidestage_duration() -> float:
    return sample_uniform_continuous(20.0, 30.0)

def sample_couple_interval() -> float:
    """60 couples/hour → mean inter-arrival = 1 min."""
    return sample_exponential(1.0)

def sample_single_interval() -> float:
    """500 singles/day over 7 arrival hours (420 min) → mean = 420/500 min."""
    return sample_exponential(420.0 / 500.0)

def sample_ticket_scan() -> float:
    return sample_uniform_continuous(1.5, 3.0)

def sample_security_check() -> float:
    return sample_exponential(2.0)

def sample_merch_service() -> float:
    return sample_uniform_continuous(2.0, 6.0)

def sample_bodyart_glitter() -> float:
    return sample_normal_positive(15.0, 3.0)

def sample_bodyart_neon() -> float:
    return sample_exponential(12.0)

def sample_bodyart_henna() -> float:
    return sample_uniform_continuous(17.0, 22.0)

def sample_friends_group_size() -> int:
    return sample_uniform_discrete(3, 6)

def sample_food_cashier_service() -> float:
    return sample_normal_positive(5.0, 1.5)

def sample_eating_time() -> float:
    return sample_uniform_continuous(15.0, 35.0)

def sample_pizza_prep() -> float:
    return sample_uniform_continuous(4.0, 6.0)

def sample_burger_prep() -> float:
    return sample_uniform_continuous(3.0, 4.0)

def sample_asian_prep() -> float:
    return sample_uniform_continuous(3.0, 7.0)
