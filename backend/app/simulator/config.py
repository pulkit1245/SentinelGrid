from __future__ import annotations
import json
import os
from pathlib import Path
from functools import lru_cache
from backend.app.simulator.models import SensorConfig

# Default config dir: project_root/simulator/config/
# Path: SentinelGrid/backend/app/simulator/config.py → .parent×4 = SentinelGrid/
DEFAULT_CONFIG_DIR = Path(__file__).parent.parent.parent.parent / 'simulator' / 'config'

@lru_cache(maxsize=1)
def load_sensor_configs() -> list[SensorConfig]:
    path = Path(os.environ.get('SIMULATOR_CONFIG_DIR', str(DEFAULT_CONFIG_DIR))) / 'sensors.json'
    with open(path) as f:
        data = json.load(f)
    return [SensorConfig(**s) for s in data]

@lru_cache(maxsize=1) 
def load_zones() -> list[dict]:
    path = Path(os.environ.get('SIMULATOR_CONFIG_DIR', str(DEFAULT_CONFIG_DIR))) / 'zones.json'
    with open(path) as f:
        return json.load(f)

@lru_cache(maxsize=1)
def load_thresholds() -> dict:
    path = Path(os.environ.get('SIMULATOR_CONFIG_DIR', str(DEFAULT_CONFIG_DIR))) / 'thresholds.json'
    with open(path) as f:
        return json.load(f)
