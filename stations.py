"""
Station and venue classes for the Queuechella simulation.

Three station archetypes:
  ServiceStation  – multi-server queue (entry gate, photo, charging, merch, food)
  ShowVenue       – batch-admit show venue with scheduled shows (MainStage, SideStage)
  ContinuousVenue – capacity-limited continuous venue (DJStage)
  BodyArtStation  – ServiceStation subclass with artist break logic
"""

from collections import deque


class ServiceStation:
    """Generic multi-server service station with a shared FIFO queue."""

    def __init__(self, name: str, num_servers: int):
        self.name = name
        self.num_servers = num_servers
        self.queue: deque = deque()          # waiting entities
        self._servers: list = [None] * num_servers  # entity or None

        # KPI accumulators
        self.n_served = 0
        self.n_abandoned = 0
        self.total_wait = 0.0    # sum of waiting minutes
        self.total_service = 0.0

    # ── server management ──────────────────────────────────────────────────

    def free_server(self) -> int:
        """Return index of a free server, or -1 if all busy."""
        for i, s in enumerate(self._servers):
            if s is None:
                return i
        return -1

    def has_free_server(self) -> bool:
        return self.free_server() >= 0

    def start_service(self, entity, server_idx: int):
        self._servers[server_idx] = entity
        entity.in_service_at = self.name
        entity.in_queue_at = None

    def end_service(self, entity, server_idx: int):
        self._servers[server_idx] = None
        entity.in_service_at = None
        self.n_served += 1

    # ── queue management ──────────────────────────────────────────────────

    def enqueue(self, entity):
        self.queue.append(entity)
        entity.in_queue_at = self.name

    def dequeue(self) -> object:
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

    def busy_servers(self) -> int:
        return sum(1 for s in self._servers if s is not None)

    def __repr__(self):
        return (f"{self.name}(servers={self.busy_servers()}/{self.num_servers}, "
                f"queue={self.queue_length()})")


class BodyArtStation(ServiceStation):
    """
    Two-artist station. Each artist must take a 15-minute break
    after every 10 completed drawings.
    """
    BREAK_AFTER = 10
    BREAK_DURATION = 15.0

    def __init__(self, name: str, num_servers: int):
        super().__init__(name, num_servers)
        self._drawings_done = [0] * num_servers   # counter per artist
        self._on_break_until = [0.0] * num_servers  # simulation time

    def artist_available(self, server_idx: int, clock: float) -> bool:
        return (self._servers[server_idx] is None
                and clock >= self._on_break_until[server_idx])

    def free_available_artist(self, clock: float) -> int:
        """Return index of artist who is idle AND not on break, or -1."""
        for i in range(self.num_servers):
            if self.artist_available(i, clock):
                return i
        return -1

    def end_service(self, entity, server_idx: int):
        super().end_service(entity, server_idx)
        self._drawings_done[server_idx] += 1
        if self._drawings_done[server_idx] >= self.BREAK_AFTER:
            self._drawings_done[server_idx] = 0
            # Break start time = current clock (set externally via record_break)

    def record_break(self, server_idx: int, clock: float):
        self._on_break_until[server_idx] = clock + self.BREAK_DURATION

    def next_break_end(self, server_idx: int) -> float:
        return self._on_break_until[server_idx]


class ShowVenue:
    """
    Venue for scheduled shows (MainStage=mainstream, SideStage=indie).

    Shows run back-to-back with a fixed break between them.
    Entities queue here waiting for the next show start.
    At show start, we greedily fill the venue up to capacity, maximising
    total people admitted (skip entities that would overflow capacity).
    """

    def __init__(self, name: str, capacity: int, genre: str, break_min: float):
        self.name = name
        self.capacity = capacity        # people per show
        self.genre = genre              # 'mainstream' | 'indie'
        self.break_min = break_min      # minutes between shows

        self.queue: deque = deque()     # entities waiting for next show
        self._attendees: list = []      # entities inside current show (ordered by entry)
        self._occupancy = 0             # people count inside current show

        # KPI
        self.n_shows = 0
        self.total_attendees = 0

    # ── queue management ──────────────────────────────────────────────────

    def enqueue(self, entity):
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

    # ── show mechanics ────────────────────────────────────────────────────

    def fill_show(self) -> list:
        """
        Admit entities from queue into the show, maximising people count.
        Policy: scan queue in order; admit entity if its group_size fits in
        remaining capacity; otherwise skip and continue scanning.
        Returns list of admitted entities.
        """
        remaining = self.capacity - self._occupancy
        admitted = []
        skipped = []

        while self.queue and remaining > 0:
            entity = self.queue.popleft()
            entity.in_queue_at = None
            if entity.group_size <= remaining:
                admitted.append(entity)
                remaining -= entity.group_size
            else:
                skipped.append(entity)

        # Return skipped entities to the front of the queue
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
        """Return up to 10 entities at the back (farthest from stage)."""
        return list(self._attendees[-10:])

    def remove_attendee(self, entity):
        try:
            self._attendees.remove(entity)
            self._occupancy -= entity.group_size
            entity.in_show_at = None
        except ValueError:
            pass

    def end_show(self) -> list:
        """End current show; return all remaining attendees."""
        attendees = list(self._attendees)
        for e in attendees:
            e.in_show_at = None
        self._attendees.clear()
        self._occupancy = 0
        return attendees

    def current_occupancy(self) -> int:
        return self._occupancy

    def is_show_running(self) -> bool:
        return self._occupancy > 0

    def __repr__(self):
        return (f"{self.name}(in_show={self._occupancy}/{self.capacity}, "
                f"queue={self.queue_length()})")


class ContinuousVenue:
    """
    DJ Stage: continuous music, capacity-limited.
    Entities enter whenever there is room and stay for a sampled duration.
    """

    def __init__(self, name: str, capacity: int):
        self.name = name
        self.capacity = capacity       # max people at any moment
        self.queue: deque = deque()    # entities waiting to enter
        self._occupants: dict = {}     # entity_id -> entity
        self._occupancy = 0

        # KPI
        self.total_entries = 0
        self.n_abandoned = 0
        self.total_wait = 0.0

    def enqueue(self, entity):
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

    def is_full(self) -> bool:
        return self._occupancy >= self.capacity

    def admit(self, entity):
        self._occupants[entity.id] = entity
        self._occupancy += entity.group_size
        entity.in_show_at = self.name
        entity.in_queue_at = None
        self.total_entries += entity.group_size

    def leave(self, entity):
        if entity.id in self._occupants:
            del self._occupants[entity.id]
            self._occupancy -= entity.group_size
            entity.in_show_at = None

    def try_admit_queued(self) -> list:
        """Admit waiting entities if space is available. Returns admitted list."""
        admitted = []
        while self.queue:
            e = self.queue[0]
            if self._occupancy + e.group_size <= self.capacity:
                self.queue.popleft()
                self.admit(e)
                admitted.append(e)
            else:
                break
        return admitted

    def occupancy(self) -> int:
        return self._occupancy

    def __repr__(self):
        return (f"{self.name}(occupancy={self._occupancy}/{self.capacity}, "
                f"queue={self.queue_length()})")
