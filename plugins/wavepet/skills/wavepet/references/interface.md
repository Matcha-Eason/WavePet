# WavePet Interface

## Purpose

Represent user-perceived Codex waiting experience. The state describes what the user likely feels while Codex is working, not exact model compute, exact remaining turns, or task success probability.

## Input Event Shape

Every event should be JSON:

```json
{
  "event": "assistant_token_delta",
  "session_id": "session_1",
  "turn_id": "turn_3",
  "timestamp_ms": 1782268560123,
  "delta_tokens_est": 42
}
```

Required fields:

- `event`: event name.
- `session_id`: stable session id.
- `turn_id`: current assistant/user turn id when available.
- `timestamp_ms`: wall-clock milliseconds.

Useful optional fields by event:

| Event | Fields |
|---|---|
| `user_message` | `text_chars`, `token_estimate` |
| `assistant_start` | `mode`, `goal_mode`, `model` |
| `assistant_token_delta` | `delta_chars`, `delta_tokens_est` |
| `thinking_delta` | `delta_chars`, `delta_tokens_est` |
| `tool_call_start` | `tool_name`, `call_kind` |
| `tool_call_end` | `tool_name`, `success`, `duration_ms`, `output_tokens_est` |
| `file_edit` | `path`, `edit_kind`, `changed_lines_est` |
| `test_run_start` | `command_kind` |
| `test_run_end` | `success`, `duration_ms`, `output_tokens_est`, `failure_count_est` |
| `error_feedback` | `error_kind`, `severity`, `token_estimate` |
| `assistant_end` | `finish_reason`, `total_tokens_est` |
| `task_end_signal` | `source`, `confidence` |
| `tick` | `timestamp_ms` only is enough |

## Online Features

Maintain three layers:

- Historical cumulative features before the current turn: prior output, thinking, feedback, edits, tests, errors, and turn index.
- Recent-window features over the last 5 turns: error density, test density, edit density, output peak, feedback peak, visible-load slope.
- Current streaming features: streamed assistant tokens, streamed thinking tokens, feedback tokens, tool wait, silent wait, token rate, output relative to recent mean.

## Priority

Resolve simultaneous states using:

```text
overheat_debugging > deep_output > closing > reading_understanding > steady_work
```

## Smoothing

Recommended defaults:

- Update every 500-1000 ms.
- Switch only when a new raw state wins for 2 ticks or beats the current state by 0.20.
- Keep `deep_output` for at least 2 seconds.
- Keep `overheat_debugging` for at least 4 seconds.
- Exit `overheat_debugging` only after error pressure stays below 0.45 for 2 ticks.
- Increase silent-wait load after 3 seconds without events while assistant is active.

## Output JSON

The engine returns:

```json
{
  "schema_version": "codex_pet_state.v0",
  "session_id": "session_1",
  "turn_id": "turn_3",
  "timestamp_ms": 1782268560123,
  "state": "deep_output",
  "state_zh": "深度输出",
  "intensity": 0.78,
  "confidence": 0.84,
  "reason": "Current visible output is high and still increasing.",
  "signals": {
    "output_load": 0.91,
    "thinking_load": 0.42,
    "feedback_load": 0.28,
    "error_pressure": 0.12,
    "tool_wait_load": 0.0,
    "silent_wait_load": 0.08,
    "closing_signal": 0.18
  },
  "presentation": {
    "motion": "intense_typing",
    "tint": "focus",
    "scale": 1.04,
    "badge": "输出中",
    "bubble": "正在认真写...",
    "cadence_ms": 500
  },
  "smoothing": {
    "previous_state": "steady_work",
    "raw_state": "deep_output",
    "ticks_in_state": 3,
    "changed": true
  }
}
```

## Single-Image Pet Compatibility

If a pet has only one image, ignore state-specific sprite names and use:

- `motion` for bobbing, shaking, typing cadence, or stillness.
- `tint` for neutral/focus/warm/hot/cool overlay.
- `scale` for subtle enlargement under high intensity.
- `badge` for a tiny status label.
- `bubble` for optional text.
- `cadence_ms` for animation tempo.
