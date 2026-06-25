---
name: wavepet
description: Use when Codex needs to map live Codex agent events, streaming assistant output, tool calls, file edits, tests, errors, or waiting time into desktop-pet states; design or consume Codex pet-state JSON; integrate a desktop pet that may have either rich state-specific images or only one static image.
---

# WavePet

Use this skill to convert Codex activity into a small set of desktop-pet states that reflect user-perceived waiting experience.

Core states:

- `reading_understanding`: early, low-output understanding.
- `steady_work`: normal progress without strong waiting pressure.
- `deep_output`: long current output, long thinking, or long silence while assistant is still working.
- `overheat_debugging`: errors, failed tests, repeated validation, or heavy tool/log feedback.
- `closing`: completion, summary, or low-pressure wrap-up.

## Workflow

1. Read `references/interface.md` when designing an integration, renderer, or event adapter.
2. Use `scripts/pet_state_engine.py` for deterministic local state updates.
3. Feed append-only events to the engine. Prefer frequent streaming events over only per-turn summaries.
4. Render `state`, `intensity`, `signals`, and `presentation`; do not depend on state-specific images being available.

## Runtime Model

The engine is intentionally rule-based. It uses the experiment-backed pattern:

```text
historical inertia + current streaming signals + smoothing
```

Do not present its state as true model compute load or exact remaining time. It is a user-experience signal.

## Event Names

Supported event names:

- `user_message`
- `assistant_start`
- `assistant_token_delta`
- `thinking_delta`
- `tool_call_start`
- `tool_call_end`
- `file_edit`
- `test_run_start`
- `test_run_end`
- `error_feedback`
- `assistant_end`
- `task_end_signal`
- `tick`

Use `tick` every 500-1000 ms while a turn is active, especially when there is no token output.

## CLI Examples

Run a demo:

```bash
python3 scripts/pet_state_engine.py --demo
```

Process newline-delimited JSON events:

```bash
python3 scripts/pet_state_engine.py --events examples/sample_events.jsonl
```

The CLI prints one state JSON per input event. Integrations can call the script, import it, or port the documented rules to another language.

## Rendering Guidance

Rich pets can map states to separate sprites or animations.

Single-image pets should use `presentation`:

- `motion`: idle, reading, typing, intense_typing, shake, settle.
- `tint`: neutral, focus, warm, hot, cool.
- `scale`: subtle size multiplier.
- `badge`: short overlay label.
- `bubble`: short text suitable for a speech bubble.
- `cadence_ms`: suggested animation/update cadence.

Keep state changes smooth. Respect `smoothing.changed`, `intensity`, and minimum dwell behavior from the engine output.
