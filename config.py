"""
SimConfig – all tunable simulation parameters in one place.
Pass a SimConfig instance to FestivalSimulation to run a scenario.
"""

from dataclasses import dataclass, field


@dataclass
class SimConfig:
    # ── Entry gate ────────────────────────────────────────────────────────
    entry_servers: int = 5

    # ── Stage capacities ──────────────────────────────────────────────────
    mainstage_cap: int = 200
    sidestage_cap: int = 100
    djstage_cap: int = 70

    # ── Service-station server counts ──────────────────────────────────────
    photo_servers: int = 3
    charging_servers: int = 150
    merch_servers: int = 7
    body_servers: int = 2

    # ── Probabilities ─────────────────────────────────────────────────────
    lunch_prob: float = 0.70          # fraction of guests who eat lunch 13-15
    photo_satisfied_prob: float = 0.70
    food_bad_prob: float = 0.40       # probability a meal is unsatisfying

    # ── Merch ─────────────────────────────────────────────────────────────
    band_shirt_prob: float = 0.30

    # ── Satisfaction ──────────────────────────────────────────────────────
    satisfaction_init: float = 5.0

    # ── Show genre values (G in score formula) ────────────────────────────
    mainstage_genre_val: int = 3
    sidestage_genre_val: int = 2
    djstage_genre_val: int = 1

    # ── Arrival scaling (1.0 = baseline) ─────────────────────────────────
    arrival_multiplier: float = 1.0

    def clone(self, **overrides) -> "SimConfig":
        """Return a copy with selected fields overridden."""
        import copy
        cfg = copy.copy(self)
        for k, v in overrides.items():
            setattr(cfg, k, v)
        return cfg
