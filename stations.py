"""
Station hierarchy for the Queuechella festival simulation.

Station (ABC)
├── ServiceStation    – generic multi-server FIFO queue
│   ├── BodyArtStation – adds per-artist break tracking
│   └── FoodStation    – encapsulates food-specific service logic
├── ShowVenue         – batch-admit, scheduled shows (MainStage / SideStage)
└── ContinuousVenue   – capacity-limited continuous venue (DJStage)
"""

from __future__ import annotations
import abc
from collections import deque
from typing import Optional

from distributions import (
    sample_photo_duration, sample_charging_duration, sample_battery_level,
    sample_merch_service,
    sample_bodyart_glitter, sample_bodyart_neon, sample_bodyart_henna,
    sample_food_cashier_service,
    sample_pizza_prep, sample_burger_prep, sample_asian_prep,
    sample_eating_time, u01,
)


# ── Abstract base ─────────────────────────────────────────────────────────────

class Station(abc.ABC):
    """Abstract base class for all festival stations and venues."""

    def __init__(self, name: str):
        self.name = name

    @abc.abstractmethod
    def queue_length(self) -> int: ...

    @abc.abstractmethod
    def people_in_queue(self) -> int: ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"


# ── ServiceStation ────────────────────────────────────────────────────────────

class ServiceStation(Station):
    """
    Multi-server service station with a single shared FIFO queue.
    Handles all standard service stations: EntryGate, PhotoStation,
    ChargingStation, MerchTent, and the three food stalls.
    """

    def __init__(self, name: str, num_servers: int):
        super().__init__(name)
        self.num_servers = num_servers
        self.queue: deque = deque()
        self._servers: list = [None] * num_servers  # None = idle, else = entity

        # KPI accumulators
        self.n_served:    int   = 0
        self.n_abandoned: int   = 0
        self.total_wait:  float = 0.0
        self.total_service_time: float = 0.0

    # ── Server management ─────────────────────────────────────────────────

    def free_server_index(self) -> int:
        """Return index of any idle server, or -1 if all are busy."""
        for i, s in enumerate(self._servers):
            if s is None:
                return i
        return -1

    def has_free_server(self) -> bool:
        return self.free_server_index() >= 0

    def busy_count(self) -> int:
        return sum(1 for s in self._servers if s is not None)

    def start_service(self, entity, server_idx: int) -> None:
        self._servers[server_idx] = entity
        entity.in_service_at = self.name
        entity.in_queue_at   = None

    def end_service(self, entity, server_idx: int) -> None:
        self._servers[server_idx] = None
        entity.in_service_at = None
        self.n_served += 1

    # ── Queue management ──────────────────────────────────────────────────

    def enqueue(self, entity) -> None:
        self.queue.append(entity)
        entity.in_queue_at = self.name

    def dequeue(self):
        """Pop and return the front entity, clearing its in_queue_at flag."""
        if not self.queue:
            return None
        e = self.queue.popleft()
        e.in_queue_at = None
        return e

    def remove_from_queue(self, entity) -> bool:
        try:
            self.queue.remove(entity)
            entity.in_queue_at = None
            return True
        except ValueError:
            return False

    def queue_length(self) -> int:
        return len(self.queue)

    def people_in_queue(self) -> int:
        return sum(e.group_size for e in self.queue)

    # ── Service-time sampling (overridable) ──────────────────────────────

    def sample_service_duration(self, entity) -> float:
        """Return service duration in minutes. Subclasses override for specialised logic."""
        return 1.0

    def __repr__(self) -> str:
        return (f"{self.name}(servers={self.busy_count()}/{self.num_servers}, "
                f"queue={self.queue_length()})")


# ── BodyArtStation ────────────────────────────────────────────────────────────

class BodyArtStation(ServiceStation):
    """
    Two-artist body-art station.
    Each artist takes a 15-minute break after every 10 completed drawings.
    Art type is chosen randomly per entity; service time depends on art type.
    """

    BREAK_AFTER:    int   = 10
    BREAK_DURATION: float = 15.0

    # Probability distribution over art types
    ART_TYPES = [
        ('glitter', 0.30, 0.70, 0.8,  sample_bodyart_glitter),
        ('neon',    0.30, 0.60, 1.2,  sample_bodyart_neon),
        ('henna',   0.40, 0.80, 0.7,  sample_bodyart_henna),
    ]

    def __init__(self, name: str, num_servers: int):
        super().__init__(name, num_servers)
        self._drawings_done    = [0]   * num_servers   # counter per artist
        self._on_break_until   = [0.0] * num_servers   # sim-clock time

    # ── Artist availability ────────────────────────────────────────────────

    def artist_available(self, server_idx: int, clock: float) -> bool:
        return (self._servers[server_idx] is None
                and clock >= self._on_break_until[server_idx])

    def free_available_artist(self, clock: float) -> int:
        """Return index of an idle, not-on-break artist, or -1."""
        for i in range(self.num_servers):
            if self.artist_available(i, clock):
                return i
        return -1

    def end_service(self, entity, server_idx: int) -> None:
        super().end_service(entity, server_idx)
        self._drawings_done[server_idx] += 1

    def needs_break(self, server_idx: int) -> bool:
        return self._drawings_done[server_idx] >= self.BREAK_AFTER

    def start_break(self, server_idx: int, clock: float) -> None:
        self._drawings_done[server_idx] = 0
        self._on_break_until[server_idx] = clock + self.BREAK_DURATION

    def break_ends_at(self, server_idx: int) -> float:
        return self._on_break_until[server_idx]

    # ── Art-type sampling ─────────────────────────────────────────────────

    @staticmethod
    def sample_art_type() -> tuple[str, float, float, float]:
        """
        Returns (art_type, service_duration, satisfied_prob, sat_delta).
        Art type probabilities: glitter 0.30, neon 0.30, henna 0.40.
        """
        r = u01()
        cumulative = 0.0
        for name, weight, sat_prob, sat_delta, sampler in BodyArtStation.ART_TYPES:
            cumulative += weight
            if r < cumulative:
                return name, sampler(), sat_prob, sat_delta
        # Fallback (floating-point edge case)
        name, weight, sat_prob, sat_delta, sampler = BodyArtStation.ART_TYPES[-1]
        return name, sampler(), sat_prob, sat_delta

    def apply_outcome(self, entity, sat_prob: float, sat_delta: float) -> None:
        """Update entity satisfaction based on body-art result."""
        if u01() < sat_prob:
            entity.update_satisfaction(sat_delta)
        # Spec does not specify a penalty for unsatisfied body-art customers


# ── FoodStation ───────────────────────────────────────────────────────────────

class FoodStation(ServiceStation):
    """
    One of the three food stalls (Pizza / Burger / Asian).
    Encapsulates food-specific service time sampling, pricing, and prep times.
    Cashier service is shared across all types (Normal(5, 1.5)).
    """

    # (stall_type, prep_sampler, price_per_person, price_per_3_for_pizza)
    STALL_TYPES = {
        'pizza':  (sample_pizza_prep,   40.0,  100.0),
        'burger': (sample_burger_prep, 100.0,   None),
        'asian':  (sample_asian_prep,   65.0,   None),
    }

    def __init__(self, stall_type: str):
        assert stall_type in self.STALL_TYPES, f"Unknown stall type: {stall_type}"
        super().__init__(f'Food_{stall_type.capitalize()}', num_servers=1)
        self.stall_type = stall_type
        self._prep_sampler, self._price_per_person, self._family_price = (
            self.STALL_TYPES[stall_type]
        )

    def sample_service_duration(self, entity) -> float:
        """Cashier order + payment (Normal(5, 1.5))."""
        return sample_food_cashier_service()

    def sample_prep_time(self) -> float:
        return self._prep_sampler()

    def calculate_cost(self, entity) -> float:
        """
        Pizza: Singles pay 40 ILS (individual); groups pay 100 ILS per 3 people.
        Burger/Asian: 100 / 65 ILS per person.
        """
        if self.stall_type == 'pizza':
            if entity.etype == 'single':
                return 40.0
            import math
            return math.ceil(entity.group_size / 3) * self._family_price
        return self._price_per_person * entity.group_size

    @staticmethod
    def sample_eating_time() -> float:
        return sample_eating_time()


# ── ShowVenue ─────────────────────────────────────────────────────────────────

class ShowVenue(Station):
    """
    Venue for scheduled shows (MainStage = mainstream, SideStage = indie).

    Policy: at each show start, fill the venue to maximise total people admitted.
    Skip entities that would overflow capacity and admit smaller ones behind them.
    The last 10 entities to enter (farthest from stage) may leave early at MainStage.
    """

    def __init__(self, name: str, capacity: int, genre: str, break_min: float):
        super().__init__(name)
        self.capacity:  int   = capacity   # max people per show
        self.genre:     str   = genre      # 'mainstream' | 'indie'
        self.break_min: float = break_min  # minutes between shows

        self.queue: deque = deque()         # entities waiting for next show
        self._attendees: list  = []         # entities inside current show (entry order)
        self._occupancy: int   = 0          # people count inside show

        # KPI
        self.n_shows:         int  = 0
        self.total_attendees: int  = 0

    # ── Queue management ──────────────────────────────────────────────────

    def enqueue(self, entity) -> None:
        self.queue.append(entity)
        entity.in_queue_at = self.name

    def remove_from_queue(self, entity) -> bool:
        try:
            self.queue.remove(entity)
            entity.in_queue_at = None
            return True
        except ValueError:
            return False

    def queue_length(self) -> int:
        return len(self.queue)

    def people_in_queue(self) -> int:
        return sum(e.group_size for e in self.queue)

    # ── Show mechanics ────────────────────────────────────────────────────

    def fill_show(self) -> list:
        """
        Admit entities from queue to maximise total people admitted.
        Entities that do not fit are skipped (returned to front of queue).
        Returns list of admitted entities in entry order.
        """
        remaining = self.capacity - self._occupancy
        admitted  = []
        skipped   = []

        while self.queue and remaining > 0:
            entity = self.queue.popleft()
            entity.in_queue_at = None
            if entity.group_size <= remaining:
                admitted.append(entity)
                remaining -= entity.group_size
            else:
                skipped.append(entity)

        # Return skipped entities to queue front (preserve order)
        for e in reversed(skipped):
            self.queue.appendleft(e)
            e.in_queue_at = self.name

        for e in admitted:
            self._attendees.append(e)
            self._occupancy += e.group_size
            e.in_show_at = self.name

        self.n_shows += 1
        self.total_attendees += self._occupancy
        return admitted

    def back_ten_entities(self) -> list:
        """Return up to 10 entities that entered last (farthest from stage)."""
        return list(self._attendees[-10:])

    def remove_attendee(self, entity) -> None:
        try:
            self._attendees.remove(entity)
            self._occupancy -= entity.group_size
            entity.in_show_at = None
        except ValueError:
            pass

    def end_show(self) -> list:
        """End current show and return all remaining attendees."""
        attendees = list(self._attendees)
        for e in attendees:
            e.in_show_at = None
        self._attendees.clear()
        self._occupancy = 0
        return attendees

    def current_occupancy(self) -> int:
        return self._occupancy

    def __repr__(self) -> str:
        return (f"{self.name}(in_show={self._occupancy}/{self.capacity}, "
                f"queue={self.queue_length()})")


# ── ContinuousVenue ───────────────────────────────────────────────────────────

class ContinuousVenue(Station):
    """
    DJ Stage: music plays continuously; entities enter whenever space is
    available and leave after a personally sampled stay duration.
    Capacity enforced at every moment (not per-show).
    """

    def __init__(self, name: str, capacity: int):
        super().__init__(name)
        self.capacity:    int  = capacity
        self.queue:       deque = deque()
        self._occupants:  dict  = {}   # entity.id → entity
        self._occupancy:  int   = 0

        # KPI
        self.total_entries: int   = 0
        self.n_abandoned:   int   = 0
        self.total_wait:    float = 0.0

    def enqueue(self, entity) -> None:
        self.queue.append(entity)
        entity.in_queue_at = self.name

    def remove_from_queue(self, entity) -> bool:
        try:
            self.queue.remove(entity)
            entity.in_queue_at = None
            return True
        except ValueError:
            return False

    def queue_length(self) -> int:
        return len(self.queue)

    def people_in_queue(self) -> int:
        return sum(e.group_size for e in self.queue)

    def is_full(self) -> bool:
        return self._occupancy >= self.capacity

    def can_admit(self, entity) -> bool:
        return self._occupancy + entity.group_size <= self.capacity

    def admit(self, entity) -> None:
        self._occupants[entity.id] = entity
        self._occupancy += entity.group_size
        entity.in_show_at  = self.name
        entity.in_queue_at = None
        self.total_entries += entity.group_size

    def leave(self, entity) -> None:
        if entity.id in self._occupants:
            del self._occupants[entity.id]
            self._occupancy -= entity.group_size
            entity.in_show_at = None

    def try_admit_queued(self) -> list:
        """Admit all waiting entities that fit. Returns list of newly admitted."""
        admitted = []
        while self.queue:
            e = self.queue[0]
            if self.can_admit(e):
                self.queue.popleft()
                self.admit(e)
                admitted.append(e)
            else:
                break
        return admitted

    def occupancy(self) -> int:
        return self._occupancy

    def __repr__(self) -> str:
        return (f"{self.name}(occupancy={self._occupancy}/{self.capacity}, "
                f"queue={self.queue_length()})")
