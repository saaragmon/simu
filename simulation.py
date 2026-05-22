"""
FestivalSimulation – event-driven simulation engine for Queuechella.

Time unit : minutes  (clock=0 ≡ 09:00 day 1)
Day 1     : clock in [0,   660)
Day 2     : clock in [660, 1320)

All festival logic is driven by an Event min-heap.
"""

from __future__ import annotations

import heapq
import math
import random
from typing import Optional

from config    import SimConfig
from sim_statistics import SimStatistics
from events    import Event, EventType, reset_seq
from entities  import (Entity, FriendsGroup, Couple, Single,
                       reset_entity_counter, SATISFACTION_INIT)
from stations  import (ServiceStation, BodyArtStation,
                       FoodStation, ShowVenue, ContinuousVenue)
from distributions import (
    sample_friends_arrival_interval, sample_couple_interval,
    sample_single_interval,
    sample_ticket_scan, sample_security_check,
    sample_mainstage_duration, sample_sidestage_duration,
    sample_photo_duration, sample_battery_level, sample_charging_duration,
    sample_merch_service, sample_dj_stay, u01,
)

# ── Time constants (minutes from 09:00 day 1) ────────────────────────────────
DAY_LEN       = 660   # 09:00 → 20:00
FESTIVAL_END  = 1320  # end of day 2

FRIENDS_ARRIVE_END  = 240   # 13:00
COUPLE_ARRIVE_START = 60    # 10:00
COUPLE_ARRIVE_END   = 420   # 16:00
SINGLE_ARRIVE_END   = 420   # 16:00

LUNCH_START = 240   # 13:00
LUNCH_END   = 360   # 15:00


class FestivalSimulation:
    """
    Discrete-event simulation of the Queuechella music festival.

    Responsibilities:
      - Maintain the event heap and advance the simulation clock.
      - Own all station instances and route entities between them.
      - Delegate statistics recording to SimStatistics.
      - Apply all spec rules: entry, shows, service queues, patience,
        satisfaction scoring, overnight logic, food stalls.
    """

    def __init__(self, config: Optional[SimConfig] = None):
        self.cfg   = config if config is not None else SimConfig()
        self._heap: list = []
        self.clock: float = 0.0

        # ── Stations ──────────────────────────────────────────────────────
        self.entry    = ServiceStation('EntryGate',      self.cfg.entry_servers)
        self.photo    = ServiceStation('PhotoStation',   self.cfg.photo_servers)
        self.charging = ServiceStation('ChargingStation',self.cfg.charging_servers)
        self.merch    = ServiceStation('MerchTent',      self.cfg.merch_servers)
        self.bodyart  = BodyArtStation('BodyArt',        self.cfg.body_servers)

        self.mainstage = ShowVenue('MainStage', self.cfg.mainstage_cap, 'mainstream', 10.0)
        self.sidestage = ShowVenue('SideStage', self.cfg.sidestage_cap, 'indie',      5.0)
        self.djstage   = ContinuousVenue('DJStage', self.cfg.djstage_cap)

        self.food_pizza  = FoodStation('pizza')
        self.food_burger = FoodStation('burger')
        self.food_asian  = FoodStation('asian')

        # Unified station lookup by activity name
        self._stations: dict[str, object] = {
            'EntryGate':      self.entry,
            'PhotoStation':   self.photo,
            'ChargingStation':self.charging,
            'MerchTent':      self.merch,
            'BodyArt':        self.bodyart,
            'MainStage':      self.mainstage,
            'SideStage':      self.sidestage,
            'DJStage':        self.djstage,
            'Food_Pizza':     self.food_pizza,
            'Food_Burger':    self.food_burger,
            'Food_Asian':     self.food_asian,
        }

        # ── Statistics ────────────────────────────────────────────────────
        self.stats = SimStatistics()

        # ── Show schedules ────────────────────────────────────────────────
        self._ms_shows: list[tuple[float, float]] = []   # (start, end)
        self._ss_shows: list[tuple[float, float]] = []

        # ── Active entity tracking (for overnight / day-end logic) ────────
        self._active_entities: set[int] = set()   # entity.id

    # ════════════════════════════════════════════════════════════════════════
    #  Event scheduling helpers
    # ════════════════════════════════════════════════════════════════════════

    def _push(self, time: float, etype: str,
              entity: Optional[Entity] = None,
              data: Optional[dict] = None,
              priority: int = 5) -> Event:
        evt = Event(time, etype, entity, data, priority)
        heapq.heappush(self._heap, evt)
        return evt

    def _push_delay(self, delay: float, etype: str,
                    entity: Optional[Entity] = None,
                    data: Optional[dict] = None,
                    priority: int = 5) -> Event:
        return self._push(self.clock + delay, etype, entity, data, priority)

    # ════════════════════════════════════════════════════════════════════════
    #  Initialisation
    # ════════════════════════════════════════════════════════════════════════

    def _build_show_schedule(self) -> None:
        """Pre-generate all show start/end times for both festival days."""
        for day in [1, 2]:
            offset = (day - 1) * DAY_LEN

            t = float(offset)
            while True:
                dur = sample_mainstage_duration()
                if t + dur > offset + DAY_LEN:
                    break
                self._ms_shows.append((t, t + dur))
                t += dur + 10.0

            t = float(offset)
            while True:
                dur = sample_sidestage_duration()
                if t + dur > offset + DAY_LEN:
                    break
                self._ss_shows.append((t, t + dur))
                t += dur + 5.0

    def _schedule_shows(self) -> None:
        for start, end in self._ms_shows:
            self._push(start, EventType.SHOW_START, priority=0,
                       data={'venue': 'MainStage', 'end': end})
        for start, end in self._ss_shows:
            self._push(start, EventType.SHOW_START, priority=0,
                       data={'venue': 'SideStage', 'end': end})

    def _schedule_arrivals(self) -> None:
        m = self.cfg.arrival_multiplier

        # FriendsGroup – day 1, 09:00–13:00
        t = 0.0
        while True:
            t += sample_friends_arrival_interval() / m
            if t >= FRIENDS_ARRIVE_END:
                break
            self._push(t, EventType.ARRIVE, data={'etype': 'friends', 'day': 1})

        # Couple – both days, 10:00–16:00
        for day in [1, 2]:
            off = (day - 1) * DAY_LEN
            t = off + COUPLE_ARRIVE_START
            while True:
                t += sample_couple_interval() / m
                if t >= off + COUPLE_ARRIVE_END:
                    break
                self._push(t, EventType.ARRIVE, data={'etype': 'couple', 'day': day})

        # Single – both days, 09:00–16:00
        for day in [1, 2]:
            off = (day - 1) * DAY_LEN
            t = float(off)
            while True:
                t += sample_single_interval() / m
                if t >= off + SINGLE_ARRIVE_END:
                    break
                self._push(t, EventType.ARRIVE, data={'etype': 'single', 'day': day})

        # Day-boundary markers
        self._push(DAY_LEN,      EventType.DAY_END, priority=0, data={'day': 1})
        self._push(FESTIVAL_END, EventType.DAY_END, priority=0, data={'day': 2})

    # ════════════════════════════════════════════════════════════════════════
    #  Main simulation loop
    # ════════════════════════════════════════════════════════════════════════

    def run(self) -> SimStatistics:
        reset_seq()
        reset_entity_counter()

        self._build_show_schedule()
        self._schedule_shows()
        self._schedule_arrivals()

        while self._heap:
            evt = heapq.heappop(self._heap)
            if evt.time > FESTIVAL_END + 180:   # 3-hour safety margin after close
                break
            self.clock = evt.time
            self._dispatch(evt)

        return self.stats

    def _dispatch(self, evt: Event) -> None:
        h = self._handlers.get(evt.etype)
        if h:
            h(evt)

    @property
    def _handlers(self) -> dict:
        return {
            EventType.ARRIVE:         self._on_arrive,
            EventType.SCAN_END:       self._on_scan_end,
            EventType.SECURITY_END:   self._on_security_end,
            EventType.SVC_END:        self._on_service_end,
            EventType.SHOW_START:     self._on_show_start,
            EventType.SHOW_END:       self._on_show_end,
            EventType.EARLY_LEAVE:    self._on_early_leave,
            EventType.DJ_LEAVE:       self._on_dj_leave,
            EventType.ABANDON:        self._on_abandon,
            EventType.NEXT:           self._on_next_activity,
            EventType.LUNCH:          self._on_lunch,
            EventType.FOOD_ORDER_END: self._on_food_order_end,
            EventType.FOOD_PREP_END:  self._on_food_prep_end,
            EventType.EAT_END:        self._on_eat_end,
            EventType.DAY_END:        self._on_day_end,
            EventType.ART_BREAK_END:  self._on_art_break_end,
        }

    # ════════════════════════════════════════════════════════════════════════
    #  Entity arrival
    # ════════════════════════════════════════════════════════════════════════

    def _on_arrive(self, evt: Event) -> None:
        etype = evt.data['etype']
        day   = evt.data['day']
        sat0  = self.cfg.satisfaction_init

        if etype == 'friends':
            entity = FriendsGroup(arrival_day=day, satisfaction_init=sat0)
            # Ticket revenue: combo if staying overnight, else standard
            if entity.stays_overnight:
                entity.spend(700.0)
                self.stats.add_revenue('ticket',  500.0)
                self.stats.add_revenue('lodging', 200.0)   # 700-500
                self.stats.overnight_count += 1
            else:
                entity.spend(500.0)
                self.stats.add_revenue('ticket', 500.0)

        elif etype == 'couple':
            entity = Couple(arrival_day=day, satisfaction_init=sat0)
            entity.spend(500.0)
            self.stats.add_revenue('ticket', 500.0)

        else:
            entity = Single(arrival_day=day, satisfaction_init=sat0)
            entity.spend(500.0)
            self.stats.add_revenue('ticket', 500.0)

        self.stats.entity_counts[etype] += 1
        self.stats.total_people += entity.group_size
        self._active_entities.add(entity.id)
        self._join_entry(entity)

    # ════════════════════════════════════════════════════════════════════════
    #  Entry gate (2-phase: ticket scan → security check)
    # ════════════════════════════════════════════════════════════════════════

    def _join_entry(self, entity: Entity) -> None:
        st = self.entry
        if st.has_free_server():
            idx = st.free_server_index()
            st.start_service(entity, idx)
            entity._queue_join_time = self.clock
            self._push_delay(sample_ticket_scan(), EventType.SCAN_END,
                             entity=entity, data={'server': idx})
        else:
            st.enqueue(entity)
            entity._queue_join_time = self.clock

    def _on_scan_end(self, evt: Event) -> None:
        entity = evt.entity
        idx    = evt.data['server']
        # Same server continues with security check
        self._push_delay(sample_security_check(), EventType.SECURITY_END,
                         entity=entity, data={'server': idx})

    def _on_security_end(self, evt: Event) -> None:
        entity = evt.entity
        idx    = evt.data['server']

        wait = self.clock - entity._queue_join_time
        entity.total_wait_min += wait
        self.stats.record_wait('EntryGate', wait)
        self.entry.end_service(entity, idx)

        # Serve next entity waiting at entry
        nxt = self.entry.dequeue()
        if nxt is not None:
            w = self.clock - nxt._queue_join_time
            nxt.total_wait_min += w
            self.stats.record_wait('EntryGate', w)
            self.entry.start_service(nxt, idx)
            nxt._queue_join_time = self.clock
            self._push_delay(sample_ticket_scan(), EventType.SCAN_END,
                             entity=nxt, data={'server': idx})

        # Entity enters the festival
        self._build_entity_activities(entity)
        self._push_delay(0.0, EventType.NEXT, entity=entity)

    def _build_entity_activities(self, entity: Entity) -> None:
        ql = {s: self._stations[s].queue_length()
              for s in FriendsGroup.ALL_STATIONS
              if s in self._stations}
        entity.build_activities(ql)

    # ════════════════════════════════════════════════════════════════════════
    #  Activity dispatcher
    # ════════════════════════════════════════════════════════════════════════

    def _on_next_activity(self, evt: Event) -> None:
        entity = evt.entity
        if entity.left_festival:
            return

        # Overnight gate: if day 1 ended and entity is not allowed overnight → leave
        if (self.clock >= DAY_LEN
                and entity.id not in self._overnight_allowed
                and entity.arrival_day == 1):
            self._entity_leaves(entity)
            return

        # Couple: refresh activity list if running low
        if isinstance(entity, Couple):
            entity.refresh_if_low()

        act = entity.next_activity()
        if act is None:
            self._entity_leaves(entity)
            return

        # Lunch window check (before any non-lunch activity)
        if (LUNCH_START <= self.clock <= LUNCH_END
                and not getattr(entity, '_had_lunch', False)):
            if u01() < self.cfg.lunch_prob:
                entity._had_lunch = True
                entity.activities_todo.insert(0, act)   # put current act back
                self._push_delay(0.0, EventType.LUNCH, entity=entity)
                return

        self._route_to(entity, act)

    def _route_to(self, entity: Entity, act: str) -> None:
        if   act == 'MainStage':      self._join_show(entity, self.mainstage)
        elif act == 'SideStage':      self._join_show(entity, self.sidestage)
        elif act == 'DJStage':        self._join_dj(entity)
        elif act == 'PhotoStation':   self._join_service(entity, self.photo,    'photo')
        elif act == 'ChargingStation':self._join_service(entity, self.charging, 'charging')
        elif act == 'MerchTent':      self._join_service(entity, self.merch,    'merch')
        elif act == 'BodyArt':        self._join_bodyart(entity)
        else:                         self._push_delay(0.0, EventType.NEXT, entity=entity)

    # ════════════════════════════════════════════════════════════════════════
    #  Generic service stations (photo, charging, merch)
    # ════════════════════════════════════════════════════════════════════════

    def _join_service(self, entity: Entity, station: ServiceStation,
                      stype: str) -> None:
        self.stats.record_queue_snapshot(station.name, station.queue_length())
        if station.has_free_server():
            idx = station.free_server_index()
            station.start_service(entity, idx)
            entity._queue_join_time = self.clock
            dur = self._sample_service(stype, entity)
            self._push_delay(dur, EventType.SVC_END, entity=entity,
                             data={'station': station.name, 'server': idx,
                                   'stype': stype})
        else:
            station.enqueue(entity)
            entity._queue_join_time = self.clock
            self._push_delay(entity.PATIENCE, EventType.ABANDON, entity=entity,
                             data={'station': station.name})

    def _sample_service(self, stype: str, entity: Entity) -> float:
        if stype == 'photo':
            return sample_photo_duration()
        if stype == 'charging':
            b = sample_battery_level()
            entity._battery = b
            return sample_charging_duration(b)
        if stype == 'merch':
            return sample_merch_service()
        return 1.0

    def _on_service_end(self, evt: Event) -> None:
        entity = evt.entity
        sname  = evt.data['station']
        idx    = evt.data['server']
        stype  = evt.data.get('stype', '')

        # BodyArt has its own handler (break logic, outcome)
        if stype == 'bodyart':
            self._on_bodyart_service_end(entity, idx)
            return

        station = self._stations[sname]
        wait = self.clock - entity._queue_join_time
        entity.total_wait_min += wait
        self.stats.record_wait(sname, wait)
        station.end_service(entity, idx)

        # Station-specific outcome
        if stype == 'photo':
            self._apply_photo_outcome(entity)
        elif stype == 'merch':
            self._apply_merch_outcome(entity)
        # charging: no satisfaction effect per spec

        # Serve next entity in queue
        self._advance_queue(station, idx, stype)
        self._push_delay(0.0, EventType.NEXT, entity=entity)

    def _advance_queue(self, station: ServiceStation, idx: int,
                       stype: str) -> None:
        """Start service for the next waiting entity, if any."""
        nxt = station.dequeue()
        if nxt is None:
            return
        nxt.abandon_event = None   # cancel any pending abandon
        w = self.clock - nxt._queue_join_time
        nxt.total_wait_min += w
        self.stats.record_wait(station.name, w)
        station.start_service(nxt, idx)
        nxt._queue_join_time = self.clock
        dur = self._sample_service(stype, nxt)
        self._push_delay(dur, EventType.SVC_END, entity=nxt,
                         data={'station': station.name, 'server': idx,
                               'stype': stype})

    def _on_abandon(self, evt: Event) -> None:
        entity = evt.entity
        sname  = evt.data['station']

        # Stale events: entity already served or gone
        if entity.in_queue_at != sname:
            return

        station = self._stations[sname]
        station.remove_from_queue(entity)
        station.n_abandoned += 1
        self.stats.record_abandon(sname)

        penalty = {'friends': 2.0, 'couple': 1.5, 'single': 1.0}
        entity.update_satisfaction(-penalty.get(entity.etype, 1.0))
        self._push_delay(0.0, EventType.NEXT, entity=entity)

    # ════════════════════════════════════════════════════════════════════════
    #  BodyArt station (with break logic)
    # ════════════════════════════════════════════════════════════════════════

    def _join_bodyart(self, entity: Entity) -> None:
        station = self.bodyart
        self.stats.record_queue_snapshot('BodyArt', station.queue_length())
        idx = station.free_available_artist(self.clock)
        if idx >= 0:
            station.start_service(entity, idx)
            entity._queue_join_time = self.clock
            art, dur, sat_prob, sat_delta = BodyArtStation.sample_art_type()
            entity._art_meta = (sat_prob, sat_delta)
            self._push_delay(dur, EventType.SVC_END, entity=entity,
                             data={'station': 'BodyArt', 'server': idx,
                                   'stype': 'bodyart'})
        else:
            station.enqueue(entity)
            entity._queue_join_time = self.clock
            self._push_delay(entity.PATIENCE, EventType.ABANDON, entity=entity,
                             data={'station': 'BodyArt'})

    def _on_bodyart_service_end(self, entity: Entity, idx: int) -> None:
        """Handle SVC_END for BodyArt: apply outcome, check for artist break."""
        station = self.bodyart
        wait = self.clock - entity._queue_join_time
        entity.total_wait_min += wait
        self.stats.record_wait('BodyArt', wait)
        station.end_service(entity, idx)

        # Apply satisfaction outcome
        sat_prob, sat_delta = getattr(entity, '_art_meta', (0.7, 0.8))
        station.apply_outcome(entity, sat_prob, sat_delta)

        # Check if this artist needs a break
        if station.needs_break(idx):
            station.start_break(idx, self.clock)
            self._push(station.break_ends_at(idx), EventType.ART_BREAK_END,
                       priority=0, data={'server': idx})
        else:
            self._serve_next_bodyart(idx)

        self._push_delay(0.0, EventType.NEXT, entity=entity)

    def _on_art_break_end(self, evt: Event) -> None:
        self._serve_next_bodyart(evt.data['server'])

    def _serve_next_bodyart(self, idx: int) -> None:
        station = self.bodyart
        if not station.queue:
            return
        nxt = station.dequeue()
        nxt.abandon_event = None
        w = self.clock - nxt._queue_join_time
        nxt.total_wait_min += w
        self.stats.record_wait('BodyArt', w)
        station.start_service(nxt, idx)
        nxt._queue_join_time = self.clock
        art, dur, sat_prob, sat_delta = BodyArtStation.sample_art_type()
        nxt._art_meta = (sat_prob, sat_delta)
        self._push_delay(dur, EventType.SVC_END, entity=nxt,
                         data={'station': 'BodyArt', 'server': idx,
                               'stype': 'bodyart'})

    # ════════════════════════════════════════════════════════════════════════
    #  Show venues (MainStage / SideStage)
    # ════════════════════════════════════════════════════════════════════════

    def _join_show(self, entity: Entity, venue: ShowVenue) -> None:
        """Entity joins the show queue; it will be admitted at the next SHOW_START."""
        venue.enqueue(entity)
        # No patience timer for shows — entities wait as long as needed

    def _on_show_start(self, evt: Event) -> None:
        vname = evt.data['venue']
        end   = evt.data['end']
        venue = self.mainstage if vname == 'MainStage' else self.sidestage

        admitted = venue.fill_show()
        self.stats.record_show(vname, venue.current_occupancy())

        # Schedule show end
        self._push(end, EventType.SHOW_END, priority=0,
                   data={'venue': vname})

        # MainStage: back-10 entities may leave early at t+15 min
        if vname == 'MainStage':
            for e in venue.back_ten_entities():
                self._push(self.clock + 15.0, EventType.EARLY_LEAVE,
                           entity=e, data={'venue': vname, 'show_end': end})

    def _on_show_end(self, evt: Event) -> None:
        vname = evt.data['venue']
        venue = self.mainstage if vname == 'MainStage' else self.sidestage
        attendees = venue.end_show()
        for e in attendees:
            self._apply_show_outcome(e, vname)
            self._push_delay(0.0, EventType.NEXT, entity=e)

    def _on_early_leave(self, evt: Event) -> None:
        entity = evt.entity
        vname  = evt.data['venue']
        if entity.in_show_at != vname:
            return   # already left or show ended
        if u01() < 0.5:
            venue = self.mainstage if vname == 'MainStage' else self.sidestage
            venue.remove_attendee(entity)
            self._apply_show_outcome(entity, vname)
            self._push_delay(0.0, EventType.NEXT, entity=entity)

    def _apply_show_outcome(self, entity: Entity, vname: str) -> None:
        """Update satisfaction after show experience (spec §satisfaction)."""
        genre_map = {
            'MainStage': self.cfg.mainstage_genre_val,
            'SideStage': self.cfg.sidestage_genre_val,
            'DJStage':   self.cfg.djstage_genre_val,
        }
        G = genre_map.get(vname, 1)
        T = (self.clock % DAY_LEN) / 60.0 + 9.0   # end-hour of show (9–20)
        if u01() < 0.5:
            score = ((G - 1) / 2.0) + ((T - 1) / 19.0)
            entity.update_satisfaction(score)
        else:
            entity.update_satisfaction(-1.0)

    # ════════════════════════════════════════════════════════════════════════
    #  DJ Stage
    # ════════════════════════════════════════════════════════════════════════

    def _join_dj(self, entity: Entity) -> None:
        dj = self.djstage
        self.stats.record_queue_snapshot('DJStage', dj.queue_length())
        if dj.can_admit(entity):
            dj.admit(entity)
            self._push_delay(sample_dj_stay(), EventType.DJ_LEAVE, entity=entity)
        else:
            dj.enqueue(entity)
            entity._queue_join_time = self.clock
            self._push_delay(entity.PATIENCE, EventType.ABANDON, entity=entity,
                             data={'station': 'DJStage'})

    def _on_dj_leave(self, evt: Event) -> None:
        entity = evt.entity
        if entity.in_show_at != 'DJStage':
            return
        self.djstage.leave(entity)
        for e in self.djstage.try_admit_queued():
            e.abandon_event = None
            self._push_delay(sample_dj_stay(), EventType.DJ_LEAVE, entity=e)
        self._push_delay(0.0, EventType.NEXT, entity=entity)

    # ════════════════════════════════════════════════════════════════════════
    #  Station outcomes
    # ════════════════════════════════════════════════════════════════════════

    def _apply_photo_outcome(self, entity: Entity) -> None:
        if u01() < self.cfg.photo_satisfied_prob:
            entity.update_satisfaction(2.0)
            cost = 30.0 * entity.group_size
            entity.spend(cost)
            self.stats.add_revenue('photo', cost)
        else:
            if u01() < 0.5:
                entity.update_satisfaction(-0.5)

    def _apply_merch_outcome(self, entity: Entity) -> None:
        n = entity.group_size
        items = [
            (0.8,                      100.0),   # festival shirt
            (0.4,                       50.0),   # festival hat
            (0.9,                       40.0),   # flag
            (self.cfg.band_shirt_prob, 200.0),   # band shirt
        ]
        total = sum(price * n for prob, price in items if u01() < prob)
        entity.spend(total)
        self.stats.add_revenue('merch', total)

    # ════════════════════════════════════════════════════════════════════════
    #  Food / lunch
    # ════════════════════════════════════════════════════════════════════════

    def _on_lunch(self, evt: Event) -> None:
        entity = evt.entity
        r = u01()
        if r < 3/8:
            stall = self.food_burger
        elif r < 3/8 + 1/4:
            stall = self.food_pizza
        else:
            stall = self.food_asian
        entity._food_stall = stall

        if stall.has_free_server():
            idx = stall.free_server_index()
            stall.start_service(entity, idx)
            entity._queue_join_time = self.clock
            dur = stall.sample_service_duration(entity)
            self._push_delay(dur, EventType.FOOD_ORDER_END, entity=entity,
                             data={'stall': stall.name, 'server': idx})
        else:
            stall.enqueue(entity)
            entity._queue_join_time = self.clock

    def _on_food_order_end(self, evt: Event) -> None:
        entity = evt.entity
        idx    = evt.data['server']
        stall  = self._stations[evt.data['stall']]

        stall.end_service(entity, idx)

        cost = stall.calculate_cost(entity)
        entity.spend(cost)
        self.stats.add_revenue('food', cost)

        # Serve next in stall queue
        nxt = stall.dequeue()
        if nxt is not None:
            stall.start_service(nxt, idx)
            nxt._queue_join_time = self.clock
            dur = stall.sample_service_duration(nxt)
            self._push_delay(dur, EventType.FOOD_ORDER_END, entity=nxt,
                             data={'stall': stall.name, 'server': idx})

        prep = stall.sample_prep_time()
        self._push_delay(prep, EventType.FOOD_PREP_END, entity=entity,
                         data={'stall': stall.name})

    def _on_food_prep_end(self, evt: Event) -> None:
        entity = evt.entity
        if u01() < self.cfg.food_bad_prob:
            entity.update_satisfaction(-0.6)
        self._push_delay(FoodStation.sample_eating_time(),
                         EventType.EAT_END, entity=entity)

    def _on_eat_end(self, evt: Event) -> None:
        self._push_delay(0.0, EventType.NEXT, entity=evt.entity)

    # ════════════════════════════════════════════════════════════════════════
    #  End of day / overnight logic
    # ════════════════════════════════════════════════════════════════════════

    # Entities allowed to continue into day 2 (populated at DAY_END day 1)
    _overnight_allowed: set = set()

    def _on_day_end(self, evt: Event) -> None:
        day = evt.data['day']

        if day == 1:
            self._overnight_allowed = set()

            for eid in list(self._active_entities):
                # Retrieve entity from the stations/queues is complex;
                # instead we rely on each entity's own reference, which is
                # passed through events. We mark IDs here; the check happens
                # in _on_next_activity when the entity is next dispatched.
                pass   # processed per-entity below (see notes)

            # We cannot directly iterate entities (no global registry), so
            # the overnight gate is enforced lazily in _on_next_activity:
            # any entity with arrival_day==1 that runs NEXT after DAY_LEN
            # and is NOT in _overnight_allowed will be sent home.
            # _overnight_allowed is populated by entity arrival logic:
            #   FriendsGroup: if stays_overnight -> pre-registered at arrival
            #   Couple: satisfaction check happens when they hit NEXT after day end
            # This is handled via the _register_overnight helper called at arrival.

        if day == 2:
            # Festival is truly over – nothing more to do.
            pass

    def _register_overnight(self, entity: Entity) -> None:
        """Mark an entity as allowed to continue into day 2."""
        if entity.id not in self._overnight_allowed:
            self._overnight_allowed.add(entity.id)

    def _maybe_register_couple_overnight(self, entity: Couple) -> None:
        """Called when a Couple hits NEXT_ACTIVITY after clock >= DAY_LEN."""
        if (entity.arrival_day == 1
                and entity.id not in self._overnight_allowed
                and entity.satisfaction > 7.0):
            entity.stays_overnight = True
            entity.spend(250.0)
            self.stats.add_revenue('lodging', 250.0)
            self.stats.overnight_count += 1
            self._register_overnight(entity)

    # Override _on_next_activity to inject the couple overnight check
    def _on_next_activity(self, evt: Event) -> None:
        entity = evt.entity
        if entity.left_festival:
            return

        # Couple overnight decision: first NEXT call after day 1 closes
        if (isinstance(entity, Couple)
                and self.clock >= DAY_LEN
                and entity.arrival_day == 1
                and entity.id not in self._overnight_allowed):
            self._maybe_register_couple_overnight(entity)

        # FriendsGroup overnight was decided at arrival; register now if needed
        if (isinstance(entity, FriendsGroup)
                and entity.stays_overnight
                and entity.id not in self._overnight_allowed):
            self._register_overnight(entity)

        # Overnight gate
        if (self.clock >= DAY_LEN
                and entity.arrival_day == 1
                and entity.id not in self._overnight_allowed):
            self._entity_leaves(entity)
            return

        if isinstance(entity, Couple):
            entity.refresh_if_low()

        act = entity.next_activity()
        if act is None:
            self._entity_leaves(entity)
            return

        # Lunch window
        if (LUNCH_START <= self.clock <= LUNCH_END
                and not getattr(entity, '_had_lunch', False)):
            if u01() < self.cfg.lunch_prob:
                entity._had_lunch = True
                entity.activities_todo.insert(0, act)
                self._push_delay(0.0, EventType.LUNCH, entity=entity)
                return

        self._route_to(entity, act)

    # ════════════════════════════════════════════════════════════════════════
    #  Entity departure
    # ════════════════════════════════════════════════════════════════════════

    def _entity_leaves(self, entity: Entity) -> None:
        if entity.left_festival:
            return
        entity.left_festival = True
        self._active_entities.discard(entity.id)
        self.stats.record_departure(entity)


# ════════════════════════════════════════════════════════════════════════════
#  Convenience runner
# ════════════════════════════════════════════════════════════════════════════

def run_simulation(config: Optional[SimConfig] = None,
                   seed: Optional[int] = None) -> dict:
    """Run one replication and return the KPI summary dict."""
    if seed is not None:
        random.seed(seed)
    sim = FestivalSimulation(config)
    stats = sim.run()
    return stats.summary()
