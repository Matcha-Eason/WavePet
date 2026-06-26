# WavePet

WavePet is a Codex plugin and skill for turning live Codex activity into desktop-pet state JSON.

It focuses on user-perceived waiting experience: whether Codex appears to be reading, steadily working, producing a long answer, debugging under pressure, or wrapping up.

## Capabilities

- Online tracking from streaming assistant tokens, thinking tokens, tool events, edits, tests, errors, and idle ticks.
- Lightweight near-term state prediction through current output load, thinking load, feedback pressure, error pressure, and smoothing.
- Five desktop-pet states: reading, steady work, deep output, overheat debugging, and closing.
- Presentation hints for rich animated pets and single-image pets: motion, tint, scale, badge, bubble text, and animation cadence.
- A dependency-free Python runtime that can be embedded in another desktop-pet renderer.

## States

| State | Meaning |
|---|---|
| `reading_understanding` | Early low-pressure reading or context understanding |
| `steady_work` | Normal progress without strong waiting pressure |
| `deep_output` | Long output, long thinking, or long silent work |
| `overheat_debugging` | Errors, failed tests, repeated validation, or heavy logs |
| `closing` | Completion, summary, or wrap-up |

## Quick Test

```bash
python3 scripts/pet_state_engine.py --demo
python3 scripts/pet_state_engine.py --events examples/sample_events.jsonl
python3 scripts/pet_state_bridge.py --demo --history
python3 scripts/install_wavepet_pet.py --run-dir ../../dist/wavepet-rocky-run
python3 -m unittest discover -s tests -v
python3 -m http.server 8787 --directory examples/local_pet_demo
```

Each input event produces one JSON state.

## Codex Integration

This folder is a Codex plugin. For GitHub publishing, keep it as:

```text
plugins/wavepet
```

The plugin manifest is:

```text
.codex-plugin/plugin.json
```

The skill entry is:

```text
skills/wavepet/SKILL.md
```

## Custom Pet Install

WavePet can also install a custom Codex pet package that maps WavePet states onto the current local Codex Rocky pet.

By default, the installer does not redistribute Codex's official Rocky artwork inside this repository. If an embedded `pets/wavepet-rocky/` package is not present, it extracts the official Rocky spritesheet from the user's local `/Applications/Codex.app/Contents/Resources/app.asar`, writes a standard Codex custom pet package, and adds `wavepet-state-map.json` with the WavePet-to-Rocky animation mapping.

Default behavior after plugin install:

- Existing Rocky frames are mapped onto WavePet states without generating new artwork.
- `reading_understanding` uses Rocky idle.
- `steady_work` and `deep_output` use Rocky work/laptop frames with different cadence.
- `overheat_debugging` uses Rocky failed/panic frames.
- `closing` uses Rocky review/closing frames.

Recommended next step:

Use the WavePet skill together with the official `hatch-pet` workflow to create truly new state-specific assets, then install the completed hatch-pet run with `--run-dir`. This is better for a polished release pet because it can add distinct visuals for deep output, red-temperature debugging pressure, and closing instead of only reusing existing Rocky rows.

Install from the current local Codex official Rocky asset:

```bash
python3 -m pip install pillow
python3 plugins/wavepet/scripts/install_wavepet_pet.py
```

Install from a completed hatch-pet run after generating new state assets:

```bash
python3 plugins/wavepet/scripts/install_wavepet_pet.py \
  --run-dir dist/wavepet-rocky-run
```

This writes the pet package to:

```text
~/.codex/pets/wavepet-rocky/
```

The installed package contains `pet.json`, `spritesheet.webp`, and `wavepet-state-map.json`. If `plugins/wavepet/pets/wavepet-rocky/pet.json` and `spritesheet.webp` are embedded later, the same installer will use that packaged pet before falling back to local official Rocky extraction.

## Single-Image Pet Compatibility

Renderers do not need separate images for every state. Use the output `presentation` object:

- `motion`: reading, typing, intense typing, shake, or settle.
- `tint`: neutral, focus, warm, hot, or cool overlay.
- `scale`: subtle size multiplier.
- `badge`: compact status label.
- `bubble`: optional speech bubble text.
- `cadence_ms`: suggested animation speed.

See `examples/single_image_renderer_mapping.json` and `examples/bsod_renderer_mapping.json` for concrete renderer mappings.

## Research Basis

WavePet was derived from a CoderForge trajectory experiment. In the current waiting-experience experiment, current state recognition improved from macro F1 0.785 with history-only features to 0.904 when current streaming tokens were included. This supports using historical inertia plus live output signals for online pet-state tracking.
