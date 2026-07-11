"""
Shift-roster generator.

Emits shift-boundary events (day/night/changeover) on a schedule the
Compound Risk Agent can query for "shift boundary within 30 min."

Default schedule: 12h shifts (day 06:00-18:00, night 18:00-06:00), with a
"changeover window" starting 30 min before each boundary -- this is the
window the Compound Risk Agent's pattern query checks against.
"""

from dataclasses import dataclass
from typing import List, Optional

SHIFT_LENGTH_S = 12 * 3600
CHANGEOVER_WINDOW_S = 30 * 60  # matches the "within 30 min" pattern condition


@dataclass
class ShiftEvent:
    sim_time_s: float
    event_type: str  # "changeover_window_start" | "shift_boundary" | "changeover_window_end"
    outgoing_shift: str
    incoming_shift: str


class ShiftRosterGenerator:
    def __init__(self, shift_length_s: float = SHIFT_LENGTH_S,
                 changeover_window_s: float = CHANGEOVER_WINDOW_S,
                 sim_start_offset_s: float = 0.0):
        """
        sim_start_offset_s lets you phase the schedule so sim_time_s=0 lands
        at an arbitrary point in the day/night cycle (useful for scenario
        scripting -- e.g. start 20 min before a changeover on purpose).
        """
        self.shift_length_s = shift_length_s
        self.changeover_window_s = changeover_window_s
        self.sim_start_offset_s = sim_start_offset_s
        self._emitted = set()
        self._cursor_idx = None  # lazily initialized on first events_up_to() call

    def _shift_name(self, boundary_index: int) -> str:
        return "day" if boundary_index % 2 == 0 else "night"

    def events_up_to(self, sim_time_s: float) -> List[ShiftEvent]:
        """
        Returns any shift-schedule events (window-start, boundary, window-end)
        that fall at or before sim_time_s and haven't been emitted yet.
        Call this once per tick with the current sim_time_s.
        """
        t = sim_time_s + self.sim_start_offset_s
        new_events = []

        if self._cursor_idx is None:
            self._cursor_idx = max(1, int(t // self.shift_length_s) + 1)

        # Walk forward one boundary at a time. The cursor only advances past
        # idx once idx's own "boundary" event has fired, so a boundary can
        # never be skipped even though window_start fires on an earlier tick.
        while True:
            idx = self._cursor_idx
            boundary_t = idx * self.shift_length_s
            window_start_t = boundary_t - self.changeover_window_s

            outgoing = self._shift_name(idx - 1)
            incoming = self._shift_name(idx)

            progressed = False
            for key, ev_time, ev_type in (
                (("window_start", idx), window_start_t, "changeover_window_start"),
                (("boundary", idx), boundary_t, "shift_boundary"),
            ):
                if key in self._emitted:
                    continue
                real_time = ev_time - self.sim_start_offset_s
                if 0 <= real_time <= sim_time_s:
                    self._emitted.add(key)
                    new_events.append(ShiftEvent(
                        sim_time_s=real_time,
                        event_type=ev_type,
                        outgoing_shift=outgoing,
                        incoming_shift=incoming,
                    ))
                    progressed = True

            if ("boundary", idx) in self._emitted:
                self._cursor_idx += 1
                continue  # check if the *next* boundary's window also opened by now
            if not progressed:
                break

        return sorted(new_events, key=lambda e: e.sim_time_s)

    def next_boundary_s(self, sim_time_s: float) -> float:
        """Sim-seconds until the next shift boundary (for agent queries)."""
        t = sim_time_s + self.sim_start_offset_s
        idx = int(t // self.shift_length_s) + 1
        boundary_t = idx * self.shift_length_s
        return boundary_t - t

    def to_event_dict(self, ev: ShiftEvent, wall_clock_iso: str) -> dict:
        return {
            "event_type": ev.event_type,
            "outgoing_shift": ev.outgoing_shift,
            "incoming_shift": ev.incoming_shift,
            "sim_time_s": ev.sim_time_s,
            "timestamp": wall_clock_iso,
        }
