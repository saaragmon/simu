"""
Event-driven simulation engine for the Queuechella music festival.

Time unit : minutes (clock=0 ≡ 09:00 day 1)
Day 1     : clock [0, 660)
Day 2     : clock [660, 1320)

Events are processed in chronological order from a min-heap.
"""

import heapq
import math
import random
from collections import defaultdict

from distributions import (
    sample_friends_arrival_interval, sample_couple_interval,
    sample_single_interval, sample_ticket_scan, sample_security_check,
    sample_mainstage_duration, sample_sidestage_duration,
    sample_merch_service, sample_photo_duration,
    sample_battery_level, sample_charging_duration,
    sample_bodyart_glitter, sample_bodyart_neon, sample_bodyart_henna,
    sample_food_cashier_service, sample_eating_time,
    sample_pizza_prep, sample_burger_prep, sample_asian_prep,
    sample_dj_stay, u01,
)
from entities import FriendsGroup, Couple, Single, reset_entity_counter
from stations import (
    ServiceStation, BodyArtStation, ShowVenue, ContinuousVenue,
)

# ─── Time constants ───────────────────────────────────────────────────────────
DAY_LEN = 660        # minutes per operating day (09:00–20:00)
FESTIVAL_END = 1320  # end of day 2

FRIENDS_ARRIVE_END = 240   # 09:00+240 = 13:00
COUPLE_ARRIVE_START = 60   # 10:00
COUPLE_ARRIVE_END = 420    # 16:00
SINGLE_ARRIVE_END = 420    # 16:00

LUNCH_START = 240   # 13:00
LUNCH_END = 360     # 15:00

# ─── Event type constants ─────────────────────────────────────────────────────
(EVT_ARRIVE, EVT_SCAN_END, EVT_SECURITY_END,
 EVT_SVC_END, EVT_SHOW_START, EVT_SHOW_END,
 EVT_EARLY_LEAVE, EVT_DJ_LEAVE, EVT_ABANDON,
 EVT_NEXT, EVT_LUNCH, EVT_FOOD_ORDER_END,
 EVT_FOOD_PREP_END, EVT_EAT_END,
 EVT_DAY_END, EVT_ART_BREAK_END) = range(16)

_SEQ = 0  # global tie-breaker for equal-time events


def _mk_event(time: float, etype: int, priority: int = 5,
              entity=None, data: dict | None = None):
    global _SEQ
    _SEQ += 1
    return (time, priority, _SEQ, etype, entity, data or {})


# ─── Simulation class ─────────────────────────────────────────────────────────

class FestivalSimulation:

    def __init__(self, config: dict | None = None):
        self.cfg = config or {}
        self._heap: list = []
        self.clock = 0.0

        # ── stations ──────────────────────────────────────────────────────
        n_entry = self.cfg.get('entry_servers', 5)
        n_photo = self.cfg.get('photo_servers', 3)
        n_body  = self.cfg.get('body_servers', 2)
        ms_cap  = self.cfg.get('mainstage_cap', 200)
        ss_cap  = self.cfg.get('sidestage_cap', 100)
        dj_cap  = self.cfg.get('djstage_cap', 70)

        self.entry    = ServiceStation('EntryGate', n_entry)
        self.photo    = ServiceStation('PhotoStation', n_photo)
        self.charging = ServiceStation('ChargingStation', 150)
        self.merch    = ServiceStation('MerchTent', 7)
        self.bodyart  = BodyArtStation('BodyArt', n_body)
        self.mainstage = ShowVenue('MainStage', ms_cap, 'mainstream', 10.0)
        self.sidestage = ShowVenue('SideStage', ss_cap, 'indie', 5.0)
        self.djstage   = ContinuousVenue('DJStage', dj_cap)

        # Food stations (1 cashier each)
        self.food_pizza  = ServiceStation('FoodPizza', 1)
        self.food_burger = ServiceStation('FoodBurger', 1)
        self.food_asian  = ServiceStation('FoodAsian', 1)

        self._station_map = {
            'EntryGate': self.entry,
            'PhotoStation': self.photo,
            'ChargingStation': self.charging,
            'MerchTent': self.merch,
            'BodyArt': self.bodyart,
            'MainStage': self.mainstage,
            'SideStage': self.sidestage,
            'DJStage': self.djstage,
            'FoodPizza': self.food_pizza,
            'FoodBurger': self.food_burger,
            'FoodAsian': self.food_asian,
        }

        # ── show schedules (clock minutes) ──────────────────────────────
        self._ms_shows: list[tuple] = []  # (start, end)
        self._ss_shows: list[tuple] = []
        self._ms_show_idx = 0
        self._ss_show_idx = 0

        # ── statistics ────────────────────────────────────────────────────
        self.stats = defaultdict(float)
        self.satisfaction_log: list[float] = []
        self.wait_log: dict[str, list[float]] = defaultdict(list)
        self.queue_snapshots: dict[str, list[int]] = defaultdict(list)
        self.revenue_log: list[float] = []
        self.overnight_count = 0
        self.entity_count_by_type = defaultdict(int)
        self.total_people = 0

        # Track entities that spend overnight
        self._pending_overnight: list = []

    # ─── Scheduling helpers ───────────────────────────────────────────────

    def _push(self, time: float, etype: int, priority: int = 5,
              entity=None, data: dict | None = None):
        heapq.heappush(self._heap, _mk_event(time, etype, priority, entity, data))

    def _push_delay(self, delay: float, etype: int, priority: int = 5,
                    entity=None, data: dict | None = None):
        self._push(self.clock + delay, etype, priority, entity, data)

    # ─── Initialisation ───────────────────────────────────────────────────

    def _gen_show_schedule(self):
        """Pre-generate all show start/end times for both days."""
        for day in [1, 2]:
            offset = (day - 1) * DAY_LEN
            # MainStage
            t = offset
            while True:
                dur = sample_mainstage_duration()
                if t + dur > offset + DAY_LEN:
                    break
                self._ms_shows.append((t, t + dur))
                t += dur + 10.0
            # SideStage
            t = offset
            while True:
                dur = sample_sidestage_duration()
                if t + dur > offset + DAY_LEN:
                    break
                self._ss_shows.append((t, t + dur))
                t += dur + 5.0

    def _schedule_shows(self):
        for start, end in self._ms_shows:
            self._push(start, EVT_SHOW_START, 0, data={'venue': 'MainStage', 'end': end})
        for start, end in self._ss_shows:
            self._push(start, EVT_SHOW_START, 0, data={'venue': 'SideStage', 'end': end})

    def _schedule_arrivals(self):
        # FriendsGroup – day 1, 09:00–13:00
        t = 0.0
        while True:
            t += sample_friends_arrival_interval()
            if t >= FRIENDS_ARRIVE_END:
                break
            self._push(t, EVT_ARRIVE, data={'etype': 'friends', 'day': 1})

        # Couple – both days, 10:00–16:00
        for day in [1, 2]:
            off = (day - 1) * DAY_LEN
            t = off + COUPLE_ARRIVE_START
            while True:
                t += sample_couple_interval()
                if t >= off + COUPLE_ARRIVE_END:
                    break
                self._push(t, EVT_ARRIVE, data={'etype': 'couple', 'day': day})

        # Single – both days, 09:00–16:00
        for day in [1, 2]:
            off = (day - 1) * DAY_LEN
            t = off
            while True:
                t += sample_single_interval()
                if t >= off + SINGLE_ARRIVE_END:
                    break
                self._push(t, EVT_ARRIVE, data={'etype': 'single', 'day': day})

        # Day-end markers
        self._push(DAY_LEN, EVT_DAY_END, 0, data={'day': 1})
        self._push(FESTIVAL_END, EVT_DAY_END, 0, data={'day': 2})

    # ─── Main loop ────────────────────────────────────────────────────────

    def run(self):
        global _SEQ
        _SEQ = 0
        reset_entity_counter()

        self._gen_show_schedule()
        self._schedule_shows()
        self._schedule_arrivals()

        while self._heap:
            evt = heapq.heappop(self._heap)
            t, pri, seq, etype, entity, data = evt
            if t > FESTIVAL_END + 180:  # safety cutoff (3h after close)
                break
            self.clock = t
            self._dispatch(etype, entity, data)

        self._finalise_stats()

    def _dispatch(self, etype: int, entity, data: dict):
        if   etype == EVT_ARRIVE:          self._on_arrive(data)
        elif etype == EVT_SCAN_END:        self._on_scan_end(entity, data)
        elif etype == EVT_SECURITY_END:    self._on_security_end(entity, data)
        elif etype == EVT_SVC_END:         self._on_service_end(entity, data)
        elif etype == EVT_SHOW_START:      self._on_show_start(data)
        elif etype == EVT_SHOW_END:        self._on_show_end(data)
        elif etype == EVT_EARLY_LEAVE:     self._on_early_leave(entity, data)
        elif etype == EVT_DJ_LEAVE:        self._on_dj_leave(entity)
        elif etype == EVT_ABANDON:         self._on_abandon(entity, data)
        elif etype == EVT_NEXT:            self._on_next_activity(entity)
        elif etype == EVT_LUNCH:           self._on_lunch_decision(entity)
        elif etype == EVT_FOOD_ORDER_END:  self._on_food_order_end(entity, data)
        elif etype == EVT_FOOD_PREP_END:   self._on_food_prep_end(entity, data)
        elif etype == EVT_EAT_END:         self._on_eat_end(entity)
        elif etype == EVT_DAY_END:         self._on_day_end(data)
        elif etype == EVT_ART_BREAK_END:   self._on_art_break_end(data)

    # ─── Arrival ──────────────────────────────────────────────────────────

    def _on_arrive(self, data: dict):
        etype = data['etype']
        day   = data['day']

        if etype == 'friends':
            entity = FriendsGroup(arrival_day=day)
        elif etype == 'couple':
            entity = Couple(arrival_day=day)
        else:
            entity = Single(arrival_day=day)

        # Ticket revenue
        if entity.stays_overnight and etype == 'friends':
            entity.spend(700.0)   # ticket + lodging combo
            self.overnight_count += 1
        else:
            entity.spend(500.0)   # ticket only

        self.entity_count_by_type[etype] += 1
        self.total_people += entity.group_size
        self.stats['n_entities'] += 1
        self.stats['ticket_revenue'] += entity.total_revenue

        # Join entry gate
        self._join_entry(entity)

    # ─── Entry gate (2-phase: scan → security) ───────────────────────────

    def _join_entry(self, entity):
        station = self.entry
        if station.has_free_server():
            idx = station.free_server()
            station.start_service(entity, idx)
            dur = sample_ticket_scan()
            self._push_delay(dur, EVT_SCAN_END, entity=entity, data={'server': idx})
        else:
            station.enqueue(entity)
            entity._queue_join_time = self.clock

    def _on_scan_end(self, entity, data: dict):
        server_idx = data['server']
        # Stay on same server for security check
        dur = sample_security_check()
        self._push_delay(dur, EVT_SECURITY_END, entity=entity,
                         data={'server': server_idx})

    def _on_security_end(self, entity, data: dict):
        server_idx = data['server']
        self.entry.end_service(entity, server_idx)

        # Serve next in entry queue
        nxt = self.entry.dequeue()
        if nxt is not None:
            wait = self.clock - nxt._queue_join_time
            nxt.total_wait_min += wait
            self.wait_log['EntryGate'].append(wait)
            self.entry.start_service(nxt, server_idx)
            dur = sample_ticket_scan()
            self._push_delay(dur, EVT_SCAN_END, entity=nxt, data={'server': server_idx})

        # Entity enters festival – build activity list
        self._build_entity_activities(entity)
        self._push_delay(0.0, EVT_NEXT, entity=entity)

    def _build_entity_activities(self, entity):
        if isinstance(entity, FriendsGroup):
            ql = {s: self._station_map[s].queue_length()
                  for s in FriendsGroup.ALL_STATIONS
                  if s in self._station_map}
            entity.build_activities(ql)
        elif isinstance(entity, Couple):
            pass  # already built in __init__
        # Single already has fixed list

    # ─── Activity dispatcher ──────────────────────────────────────────────

    def _on_next_activity(self, entity):
        if entity.left_festival:
            return

        # Refresh couple activity list when running low
        if isinstance(entity, Couple) and len(entity.activities_todo) < 3:
            entity.refresh_activities()

        act = entity.next_activity()
        if act is None:
            self._entity_leaves(entity)
            return

        # Check lunch window before proceeding
        if LUNCH_START <= self.clock <= LUNCH_END:
            if u01() < self.cfg.get('lunch_prob', 0.70):
                # Pause for lunch; put current activity back
                entity.activities_todo.insert(0, act)
                self._push_delay(0.0, EVT_LUNCH, entity=entity)
                return

        self._route_to_activity(entity, act)

    def _route_to_activity(self, entity, act: str):
        if act == 'MainStage':
            self._join_show(entity, self.mainstage)
        elif act == 'SideStage':
            self._join_show(entity, self.sidestage)
        elif act == 'DJStage':
            self._join_dj(entity)
        elif act == 'PhotoStation':
            self._join_service(entity, self.photo, 'photo')
        elif act == 'ChargingStation':
            self._join_service(entity, self.charging, 'charging')
        elif act == 'MerchTent':
            self._join_service(entity, self.merch, 'merch')
        elif act == 'BodyArt':
            self._join_bodyart(entity)
        else:
            self._on_next_activity(entity)

    # ─── Service stations ─────────────────────────────────────────────────

    def _join_service(self, entity, station: ServiceStation, stype: str):
        if station.has_free_server():
            idx = station.free_server()
            station.start_service(entity, idx)
            entity._queue_join_time = self.clock
            dur = self._sample_service(stype, entity)
            self._push_delay(dur, EVT_SVC_END, entity=entity,
                             data={'station': station.name, 'server': idx, 'stype': stype})
        else:
            station.enqueue(entity)
            entity._queue_join_time = self.clock
            # Schedule patience-based abandonment
            ae = self._push_delay(entity.PATIENCE, EVT_ABANDON, entity=entity,
                                  data={'station': station.name})
            entity.abandon_event = ae

    def _sample_service(self, stype: str, entity) -> float:
        if stype == 'photo':
            return sample_photo_duration()
        elif stype == 'charging':
            b = sample_battery_level()
            entity._battery = b
            return sample_charging_duration(b)
        elif stype == 'merch':
            return sample_merch_service()
        return 1.0

    def _on_service_end(self, entity, data: dict):
        sname  = data['station']
        sidx   = data['server']
        stype  = data.get('stype', '')
        station = self._station_map[sname]

        wait = self.clock - entity._queue_join_time
        entity.total_wait_min += wait
        self.wait_log[sname].append(wait)
        station.end_service(entity, sidx)

        # Station-specific outcomes
        if stype == 'photo':
            self._photo_outcome(entity)
        elif stype == 'merch':
            self._merch_outcome(entity)
        elif stype == 'charging':
            pass  # no satisfaction change

        # Serve next from queue
        self._serve_next_from_queue(station, sidx, stype)

        self._push_delay(0.0, EVT_NEXT, entity=entity)

    def _serve_next_from_queue(self, station: ServiceStation, sidx: int, stype: str):
        if station.queue_length() == 0:
            return
        nxt = station.dequeue()
        # Cancel their abandon event (mark as stale)
        nxt.abandon_event = None
        wait = self.clock - nxt._queue_join_time
        nxt.total_wait_min += wait
        self.wait_log[station.name].append(wait)
        station.start_service(nxt, sidx)
        nxt._queue_join_time = self.clock
        dur = self._sample_service(stype, nxt)
        self._push_delay(dur, EVT_SVC_END, entity=nxt,
                         data={'station': station.name, 'server': sidx, 'stype': stype})

    def _on_abandon(self, entity, data: dict):
        # Stale abandon events (entity already served) are silently ignored
        sname = data['station']
        station = self._station_map.get(sname)
        if station is None:
            return
        if entity.in_queue_at != sname:
            return  # already served or gone
        station.remove_from_queue(entity)
        station.n_abandoned += 1

        # Satisfaction penalty
        penalty = {'friends': 2.0, 'couple': 1.5, 'single': 1.0}
        entity.update_satisfaction(-penalty.get(entity.etype, 1.0))

        self._push_delay(0.0, EVT_NEXT, entity=entity)

    # ─── BodyArt station ─────────────────────────────────────────────────

    def _join_bodyart(self, entity):
        station = self.bodyart
        idx = station.free_available_artist(self.clock)
        if idx >= 0:
            station.start_service(entity, idx)
            entity._queue_join_time = self.clock
            art_type, dur = self._sample_bodyart()
            entity._art_type = art_type
            self._push_delay(dur, EVT_SVC_END, entity=entity,
                             data={'station': 'BodyArt', 'server': idx, 'stype': 'bodyart'})
        else:
            station.enqueue(entity)
            entity._queue_join_time = self.clock
            self._push_delay(entity.PATIENCE, EVT_ABANDON, entity=entity,
                             data={'station': 'BodyArt'})

    def _sample_bodyart(self) -> tuple[str, float]:
        r = u01()
        if r < 0.3:
            return ('glitter', sample_bodyart_glitter())
        elif r < 0.6:
            return ('neon', sample_bodyart_neon())
        else:
            return ('henna', sample_bodyart_henna())

    def _bodyart_outcome(self, entity):
        art = getattr(entity, '_art_type', 'glitter')
        satisfied_probs = {'glitter': 0.7, 'neon': 0.6, 'henna': 0.8}
        sat_deltas = {'glitter': 0.8, 'neon': 1.2, 'henna': 0.7}
        if u01() < satisfied_probs.get(art, 0.7):
            entity.update_satisfaction(sat_deltas.get(art, 0.8))

    # Override service end for bodyart to handle breaks
    def _on_service_end_bodyart(self, entity, sidx: int):
        station = self.bodyart
        station.end_service(entity, sidx)
        needs_break = (station._drawings_done[sidx] == 0)  # reset means break needed

        self._bodyart_outcome(entity)
        wait = self.clock - entity._queue_join_time
        entity.total_wait_min += wait
        self.wait_log['BodyArt'].append(wait)

        if needs_break:
            station.record_break(sidx, self.clock)
            self._push_delay(BodyArtStation.BREAK_DURATION, EVT_ART_BREAK_END,
                             data={'server': sidx})
        else:
            self._serve_next_bodyart(sidx)

        self._push_delay(0.0, EVT_NEXT, entity=entity)

    def _on_art_break_end(self, data: dict):
        sidx = data['server']
        self._serve_next_bodyart(sidx)

    def _serve_next_bodyart(self, sidx: int):
        station = self.bodyart
        if not station.queue:
            return
        nxt = station.dequeue()
        nxt.abandon_event = None
        wait = self.clock - nxt._queue_join_time
        nxt.total_wait_min += wait
        self.wait_log['BodyArt'].append(wait)
        station.start_service(nxt, sidx)
        nxt._queue_join_time = self.clock
        art_type, dur = self._sample_bodyart()
        nxt._art_type = art_type
        self._push_delay(dur, EVT_SVC_END, entity=nxt,
                         data={'station': 'BodyArt', 'server': sidx, 'stype': 'bodyart'})

    # ─── Show venues (MainStage / SideStage) ────────────────────────────

    def _join_show(self, entity, venue: ShowVenue):
        """Entity waits in the show queue; admission happens at EVT_SHOW_START."""
        venue.enqueue(entity)
        # No patience limit for shows (entities wait as long as needed)

    def _on_show_start(self, data: dict):
        vname = data['venue']
        end   = data['end']
        venue = self.mainstage if vname == 'MainStage' else self.sidestage

        admitted = venue.fill_show()

        # Schedule show end
        self._push(end, EVT_SHOW_END, 0, data={'venue': vname, 'end': end})

        # Schedule early-leave check for the back 10 entities at MainStage
        if vname == 'MainStage' and admitted:
            back10 = venue.back_ten_entities()
            for e in back10:
                self._push_delay(15.0, EVT_EARLY_LEAVE, entity=e,
                                 data={'venue': vname, 'show_end': end})

    def _on_show_end(self, data: dict):
        vname = data['venue']
        venue = self.mainstage if vname == 'MainStage' else self.sidestage
        attendees = venue.end_show()

        for e in attendees:
            self._show_outcome(e, vname)
            self._push_delay(0.0, EVT_NEXT, entity=e)

        # Admit waiting entities immediately for the next show
        # (they'll enter when the next show starts — nothing to do here)

    def _on_early_leave(self, entity, data: dict):
        if entity.in_show_at != data['venue']:
            return  # already left
        if u01() < 0.5:
            venue = self.mainstage if data['venue'] == 'MainStage' else self.sidestage
            venue.remove_attendee(entity)
            self._show_outcome(entity, data['venue'])
            self._push_delay(0.0, EVT_NEXT, entity=entity)

    def _show_outcome(self, entity, vname: str):
        """Update satisfaction after a show experience."""
        genre_val = 3 if vname == 'MainStage' else (2 if vname == 'SideStage' else 1)
        genre_val = self.cfg.get('mainstage_genre_val', genre_val) if vname == 'MainStage' else genre_val
        hour_end = (self.clock % DAY_LEN) / 60.0 + 9.0  # hour of day (9–20)
        if u01() < 0.5:
            score = ((genre_val - 1) / 2.0) + ((hour_end - 1) / 19.0)
            entity.update_satisfaction(score)
        else:
            entity.update_satisfaction(-1.0)

    # ─── DJStage ──────────────────────────────────────────────────────────

    def _join_dj(self, entity):
        dj = self.djstage
        if not dj.is_full() and self._can_fit_dj(entity):
            dj.admit(entity)
            stay = sample_dj_stay()
            self._push_delay(stay, EVT_DJ_LEAVE, entity=entity)
        else:
            dj.enqueue(entity)
            entity._queue_join_time = self.clock
            self._push_delay(entity.PATIENCE, EVT_ABANDON, entity=entity,
                             data={'station': 'DJStage'})

    def _can_fit_dj(self, entity) -> bool:
        return self.djstage.occupancy() + entity.group_size <= self.djstage.capacity

    def _on_dj_leave(self, entity):
        if entity.in_show_at != 'DJStage':
            return
        self.djstage.leave(entity)
        # Admit waiting entities
        admitted = self.djstage.try_admit_queued()
        for e in admitted:
            e.abandon_event = None
            stay = sample_dj_stay()
            self._push_delay(stay, EVT_DJ_LEAVE, entity=e)
        self._push_delay(0.0, EVT_NEXT, entity=entity)

    # ─── Photo station outcomes ───────────────────────────────────────────

    def _photo_outcome(self, entity):
        prob = self.cfg.get('photo_satisfied_prob', 0.70)
        if u01() < prob:
            entity.update_satisfaction(2.0)
            price = 30.0
            entity.spend(price)
            self.stats['photo_revenue'] += price * entity.group_size
        else:
            if u01() < 0.5:
                entity.update_satisfaction(-0.5)

    # ─── Merch tent outcomes ──────────────────────────────────────────────

    def _merch_outcome(self, entity):
        n = entity.group_size
        shirt_prob = self.cfg.get('band_shirt_prob', 0.3)
        items = [
            (0.8, 100.0),   # festival shirt
            (0.4,  50.0),   # festival hat
            (0.9,  40.0),   # flag
            (shirt_prob, 200.0),  # band shirt (configurable)
        ]
        total = 0.0
        for prob, price in items:
            if u01() < prob:
                total += price * n
        entity.spend(total)
        self.stats['merch_revenue'] += total

    # ─── Food / lunch ──────────────────────────────────────────────────────

    def _on_lunch_decision(self, entity):
        # Choose restaurant
        r = u01()
        if r < 3/8:
            restaurant = 'FoodBurger'
        elif r < 3/8 + 1/4:
            restaurant = 'FoodPizza'
        else:
            restaurant = 'FoodAsian'
        entity._restaurant = restaurant
        station = self._station_map[restaurant]

        if station.has_free_server():
            idx = station.free_server()
            station.start_service(entity, idx)
            entity._queue_join_time = self.clock
            dur = sample_food_cashier_service()
            self._push_delay(dur, EVT_FOOD_ORDER_END, entity=entity,
                             data={'restaurant': restaurant, 'server': idx})
        else:
            station.enqueue(entity)
            entity._queue_join_time = self.clock

    def _on_food_order_end(self, entity, data: dict):
        restaurant = data['restaurant']
        sidx = data['server']
        station = self._station_map[restaurant]
        station.end_service(entity, sidx)

        # Food cost
        if restaurant == 'FoodBurger':
            cost = 100.0 * entity.group_size
            prep = sample_burger_prep()
        elif restaurant == 'FoodPizza':
            # Singles order individual (40₪), groups order family trays (100₪ per 3 people)
            if entity.etype == 'single':
                cost = 40.0
            else:
                cost = math.ceil(entity.group_size / 3) * 100.0
            prep = sample_pizza_prep()
        else:
            cost = 65.0 * entity.group_size
            prep = sample_asian_prep()

        entity.spend(cost)
        self.stats['food_revenue'] += cost

        # Serve next in food queue
        nxt = station.dequeue()
        if nxt is not None:
            station.start_service(nxt, sidx)
            nxt._queue_join_time = self.clock
            dur = sample_food_cashier_service()
            self._push_delay(dur, EVT_FOOD_ORDER_END, entity=nxt,
                             data={'restaurant': restaurant, 'server': sidx})

        self._push_delay(prep, EVT_FOOD_PREP_END, entity=entity,
                         data={'restaurant': restaurant})

    def _on_food_prep_end(self, entity, data: dict):
        # Satisfaction effect
        if u01() < 0.4:
            entity.update_satisfaction(-0.6)
        eat_time = sample_eating_time()
        self._push_delay(eat_time, EVT_EAT_END, entity=entity)

    def _on_eat_end(self, entity):
        self._push_delay(0.0, EVT_NEXT, entity=entity)

    # ─── End of day / festival ────────────────────────────────────────────

    def _on_day_end(self, data: dict):
        day = data['day']
        if day == 1:
            # Process overnight stays
            for e in list(self._pending_overnight):
                pass  # already counted at arrival; entity events continue naturally
            self._pending_overnight.clear()

    def _entity_leaves(self, entity):
        if entity.left_festival:
            return
        entity.left_festival = True
        self.satisfaction_log.append(entity.satisfaction)
        self.revenue_log.append(entity.total_revenue)
        self.stats['total_revenue'] += entity.total_revenue

    # ─── Couple overnight check ───────────────────────────────────────────

    def _check_couple_overnight(self, entity):
        if entity.etype == 'couple' and entity.satisfaction > 7.0:
            entity.stays_overnight = True
            entity.spend(250.0)   # lodging
            self.stats['ticket_revenue'] += 250.0
            self.overnight_count += 1

    # ─── Final statistics ────────────────────────────────────────────────

    def _finalise_stats(self):
        n = len(self.satisfaction_log)
        if n > 0:
            self.stats['avg_satisfaction'] = sum(self.satisfaction_log) / n
            self.stats['n_departed'] = n

        for sname, waits in self.wait_log.items():
            if waits:
                self.stats[f'avg_wait_{sname}'] = sum(waits) / len(waits)
                self.stats[f'max_wait_{sname}'] = max(waits)

        self.stats['total_people'] = self.total_people

    def report(self) -> dict:
        """Return key KPI dictionary."""
        return dict(self.stats)


# ─── Convenience runner ───────────────────────────────────────────────────────

def run_simulation(config: dict | None = None, seed: int | None = None) -> dict:
    """Run one replication of the festival simulation and return KPIs."""
    if seed is not None:
        random.seed(seed)
    sim = FestivalSimulation(config)
    sim.run()
    result = sim.report()
    result['satisfaction_scores'] = sim.satisfaction_log
    result['wait_log'] = dict(sim.wait_log)
    result['entity_counts'] = dict(sim.entity_count_by_type)
    return result
