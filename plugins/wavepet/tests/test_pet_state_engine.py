#!/usr/bin/env python3
"""Tests for the dependency-free pet state engine."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ENGINE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "pet_state_engine.py"
SPEC = importlib.util.spec_from_file_location("pet_state_engine", ENGINE_PATH)
assert SPEC is not None and SPEC.loader is not None
pet_state_engine = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pet_state_engine
SPEC.loader.exec_module(pet_state_engine)


class PetStateEngineTest(unittest.TestCase):
    def test_deep_output_from_streaming_tokens(self) -> None:
        engine = pet_state_engine.PetStateEngine()
        engine.update({"event": "user_message", "session_id": "s", "turn_id": "t1", "timestamp_ms": 1000, "token_estimate": 120})
        engine.update({"event": "assistant_start", "session_id": "s", "turn_id": "t1", "timestamp_ms": 1200})
        state = engine.update(
            {
                "event": "assistant_token_delta",
                "session_id": "s",
                "turn_id": "t1",
                "timestamp_ms": 1800,
                "delta_tokens_est": 360,
            }
        )
        self.assertEqual(state["state"], "deep_output")
        self.assertEqual(state["presentation"]["motion"], "intense_typing")
        self.assertGreaterEqual(state["signals"]["output_load"], 1.0)

    def test_overheat_from_failed_test_and_error(self) -> None:
        engine = pet_state_engine.PetStateEngine()
        events = [
            {"event": "assistant_start", "session_id": "s", "turn_id": "t1", "timestamp_ms": 1000},
            {
                "event": "test_run_end",
                "session_id": "s",
                "turn_id": "t1",
                "timestamp_ms": 2000,
                "success": False,
                "failure_count_est": 2,
                "output_tokens_est": 900,
            },
            {
                "event": "error_feedback",
                "session_id": "s",
                "turn_id": "t1",
                "timestamp_ms": 2200,
                "severity": "high",
                "token_estimate": 300,
            },
        ]
        state = {}
        for event in events:
            state = engine.update(event)
        self.assertEqual(state["state"], "overheat_debugging")
        self.assertEqual(state["presentation"]["motion"], "shake")
        self.assertEqual(state["presentation"]["tint"], "hot")

    def test_tick_silent_wait_in_goal_mode(self) -> None:
        engine = pet_state_engine.PetStateEngine()
        engine.update({"event": "assistant_start", "session_id": "s", "turn_id": "t1", "timestamp_ms": 1000, "goal_mode": True})
        state = engine.update({"event": "tick", "session_id": "s", "turn_id": "t1", "timestamp_ms": 5000})
        self.assertGreaterEqual(state["signals"]["silent_wait_load"], 1.0)
        self.assertIn(state["state"], {"deep_output", "steady_work"})
        self.assertIn("presentation", state)


if __name__ == "__main__":
    unittest.main()
