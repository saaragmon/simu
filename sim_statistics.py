"""
SimStatistics – collects and summarises KPIs from one simulation replication.
Kept separate from FestivalSimulation so it can be swapped / extended easily.
"""

import math
import statistics as _stats
from collections import defaultdict
from typing import Dict, List


class SimStatistics:
    """All measurements collected during a single festival simulation run."""

    def __init__(self):
        # Per-entity departure records
        self.satisfaction_scores: List[float] = []
        self.revenue_per_entity: List[float] = []

        # Per-station wait times (minutes)
        self.wait_times: Dict[str, List[float]] = defaultdict(list)

        # Queue-length snapshots (sampled at each service-start)
        self.queue_snapshots: Dict[str, List[int]] = defaultdict(list)

        # Abandonment counts per station
        self.abandon_counts: Dict[str, int] = defaultdict(int)

        # Revenue breakdown
        self.ticket_revenue: float = 0.0
        self.lodging_revenue: float = 0.0
        self.merch_revenue: float = 0.0
        self.food_revenue: float = 0.0
        self.photo_revenue: float = 0.0

        # Entity / people counts
        self.entity_counts: Dict[str, int] = defaultdict(int)  # by type
        self.total_people: int = 0
        self.overnight_count: int = 0

        # Show statistics
        self.show_counts: Dict[str, int] = defaultdict(int)
        self.show_occupancy: Dict[str, List[int]] = defaultdict(list)

    # ── Recording helpers ─────────────────────────────────────────────────

    def record_departure(self, entity) -> None:
        self.satisfaction_scores.append(entity.satisfaction)
        self.revenue_per_entity.append(entity.total_revenue)

    def record_wait(self, station_name: str, wait: float) -> None:
        self.wait_times[station_name].append(wait)

    def record_queue_snapshot(self, station_name: str, length: int) -> None:
        self.queue_snapshots[station_name].append(length)

    def record_abandon(self, station_name: str) -> None:
        self.abandon_counts[station_name] += 1

    def record_show(self, venue_name: str, occupancy: int) -> None:
        self.show_counts[venue_name] += 1
        self.show_occupancy[venue_name].append(occupancy)

    def add_revenue(self, category: str, amount: float) -> None:
        if category == 'ticket':
            self.ticket_revenue += amount
        elif category == 'lodging':
            self.lodging_revenue += amount
        elif category == 'merch':
            self.merch_revenue += amount
        elif category == 'food':
            self.food_revenue += amount
        elif category == 'photo':
            self.photo_revenue += amount

    # ── Summary ───────────────────────────────────────────────────────────

    @property
    def total_revenue(self) -> float:
        return (self.ticket_revenue + self.lodging_revenue
                + self.merch_revenue + self.food_revenue + self.photo_revenue)

    @property
    def avg_satisfaction(self) -> float:
        return _stats.mean(self.satisfaction_scores) if self.satisfaction_scores else 0.0

    @property
    def std_satisfaction(self) -> float:
        return (_stats.stdev(self.satisfaction_scores)
                if len(self.satisfaction_scores) > 1 else 0.0)

    def avg_wait(self, station_name: str) -> float:
        w = self.wait_times.get(station_name, [])
        return _stats.mean(w) if w else 0.0

    def max_wait(self, station_name: str) -> float:
        w = self.wait_times.get(station_name, [])
        return max(w) if w else 0.0

    def avg_queue_length(self, station_name: str) -> float:
        q = self.queue_snapshots.get(station_name, [])
        return _stats.mean(q) if q else 0.0

    def summary(self) -> dict:
        """Return a flat dict of all KPIs — used by main.py for comparisons."""
        result = {
            'avg_satisfaction': self.avg_satisfaction,
            'std_satisfaction': self.std_satisfaction,
            'total_revenue': self.total_revenue,
            'ticket_revenue': self.ticket_revenue,
            'lodging_revenue': self.lodging_revenue,
            'merch_revenue': self.merch_revenue,
            'food_revenue': self.food_revenue,
            'photo_revenue': self.photo_revenue,
            'n_entities': sum(self.entity_counts.values()),
            'total_people': self.total_people,
            'overnight_count': self.overnight_count,
            'satisfaction_scores': self.satisfaction_scores,
        }
        for sname, waits in self.wait_times.items():
            if waits:
                result[f'avg_wait_{sname}'] = _stats.mean(waits)
                result[f'max_wait_{sname}'] = max(waits)
        for sname, count in self.abandon_counts.items():
            result[f'abandon_{sname}'] = count
        for sname, counts in self.show_counts.items():
            result[f'shows_{sname}'] = counts
        return result
