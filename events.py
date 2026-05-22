"""
Event class and event-type constants for the Queuechella simulation.

Using an OOP Event (with __lt__ for the min-heap) instead of raw tuples
makes event data self-documenting and easier to debug.
"""

from __future__ import annotations
from typing import Any, Optional


# ── Event type constants ───────────────────────────────────────────────────────

class EventType:
    ARRIVE          = 'ARRIVE'
    SCAN_END        = 'SCAN_END'
    SECURITY_END    = 'SECURITY_END'
    SVC_END         = 'SVC_END'
    SHOW_START      = 'SHOW_START'
    SHOW_END        = 'SHOW_END'
    EARLY_LEAVE     = 'EARLY_LEAVE'
    DJ_LEAVE        = 'DJ_LEAVE'
    ABANDON         = 'ABANDON'
    NEXT            = 'NEXT'
    LUNCH           = 'LUNCH'
    FOOD_ORDER_END  = 'FOOD_ORDER_END'
    FOOD_PREP_END   = 'FOOD_PREP_END'
    EAT_END         = 'EAT_END'
    DAY_END         = 'DAY_END'
    ART_BREAK_END   = 'ART_BREAK_END'


# ── Global sequence counter (tie-breaker for equal-time events) ───────────────

_SEQ: int = 0


def reset_seq() -> None:
    global _SEQ
    _SEQ = 0


# ── Event class ───────────────────────────────────────────────────────────────

class Event:
    """
    A single simulation event stored in the min-heap.

    Ordering: primary by time, secondary by priority (lower = earlier),
    tertiary by sequence number to guarantee FIFO among ties.
    """

    __slots__ = ('time', 'etype', 'entity', 'data', 'priority', 'seq')

    def __init__(self,
                 time: float,
                 etype: str,
                 entity: Optional[Any] = None,
                 data: Optional[dict] = None,
                 priority: int = 5):
        global _SEQ
        _SEQ += 1
        self.time = time
        self.etype = etype
        self.entity = entity
        self.data: dict = data if data is not None else {}
        self.priority = priority
        self.seq = _SEQ

    # Heap comparison
    def __lt__(self, other: Event) -> bool:
        if self.time != other.time:
            return self.time < other.time
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.seq < other.seq

    def __repr__(self) -> str:
        eid = getattr(self.entity, 'id', None)
        return (f"Event({self.etype}, t={self.time:.2f}, "
                f"entity={eid}, data={self.data})")
