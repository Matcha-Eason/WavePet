#!/usr/bin/env python3
"""Rule-based Codex desktop-pet state engine.

The engine consumes append-only Codex activity events and emits one JSON state
after each event. It is dependency-free so a plugin or desktop pet can vendor it
directly.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Iterable, Optional


STATE_ZH = {
    "reading_understanding": "读题理解",
    "steady_work": "稳定工作",
    "deep_output": "深度输出",
    "overheat_debugging": "红温调试",
    "closing": "收束",
}


@dataclass
class Thresholds:
    long_output_tokens: float = 300.0
    long_thinking_tokens: float = 120.0
    heavy_feedback_tokens: float = 1200.0
    tool_wait_ms: float = 8000.0
    silent_wait_ms: float = 3000.0
    overheat_pressure: float = 0.75
    closing_signal: float = 0.70


@dataclass
class TurnSummary:
    assistant_tokens: float = 0.0
    thinking_tokens: float = 0.0
    feedback_tokens: float = 0.0
    edit_count: int = 0
    test_count: int = 0
    error_count: int = 0
    finish_count: int = 0

    @property
    def visible_load(self) -> float:
        return self.assistant_tokens + self.thinking_tokens


@dataclass
class PetStateEngine:
    thresholds: Thresholds = field(default_factory=Thresholds)
    recent_window: int = 5
    session_id: str = "default"
    turn_id: str = "turn_0"
    turn_index: int = 0
    active: bool = False
    goal_mode: bool = False
    current: TurnSummary = field(default_factory=TurnSummary)
    recent_turns: Deque[TurnSummary] = field(default_factory=lambda: deque(maxlen=5))
    last_event_ms: Optional[int] = None
    assistant_start_ms: Optional[int] = None
    open_tool_start_ms: Optional[int] = None
    pending_user_tokens: float = 0.0
    state: str = "steady_work"
    raw_state: str = "steady_work"
    candidate_state: Optional[str] = None
    candidate_ticks: int = 0
    ticks_in_state: int = 0

    def update(self, event: Dict[str, Any]) -> Dict[str, Any]:
        now = int(event.get("timestamp_ms") or self._next_timestamp())
        self.session_id = str(event.get("session_id") or self.session_id)
        self.turn_id = str(event.get("turn_id") or self.turn_id)
        event_name = str(event.get("event") or "tick")
        self._apply_event(event_name, event, now)
        signals = self._signals(now)
        scores = self._scores(signals)
        raw_state = self._raw_state(scores)
        previous_state, changed = self._smooth(raw_state, scores, now)
        self.last_event_ms = now
        return self._output(now, raw_state, signals, scores, previous_state, changed)

    def _next_timestamp(self) -> int:
        return (self.last_event_ms or 0) + 1000

    def _apply_event(self, name: str, event: Dict[str, Any], now: int) -> None:
        if name == "user_message":
            if self.active:
                self._close_current_turn()
            self.pending_user_tokens += float(event.get("token_estimate") or 0)
            return

        if name == "assistant_start":
            if self.active:
                self._close_current_turn()
            self.active = True
            self.goal_mode = bool(event.get("goal_mode") or event.get("mode") == "goal")
            self.assistant_start_ms = now
            self.current = TurnSummary()
            self.current.feedback_tokens = self.pending_user_tokens
            self.pending_user_tokens = 0.0
            return

        if name == "assistant_token_delta":
            self.current.assistant_tokens += float(event.get("delta_tokens_est") or 0)
            return

        if name == "thinking_delta":
            self.current.thinking_tokens += float(event.get("delta_tokens_est") or 0)
            return

        if name == "tool_call_start":
            self.open_tool_start_ms = now
            return

        if name == "tool_call_end":
            self.current.feedback_tokens += float(event.get("output_tokens_est") or 0)
            if event.get("success") is False:
                self.current.error_count += 1
            self.open_tool_start_ms = None
            return

        if name == "file_edit":
            self.current.edit_count += 1
            return

        if name == "test_run_start":
            return

        if name == "test_run_end":
            self.current.test_count += 1
            self.current.feedback_tokens += float(event.get("output_tokens_est") or 0)
            failures = int(event.get("failure_count_est") or 0)
            if event.get("success") is False or failures > 0:
                self.current.error_count += max(1, failures)
            return

        if name == "error_feedback":
            severity = str(event.get("severity") or "error")
            weight = 2 if severity in {"fatal", "high"} else 1
            self.current.error_count += weight
            self.current.feedback_tokens += float(event.get("token_estimate") or 0)
            return

        if name == "task_end_signal":
            confidence = float(event.get("confidence") or 1.0)
            self.current.finish_count += 1 if confidence >= 0.5 else 0
            return

        if name == "assistant_end":
            self.current.finish_count += 1 if event.get("finish_reason") in {"stop", "complete", "done"} else 0
            self._close_current_turn()
            return

    def _close_current_turn(self) -> None:
        self.recent_turns.append(self.current)
        self.current = TurnSummary()
        self.active = False
        self.goal_mode = False
        self.turn_index += 1
        self.assistant_start_ms = None
        self.open_tool_start_ms = None

    def _recent_sum(self, attr: str) -> float:
        return float(sum(getattr(turn, attr) for turn in self.recent_turns))

    def _recent_max(self, attr: str) -> float:
        if not self.recent_turns:
            return 0.0
        return float(max(getattr(turn, attr) for turn in self.recent_turns))

    def _signals(self, now: int) -> Dict[str, float]:
        t = self.thresholds
        silent_ms = 0.0
        if self.active and self.last_event_ms is not None:
            silent_ms = max(0.0, float(now - self.last_event_ms))
        tool_wait_ms = 0.0
        if self.open_tool_start_ms is not None:
            tool_wait_ms = max(0.0, float(now - self.open_tool_start_ms))

        output_load = self.current.assistant_tokens / t.long_output_tokens
        thinking_load = self.current.thinking_tokens / t.long_thinking_tokens
        feedback_load = self.current.feedback_tokens / t.heavy_feedback_tokens
        recent_errors = self._recent_sum("error_count")
        recent_tests = self._recent_sum("test_count")
        current_error_pressure = self.current.error_count * 0.25 + recent_errors * 0.12
        validation_pressure = self.current.test_count * 0.12 + recent_tests * 0.06
        feedback_pressure = min(1.0, feedback_load) * 0.25
        error_pressure = min(1.0, current_error_pressure + validation_pressure + feedback_pressure)
        tool_wait_load = tool_wait_ms / t.tool_wait_ms
        silent_weight = 1.25 if self.goal_mode else 1.0
        silent_wait_load = silent_weight * silent_ms / t.silent_wait_ms
        closing_signal = min(1.0, self.current.finish_count * 0.8 + max(0.0, -self._visible_load_slope()) * 0.2)
        return {
            "output_load": _clamp(output_load),
            "thinking_load": _clamp(thinking_load),
            "feedback_load": _clamp(feedback_load),
            "error_pressure": _clamp(error_pressure),
            "tool_wait_load": _clamp(tool_wait_load),
            "silent_wait_load": _clamp(silent_wait_load),
            "closing_signal": _clamp(closing_signal),
        }

    def _visible_load_slope(self) -> float:
        values = [turn.visible_load for turn in self.recent_turns] + [self.current.visible_load]
        if len(values) < 2:
            return 0.0
        return (values[-1] - values[0]) / max(1.0, len(values) - 1)

    def _scores(self, signals: Dict[str, float]) -> Dict[str, float]:
        reading = 0.65 if self.turn_index <= 2 else 0.05
        reading *= 1.0 - max(signals["output_load"], signals["error_pressure"])
        deep = max(signals["output_load"], signals["thinking_load"], signals["silent_wait_load"] * 0.9)
        overheat = signals["error_pressure"]
        closing = signals["closing_signal"] * (1.0 - min(0.8, overheat))
        steady = 0.45 * (1.0 - max(deep, overheat, closing)) + 0.25
        return {
            "reading_understanding": _clamp(reading),
            "steady_work": _clamp(steady),
            "deep_output": _clamp(deep),
            "overheat_debugging": _clamp(overheat),
            "closing": _clamp(closing),
        }

    def _raw_state(self, scores: Dict[str, float]) -> str:
        priority = ["overheat_debugging", "deep_output", "closing", "reading_understanding", "steady_work"]
        best = max(priority, key=lambda name: (scores[name], -priority.index(name)))
        if scores["overheat_debugging"] >= self.thresholds.overheat_pressure:
            return "overheat_debugging"
        if scores["deep_output"] >= 0.75:
            return "deep_output"
        if scores["closing"] >= self.thresholds.closing_signal:
            return "closing"
        if scores["reading_understanding"] >= 0.45:
            return "reading_understanding"
        return best if scores[best] >= 0.45 else "steady_work"

    def _smooth(self, raw_state: str, scores: Dict[str, float], now: int) -> tuple[str, bool]:
        previous = self.state
        if raw_state == self.state:
            self.candidate_state = None
            self.candidate_ticks = 0
            self.ticks_in_state += 1
            self.raw_state = raw_state
            return previous, False

        min_dwell_ms = 4000 if self.state == "overheat_debugging" else 2000 if self.state == "deep_output" else 0
        elapsed = 0 if self.last_event_ms is None else now - self.last_event_ms
        enough_margin = scores[raw_state] >= scores.get(self.state, 0.0) + 0.20
        if self.candidate_state == raw_state:
            self.candidate_ticks += 1
        else:
            self.candidate_state = raw_state
            self.candidate_ticks = 1

        can_leave_overheat = self.state != "overheat_debugging" or scores["overheat_debugging"] < 0.45
        dwell_ok = min_dwell_ms == 0 or self.ticks_in_state * max(elapsed, 500) >= min_dwell_ms
        if can_leave_overheat and dwell_ok and (self.candidate_ticks >= 2 or enough_margin):
            self.state = raw_state
            self.ticks_in_state = 1
            self.raw_state = raw_state
            return previous, previous != self.state

        self.ticks_in_state += 1
        self.raw_state = raw_state
        return previous, False

    def _output(
        self,
        now: int,
        raw_state: str,
        signals: Dict[str, float],
        scores: Dict[str, float],
        previous_state: str,
        changed: bool,
    ) -> Dict[str, Any]:
        intensity = _clamp(max(scores[self.state], signals["output_load"], signals["error_pressure"]))
        confidence = _clamp(scores[self.state])
        return {
            "schema_version": "codex_pet_state.v0",
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "timestamp_ms": now,
            "state": self.state,
            "state_zh": STATE_ZH[self.state],
            "intensity": round(intensity, 4),
            "confidence": round(confidence, 4),
            "reason": reason_for(self.state),
            "signals": {key: round(value, 4) for key, value in signals.items()},
            "online_features": self._online_features(now),
            "state_scores": {key: round(value, 4) for key, value in scores.items()},
            "presentation": presentation_for(self.state, intensity),
            "smoothing": {
                "previous_state": previous_state,
                "raw_state": raw_state,
                "ticks_in_state": self.ticks_in_state,
                "changed": changed,
            },
        }

    def _online_features(self, now: int) -> Dict[str, Any]:
        return {
            "history_turn_index": self.turn_index,
            "recent_error_count_sum": self._recent_sum("error_count"),
            "recent_test_count_sum": self._recent_sum("test_count"),
            "recent_edit_count_sum": self._recent_sum("edit_count"),
            "recent_assistant_tokens_max": self._recent_max("assistant_tokens"),
            "recent_feedback_tokens_max": self._recent_max("feedback_tokens"),
            "current_assistant_tokens_streamed": self.current.assistant_tokens,
            "current_thinking_tokens_streamed": self.current.thinking_tokens,
            "current_feedback_tokens": self.current.feedback_tokens,
            "current_error_count": self.current.error_count,
            "current_test_count": self.current.test_count,
            "current_edit_count": self.current.edit_count,
            "current_tool_wait_ms": 0 if self.open_tool_start_ms is None else now - self.open_tool_start_ms,
            "current_silent_wait_ms": 0 if self.last_event_ms is None else max(0, now - self.last_event_ms),
            "goal_mode": self.goal_mode,
        }


def _clamp(value: float) -> float:
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return max(0.0, min(1.0, float(value)))


def reason_for(state: str) -> str:
    return {
        "reading_understanding": "Early low-pressure turn; likely reading or understanding context.",
        "steady_work": "Codex is making normal progress without strong waiting pressure.",
        "deep_output": "Current output, thinking, or silence is long enough to feel like deep work.",
        "overheat_debugging": "Errors, tests, logs, or validation pressure are high.",
        "closing": "Completion or wrap-up signals are stronger than active pressure.",
    }[state]


def presentation_for(state: str, intensity: float) -> Dict[str, Any]:
    table = {
        "reading_understanding": ("reading", "neutral", "读题", "我先看看..."),
        "steady_work": ("typing", "neutral", "工作", "稳定推进中"),
        "deep_output": ("intense_typing", "focus", "输出", "正在认真写..."),
        "overheat_debugging": ("shake", "hot", "调试", "压力上来了"),
        "closing": ("settle", "cool", "收束", "快整理好了"),
    }
    motion, tint, badge, bubble = table[state]
    return {
        "motion": motion,
        "tint": tint,
        "scale": round(1.0 + min(0.08, intensity * 0.08), 3),
        "badge": badge,
        "bubble": bubble,
        "cadence_ms": int(max(250, 900 - intensity * 450)),
    }


DEMO_EVENTS = [
    {"event": "user_message", "session_id": "demo", "turn_id": "turn_1", "timestamp_ms": 1000, "token_estimate": 180},
    {"event": "assistant_start", "session_id": "demo", "turn_id": "turn_1", "timestamp_ms": 1500, "goal_mode": True},
    {"event": "tick", "session_id": "demo", "turn_id": "turn_1", "timestamp_ms": 4500},
    {"event": "thinking_delta", "session_id": "demo", "turn_id": "turn_1", "timestamp_ms": 5200, "delta_tokens_est": 60},
    {"event": "assistant_token_delta", "session_id": "demo", "turn_id": "turn_1", "timestamp_ms": 6200, "delta_tokens_est": 180},
    {"event": "assistant_token_delta", "session_id": "demo", "turn_id": "turn_1", "timestamp_ms": 7600, "delta_tokens_est": 170},
    {"event": "test_run_end", "session_id": "demo", "turn_id": "turn_1", "timestamp_ms": 9000, "success": False, "output_tokens_est": 900, "failure_count_est": 2},
    {"event": "error_feedback", "session_id": "demo", "turn_id": "turn_1", "timestamp_ms": 9200, "severity": "high", "token_estimate": 300},
    {"event": "task_end_signal", "session_id": "demo", "turn_id": "turn_1", "timestamp_ms": 12000, "confidence": 0.8},
]


def iter_events(path: Optional[str], demo: bool) -> Iterable[Dict[str, Any]]:
    if demo:
        yield from DEMO_EVENTS
        return
    stream = open(path, "r", encoding="utf-8") if path else sys.stdin
    with stream:
        for line in stream:
            line = line.strip()
            if line:
                yield json.loads(line)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", help="Path to newline-delimited JSON events. Defaults to stdin.")
    parser.add_argument("--demo", action="store_true", help="Run built-in demo events.")
    args = parser.parse_args()

    engine = PetStateEngine()
    for event in iter_events(args.events, args.demo):
        print(json.dumps(engine.update(event), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
