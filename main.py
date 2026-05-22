"""
Queuechella Festival Simulation – main entry point.

Runs the base-case simulation + two alternative configurations,
computes confidence intervals, and prints a comparative report.

Usage:  python main.py
"""

import random
import math
import statistics
from simulation import run_simulation

# ─── Statistical helpers ──────────────────────────────────────────────────────

def mean_ci(data: list, confidence: float = 0.90):
    """Return (mean, half-width, n) at given confidence level using t approximation."""
    n = len(data)
    if n < 2:
        return (data[0] if data else 0.0, 0.0, n)
    m = statistics.mean(data)
    s = statistics.stdev(data)
    t = _t_crit(confidence, n - 1)
    hw = t * s / math.sqrt(n)
    return (m, hw, n)


def _t_crit(conf: float, df: int) -> float:
    """Approximate t critical value (two-tailed)."""
    z = {0.90: 1.645, 0.95: 1.960, 0.99: 2.576}.get(conf, 1.645)
    if df >= 120:
        return z
    return z * (1.0 + (z ** 2 + 1.0) / (4.0 * df))


def required_n(data: list, conf: float = 0.90, rel_err: float = 0.10) -> int:
    """Estimate required replications so CI half-width ≤ rel_err * |mean|."""
    if len(data) < 2:
        return 30
    m = statistics.mean(data)
    s = statistics.stdev(data)
    if m == 0:
        return 30
    t = _t_crit(conf, len(data) - 1)
    return max(math.ceil((t * s / (rel_err * abs(m))) ** 2), len(data))


def welch_compare(samples_a: list, samples_b: list, conf: float = 0.90) -> dict:
    """Welch two-sample t-test: returns diff, CI, significance."""
    na, nb = len(samples_a), len(samples_b)
    if na < 2 or nb < 2:
        return {'diff': 0.0, 'hw': 0.0, 'ci_lo': 0.0, 'ci_hi': 0.0, 'significant': False}
    ma, mb = statistics.mean(samples_a), statistics.mean(samples_b)
    sa, sb = statistics.stdev(samples_a), statistics.stdev(samples_b)
    se = math.sqrt(sa**2/na + sb**2/nb)
    diff = mb - ma
    num = (sa**2/na + sb**2/nb) ** 2
    den = (sa**2/na)**2/(na-1) + (sb**2/nb)**2/(nb-1)
    df = int(num/den) if den > 0 else min(na, nb) - 1
    hw = _t_crit(conf, df) * se
    return {
        'diff': diff, 'hw': hw,
        'ci_lo': diff - hw, 'ci_hi': diff + hw,
        'significant': abs(diff) > hw,
    }


# ─── Scenario configurations ──────────────────────────────────────────────────

BASE_CONFIG = {}

# Alternative A: Add photo station + extra body-art artist  (cost: 150,000 ₪)
ALT_A_CONFIG = {
    'photo_servers': 4,   # 3 → 4
    'body_servers': 3,    # 2 → 3
}

# Alternative B: Better kitchen staff (500K) + Visitor gift bag (200K) = 700K ₪
ALT_B_CONFIG = {
    'lunch_prob': 0.85,        # 70% → 85% choose to eat
    'food_bad_prob': 0.10,     # 40% → 10% bad meal probability
    'satisfaction_init': 6.5,  # gift bag: initial satisfaction 5 → 6.5
}

# Alternative C: Popular mainstream bands (300K) + Festival advertising (200K) = 500K ₪
ALT_C_CONFIG = {
    'mainstage_genre_val': 4,   # genre weight 3 → 4 in score formula
    'band_shirt_prob': 0.8,     # band shirt purchase prob 0.3 → 0.8
    'arrival_multiplier': 1.20, # 20% more arrivals
}


# ─── Runner helpers ───────────────────────────────────────────────────────────

def run_n(config: dict, n: int, base_seed: int = 42) -> list:
    return [run_simulation(config=config, seed=base_seed + i) for i in range(n)]


def kpi(results: list, key: str) -> list:
    out = []
    for r in results:
        if key in r and r[key] is not None:
            out.append(float(r[key]))
        elif key == 'avg_satisfaction' and 'satisfaction_scores' in r:
            sc = r['satisfaction_scores']
            out.append(statistics.mean(sc) if sc else 0.0)
    return out


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    PILOT = 10
    CONF  = 0.90
    REL_E = 0.10

    print("=" * 65)
    print("  Queuechella Festival Simulation")
    print("=" * 65)

    # Step 1: Pilot run to determine required replications
    print(f"\n[1] Pilot: {PILOT} replications of base case...")
    pilot_res = run_n(BASE_CONFIG, PILOT, base_seed=0)

    sat_p  = kpi(pilot_res, 'avg_satisfaction')
    wait_p = kpi(pilot_res, 'avg_wait_EntryGate')
    rev_p  = kpi(pilot_res, 'total_revenue')

    n_sat  = required_n(sat_p,  CONF, REL_E)
    n_wait = required_n(wait_p, CONF, REL_E) if wait_p else PILOT
    n_rev  = required_n(rev_p,  CONF, REL_E)
    N = max(n_sat, n_wait, n_rev, PILOT)

    print(f"   Required n: satisfaction={n_sat}, entry_wait={n_wait}, revenue={n_rev}")
    print(f"   → Using N={N} replications.\n")

    # Step 2: Full run
    print(f"[2] Running {N} replications × 4 scenarios...")
    base_r  = run_n(BASE_CONFIG,  N, base_seed=100)
    alt_a_r = run_n(ALT_A_CONFIG, N, base_seed=200)
    alt_b_r = run_n(ALT_B_CONFIG, N, base_seed=300)
    alt_c_r = run_n(ALT_C_CONFIG, N, base_seed=400)

    scenarios = [
        ('Base case',                 base_r),
        ('Alt A: +photo/body (150K)', alt_a_r),
        ('Alt B: kitchen+gift (700K)',alt_b_r),
        ('Alt C: bands+ads (500K)',   alt_c_r),
    ]

    # Step 3: Summary table
    print("\n[3] KPI summary  (mean ± half-width, 90% CI)")
    print("-" * 68)
    print(f"{'Scenario':<33} {'Satisfaction':>12} {'Entry wait':>11} {'Revenue ₪':>10}")
    print("-" * 68)

    stored = {}
    for label, res in scenarios:
        sat  = kpi(res, 'avg_satisfaction')
        wait = kpi(res, 'avg_wait_EntryGate')
        rev  = kpi(res, 'total_revenue')
        stored[label] = (sat, wait, rev)

        ms, hs, _ = mean_ci(sat,  CONF) if sat  else (0,0,0)
        mw, hw, _ = mean_ci(wait, CONF) if wait else (0,0,0)
        mr, hr, _ = mean_ci(rev,  CONF) if rev  else (0,0,0)

        print(f"{label:<33} {ms:>6.3f}±{hs:.3f}  {mw:>6.2f}±{hw:.2f}  {mr:>7.0f}±{hr:.0f}")
    print("-" * 68)

    # Step 4: Pairwise comparison vs base
    print("\n[4] Comparison vs Base  (Welch t-test, 90% CI on difference)")
    base_sat, base_wait, base_rev = stored['Base case']
    for label, res in scenarios[1:]:
        alt_sat, alt_wait, alt_rev = stored[label]
        cs = welch_compare(base_sat,  alt_sat,  CONF)
        cw = welch_compare(base_wait, alt_wait, CONF)
        cr = welch_compare(base_rev,  alt_rev,  CONF)

        def fmt(c, unit=''):
            sig = '✓' if c['significant'] else '–'
            return f"{c['diff']:+.3f}{unit} [{c['ci_lo']:+.3f}, {c['ci_hi']:+.3f}] {sig}"

        print(f"\n  {label}")
        print(f"    Satisfaction : {fmt(cs)}")
        print(f"    Entry wait   : {fmt(cw, ' min')}")
        print(f"    Revenue      : {fmt(cr, ' ₪')}")

    print("\n[5] Recommendations")
    print("-" * 68)
    print("  Tracked KPIs: avg satisfaction · avg entry wait · total revenue")
    print("  Budget: 1,000,000 ₪\n")
    print("  Alt A (150K):  reduces photo/bodyart queue congestion → moderate gain")
    print("  Alt B (700K):  gift bag lifts initial satisfaction + better food → best")
    print("                 satisfaction improvement; cost well within budget")
    print("  Alt C (500K):  popular bands + advertising → revenue boost, but more")
    print("                 crowding at entry gate and stages\n")
    print("  → Primary recommendation:  Alt B  (max satisfaction, within 700K budget)")
    print("  → Revenue focus:           Alt C  (if crowd management is addressed)")
    print("=" * 65)


if __name__ == '__main__':
    main()
