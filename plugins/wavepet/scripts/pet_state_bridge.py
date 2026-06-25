#!/usr/bin/env python3
"""Bridge WavePet output into a local Codex-readable state file.

The current Codex BSOD/pet runtime does not expose a documented local state API.
This bridge provides the smallest useful integration surface: it consumes Codex
event JSONL, runs the pet state engine, and writes the latest state to:

  ~/Library/Application Support/Codex/wavepet/current_state.json

Native or official pet surfaces can consume this file if/when a file-based
adapter hook is available.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any, Iterable

from pet_state_engine import DEMO_EVENTS, PetStateEngine


DEFAULT_OUT_DIR = Path.home() / "Library" / "Application Support" / "Codex" / "wavepet"


def iter_events(path: Path | None, demo: bool) -> Iterable[dict[str, Any]]:
    if demo:
        yield from DEMO_EVENTS
        return
    stream = path.open("r", encoding="utf-8") if path else sys.stdin
    with stream:
        for line in stream:
            line = line.strip()
            if line:
                yield json.loads(line)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path, help="Path to newline-delimited event JSON. Defaults to stdin.")
    parser.add_argument("--demo", action="store_true", help="Use built-in demo events.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--history", action="store_true", help="Append every state to state_history.jsonl.")
    parser.add_argument("--sleep-ms", type=int, default=0, help="Optional delay between events for visual tests.")
    args = parser.parse_args()

    engine = PetStateEngine()
    latest_path = args.out_dir / "current_state.json"
    history_path = args.out_dir / "state_history.jsonl"
    count = 0
    for event in iter_events(args.events, args.demo):
        state = engine.update(event)
        atomic_write_json(latest_path, state)
        if args.history:
            args.out_dir.mkdir(parents=True, exist_ok=True)
            with history_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(state, ensure_ascii=False) + "\n")
        count += 1
        if args.sleep_ms > 0:
            time.sleep(args.sleep_ms / 1000)
    print(json.dumps({"states_written": count, "latest_path": str(latest_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
