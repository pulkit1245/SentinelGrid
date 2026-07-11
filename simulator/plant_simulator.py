"""
Synthetic Plant Simulator -- main entrypoint.

Streams zone/sensor/permit/shift events to the ingest endpoint at a
1Hz-equivalent simulated rate, sped up by --speed for demoability.

Usage:
    python -m simulator.plant_simulator --scenario baseline --speed 60
    python -m simulator.plant_simulator --scenario compound_risk_1 --speed 30 --offline
    python -m simulator.plant_simulator --scenario compound_risk_1 --speed 0 --duration 4000
        (--speed 0 = run as fast as possible, no wall-clock throttling --
         useful for generating training data for Module 5's XGBoost scorer)
"""

import argparse
import importlib
import signal
import sys
import time
from datetime import datetime, timezone

from .ingest_client import IngestClient

SCENARIOS = {
    "baseline": "simulator.scenario_scripts.baseline_scenario",
    "compound_risk_1": "simulator.scenario_scripts.compound_risk_scenario_1",
}

DEFAULT_DURATION_S = {
    "baseline": 6000,
    "compound_risk_1": 4200,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Simulator:
    def __init__(self, scenario_name: str, speed: float, offline: bool,
                 base_url: str = None, seed: int = None):
        if scenario_name not in SCENARIOS:
            raise ValueError(f"Unknown scenario '{scenario_name}'. "
                              f"Choices: {list(SCENARIOS)}")
        module = importlib.import_module(SCENARIOS[scenario_name])
        self.scenario_name = scenario_name
        self.module = module
        self.speed = speed
        self.paused = False
        self._stop = False

        kwargs = {"seed": seed} if seed is not None else {}
        self.stream, self.roster, self.permit_events = module.build(**kwargs)
        self.client = IngestClient(base_url=base_url or "http://localhost:8000",
                                    offline=offline)

        self._permit_by_time = sorted(self.permit_events, key=lambda e: e["sim_time_s"])
        self._permit_idx = 0

    def _emit_sensor_tick(self, sim_time_s: float):
        events = self.stream.tick_events(sim_time_s, _now_iso())
        for ev in events:
            self.client.post_sensor(ev)
        return events

    def _emit_shift_events(self, sim_time_s: float):
        for ev in self.roster.events_up_to(sim_time_s):
            payload = self.roster.to_event_dict(ev, _now_iso())
            self.client.post_event(payload)
            print(f"[t={sim_time_s:.0f}s] SHIFT EVENT: {payload['event_type']} "
                  f"({payload['outgoing_shift']} -> {payload['incoming_shift']})")

    def _emit_permit_events(self, sim_time_s: float):
        while (self._permit_idx < len(self._permit_by_time)
               and self._permit_by_time[self._permit_idx]["sim_time_s"] <= sim_time_s):
            ev = dict(self._permit_by_time[self._permit_idx])
            ev["timestamp"] = _now_iso()
            self.client.post_event(ev)
            print(f"[t={sim_time_s:.0f}s] PERMIT EVENT: {ev['event_type']} "
                  f"{ev.get('permit_id')} in {ev.get('zone_id')}")
            self._permit_idx += 1

    def run(self, duration_s: float, tick_s: float = 1.0):
        print(f"Running scenario '{self.scenario_name}' for {duration_s:.0f} sim-seconds "
              f"at speed={self.speed}x ({'offline' if self.client.offline else self.client.base_url})")

        def handle_sigint(sig, frame):
            self._stop = True
            print("\nStopping simulator (received interrupt)...")

        signal.signal(signal.SIGINT, handle_sigint)

        sim_time_s = 0.0
        wall_start = time.monotonic()
        while sim_time_s <= duration_s and not self._stop:
            if self.paused:
                time.sleep(0.1)
                continue

            self._emit_sensor_tick(sim_time_s)
            self._emit_shift_events(sim_time_s)
            self._emit_permit_events(sim_time_s)

            sim_time_s += tick_s

            if self.speed > 0:
                # sleep just enough to keep wall-clock pace at `speed`x
                target_wall_elapsed = sim_time_s / self.speed
                actual_wall_elapsed = time.monotonic() - wall_start
                sleep_for = target_wall_elapsed - actual_wall_elapsed
                if sleep_for > 0:
                    time.sleep(sleep_for)
            # speed == 0 -> run flat out, no throttling (bulk data generation)

        print(f"Scenario '{self.scenario_name}' finished at sim_time_s={sim_time_s:.0f}")


def main():
    parser = argparse.ArgumentParser(description="SentinelGrid Synthetic Plant Simulator")
    parser.add_argument("--scenario", choices=list(SCENARIOS), default="baseline")
    parser.add_argument("--speed", type=float, default=60.0,
                         help="Simulated seconds per wall-clock second. 0 = run flat out.")
    parser.add_argument("--duration", type=float, default=None,
                         help="Sim-seconds to run. Defaults per-scenario.")
    parser.add_argument("--offline", action="store_true",
                         help="Log events to local JSONL instead of POSTing to the backend.")
    parser.add_argument("--base-url", default=None, help="Override the ingest API base URL.")
    parser.add_argument("--seed", type=int, default=None, help="Override the RNG seed.")
    args = parser.parse_args()

    duration = args.duration or DEFAULT_DURATION_S.get(args.scenario, 3600)
    sim = Simulator(args.scenario, speed=args.speed, offline=args.offline,
                     base_url=args.base_url, seed=args.seed)
    sim.run(duration_s=duration)


if __name__ == "__main__":
    main()
