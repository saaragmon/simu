"""
Entity hierarchy for the Queuechella festival simulation.

Entity (ABC)
├── FriendsGroup  – 3-6 friends, day-1 only, 70 % overnight
├── Couple        – 2 people, both days, overnight if satisfaction > 7
└── Single        – 1 person, one day only, fixed route
"""

from __future__ import annotations
import abc
import random
from typing import Optional

from distributions import sample_friends_group_size, u01

SATISFACTION_INIT = 5.0
SATISFACTION_MAX  = 10.0
SATISFACTION_MIN  = 0.0

_COUNTER: int = 0


def _next_id() -> int:
    global _COUNTER
    _COUNTER += 1
    return _COUNTER


def reset_entity_counter() -> None:
    global _COUNTER
    _COUNTER = 0


# ── Base class ────────────────────────────────────────────────────────────────

class Entity(abc.ABC):
    """Abstract base for all festival visitors."""

    PATIENCE: int = 20   # minutes willing to wait in any service queue

    def __init__(self, etype: str, group_size: int,
                 arrival_day: int, satisfaction_init: float = SATISFACTION_INIT):
        self.id           = _next_id()
        self.etype        = etype        # 'friends' | 'couple' | 'single'
        self.group_size   = group_size   # people represented by this entity
        self.arrival_day  = arrival_day
        self.satisfaction = satisfaction_init

        # Activity routing
        self.activities_todo: list[str] = []
        self.activities_done: list[str] = []

        # State flags (set by simulation)
        self.in_queue_at:   Optional[str] = None
        self.in_service_at: Optional[str] = None
        self.in_show_at:    Optional[str] = None
        self.left_festival: bool = False

        # Overnight flag (resolved at runtime per subclass rules)
        self.stays_overnight: bool = False

        # Per-replication statistics
        self.total_wait_min: float = 0.0
        self.total_revenue:  float = 0.0

        # Internal scratch fields used by the simulation engine
        self._queue_join_time: float = 0.0
        self.abandon_event = None   # reference to pending abandon Event

    # ── Satisfaction ──────────────────────────────────────────────────────

    def update_satisfaction(self, delta: float) -> None:
        self.satisfaction = max(SATISFACTION_MIN,
                                min(SATISFACTION_MAX, self.satisfaction + delta))

    # ── Revenue ───────────────────────────────────────────────────────────

    def spend(self, amount: float) -> None:
        self.total_revenue += amount

    # ── Activity routing ──────────────────────────────────────────────────

    @abc.abstractmethod
    def build_activities(self, station_queue_lengths: dict[str, int]) -> None:
        """Populate activities_todo based on entity type and current queue lengths."""

    def next_activity(self) -> Optional[str]:
        """Pop and return the next activity name, or None when done."""
        if not self.activities_todo:
            return None
        act = self.activities_todo.pop(0)
        self.activities_done.append(act)
        return act

    def peek_activity(self) -> Optional[str]:
        return self.activities_todo[0] if self.activities_todo else None

    def is_busy(self) -> bool:
        return (self.in_queue_at is not None
                or self.in_service_at is not None
                or self.in_show_at is not None)

    # ── Repr ──────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (f"{self.etype.capitalize()}#{self.id}"
                f"(n={self.group_size}, sat={self.satisfaction:.2f})")


# ── FriendsGroup ──────────────────────────────────────────────────────────────

class FriendsGroup(Entity):
    """
    Group of 3-6 friends.
    Arrive day 1 only, 09:00–13:00.
    Want exactly 1 show of each type + all 4 service stations.
    Stations are ordered by shortest queue at time of entry.
    70 % probability of staying overnight.
    Queue patience: 15 min.
    """

    PATIENCE = 15
    ALL_SHOWS    = ['MainStage', 'SideStage', 'DJStage']
    ALL_STATIONS = ['PhotoStation', 'ChargingStation', 'MerchTent', 'BodyArt']

    def __init__(self, arrival_day: int = 1,
                 satisfaction_init: float = SATISFACTION_INIT):
        size = sample_friends_group_size()
        super().__init__('friends', size, arrival_day, satisfaction_init)
        self.stays_overnight = (u01() < 0.70)

    def build_activities(self, station_queue_lengths: dict[str, int] = None) -> None:
        """Shows first (fixed order), then stations sorted by current queue length."""
        stations = list(self.ALL_STATIONS)
        if station_queue_lengths:
            stations.sort(key=lambda s: station_queue_lengths.get(s, 0))
        self.activities_todo = list(self.ALL_SHOWS) + stations


# ── Couple ────────────────────────────────────────────────────────────────────

class Couple(Entity):
    """
    Two-person couple.
    Arrive 10:00–16:00, both days.
    Alternates show → station → show → station …  (no DJStage).
    Stays overnight on day 1 only if satisfaction > 7 at end of day.
    Queue patience: 20 min.
    """

    PATIENCE = 20
    SHOWS    = ['MainStage', 'SideStage']
    STATIONS = ['PhotoStation', 'ChargingStation', 'MerchTent', 'BodyArt']
    _ROUNDS  = 8   # pre-generate this many alternating pairs

    def __init__(self, arrival_day: int = 1,
                 satisfaction_init: float = SATISFACTION_INIT):
        super().__init__('couple', 2, arrival_day, satisfaction_init)
        self.activities_todo = self._generate_alternating(self._ROUNDS)

    def _generate_alternating(self, rounds: int) -> list[str]:
        """Produce a show/station/show/station … list with equal probabilities."""
        seq = []
        for _ in range(rounds):
            seq.append(random.choice(self.SHOWS))
            seq.append(random.choice(self.STATIONS))
        return seq

    def build_activities(self, station_queue_lengths: dict[str, int] = None) -> None:
        """For Couple the list is already built in __init__; this refreshes it."""
        self.activities_todo = self._generate_alternating(self._ROUNDS)

    def refresh_if_low(self) -> None:
        """Called by the simulation engine when the todo list runs low."""
        if len(self.activities_todo) < 4:
            self.activities_todo += self._generate_alternating(4)


# ── Single ────────────────────────────────────────────────────────────────────

class Single(Entity):
    """
    Individual visitor.
    Arrive 09:00–16:00, one day only (day 1 or day 2).
    Fixed route: MerchTent → 2×MainStage → 2×SideStage → 1×DJStage.
    Queue patience: 20 min.
    """

    PATIENCE = 20
    FIXED_ROUTE = [
        'MerchTent',
        'MainStage', 'MainStage',
        'SideStage', 'SideStage',
        'DJStage',
    ]

    def __init__(self, arrival_day: int = 1,
                 satisfaction_init: float = SATISFACTION_INIT):
        super().__init__('single', 1, arrival_day, satisfaction_init)
        self.activities_todo = list(self.FIXED_ROUTE)

    def build_activities(self, station_queue_lengths: dict[str, int] = None) -> None:
        self.activities_todo = list(self.FIXED_ROUTE)
