"""
Entity (visitor) classes for the Queuechella festival simulation.
Three entity types: FriendsGroup, Couple, Single.
Each entity travels as a unit; group_size counts people for venue capacity.
"""

from distributions import sample_friends_group_size, u01

SATISFACTION_INIT = 5.0
SATISFACTION_MAX = 10.0
SATISFACTION_MIN = 0.0

_ENTITY_COUNTER = 0


def _next_id() -> int:
    global _ENTITY_COUNTER
    _ENTITY_COUNTER += 1
    return _ENTITY_COUNTER


def reset_entity_counter():
    global _ENTITY_COUNTER
    _ENTITY_COUNTER = 0


class Entity:
    """Base class for all festival visitors."""

    PATIENCE = 20  # minutes willing to wait in service queues

    def __init__(self, etype: str, group_size: int, arrival_day: int):
        self.id = _next_id()
        self.etype = etype           # 'friends' | 'couple' | 'single'
        self.group_size = group_size  # number of people this entity represents
        self.arrival_day = arrival_day
        self.satisfaction = SATISFACTION_INIT

        # Activity routing
        self.activities_todo: list[str] = []  # remaining activities
        self.activities_done: list[str] = []

        # State flags
        self.in_queue_at: str | None = None      # station name if queuing
        self.in_service_at: str | None = None    # station name if being served
        self.in_show_at: str | None = None       # venue name if inside show/DJ
        self.abandon_event = None                 # scheduled abandon event (can be cancelled)
        self.left_festival = False

        # Per-run statistics
        self.total_wait_min = 0.0    # total minutes spent waiting in queues
        self.total_revenue = 0.0     # money spent at festival

        # Overnight flag (resolved at end of day 1)
        self.stays_overnight = False

    def update_satisfaction(self, delta: float):
        self.satisfaction = max(SATISFACTION_MIN,
                                min(SATISFACTION_MAX, self.satisfaction + delta))

    def spend(self, amount: float):
        self.total_revenue += amount

    def next_activity(self) -> str | None:
        """Pop and return the next activity name, or None if done."""
        if not self.activities_todo:
            return None
        act = self.activities_todo.pop(0)
        self.activities_done.append(act)
        return act

    def peek_activity(self) -> str | None:
        return self.activities_todo[0] if self.activities_todo else None

    def is_busy(self) -> bool:
        return (self.in_queue_at is not None
                or self.in_service_at is not None
                or self.in_show_at is not None)

    def __repr__(self):
        return (f"{self.etype.capitalize()}#{self.id}"
                f"(n={self.group_size}, sat={self.satisfaction:.1f})")


class FriendsGroup(Entity):
    """
    3-6 friends. Arrive day 1 only, 09:00-13:00.
    Want 1 show of each type + all stations (shortest queue priority).
    70% chance to stay overnight.
    Queue patience: 15 min.
    """
    PATIENCE = 15
    ALL_SHOWS = ['MainStage', 'SideStage', 'DJStage']
    ALL_STATIONS = ['PhotoStation', 'ChargingStation', 'MerchTent', 'BodyArt']

    def __init__(self, arrival_day: int = 1):
        size = sample_friends_group_size()
        super().__init__('friends', size, arrival_day)
        self.stays_overnight = (u01() < 0.7)
        # Activities are set by build_activities(); stations reordered at runtime
        self.pending_shows = list(self.ALL_SHOWS)
        self.pending_stations = list(self.ALL_STATIONS)

    def build_activities(self, station_queue_lengths: dict[str, int] | None = None):
        """
        Build todo list: shows first (no preference order among shows),
        then stations ordered by current queue length (shortest first).
        """
        stations = list(self.ALL_STATIONS)
        if station_queue_lengths:
            stations.sort(key=lambda s: station_queue_lengths.get(s, 0))
        self.activities_todo = list(self.ALL_SHOWS) + stations


class Couple(Entity):
    """
    2-person couple. Arrive 10:00-16:00, both days.
    Alternates: show → station → show → station …
    No electronic music (DJStage excluded).
    Stays overnight on day 1 if satisfaction > 7 at end of day.
    Queue patience: 20 min.
    """
    PATIENCE = 20
    SHOWS = ['MainStage', 'SideStage']
    STATIONS = ['PhotoStation', 'ChargingStation', 'MerchTent', 'BodyArt']

    def __init__(self, arrival_day: int = 1):
        super().__init__('couple', 2, arrival_day)
        self._next_is_show = True  # alternating flag
        # Pre-generate a long alternating list; simulation stops them at festival end
        self.activities_todo = self._build_long_list(10)

    def _build_long_list(self, rounds: int) -> list[str]:
        import random as _r
        seq = []
        for _ in range(rounds):
            seq.append(_r.choice(self.SHOWS))
            seq.append(_r.choice(self.STATIONS))
        return seq

    def refresh_activities(self):
        """Called when todo list runs low."""
        import random as _r
        for _ in range(4):
            self.activities_todo.append(_r.choice(self.SHOWS))
            self.activities_todo.append(_r.choice(self.STATIONS))


class Single(Entity):
    """
    Single visitor. Arrives 09:00-16:00, one day only.
    Fixed route: MerchTent → 2×MainStage → 2×SideStage → 1×DJStage.
    Queue patience: 20 min.
    """
    PATIENCE = 20

    def __init__(self, arrival_day: int = 1):
        super().__init__('single', 1, arrival_day)
        self.activities_todo = [
            'MerchTent',
            'MainStage', 'MainStage',
            'SideStage', 'SideStage',
            'DJStage',
        ]
