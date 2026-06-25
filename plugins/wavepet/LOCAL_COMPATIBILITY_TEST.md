# Local Compatibility Test

Date: 2026-06-24

## Installation

Installed the plugin into the personal Codex plugin directory:

```text
/Users/gyc/plugins/wavepet
```

Registered it in the personal marketplace:

```text
/Users/gyc/.agents/plugins/marketplace.json
```

Marketplace entry:

```json
{
  "name": "wavepet",
  "source": {
    "source": "local",
    "path": "./plugins/wavepet"
  },
  "policy": {
    "installation": "AVAILABLE",
    "authentication": "ON_INSTALL"
  },
  "category": "Productivity"
}
```

## Local Demo

Started a local single-image pet compatibility demo:

```text
http://127.0.0.1:8787/
```

Demo file:

```text
plugins/wavepet/examples/local_pet_demo/index.html
```

The page renders one static pet image and drives it only through:

- `presentation.motion`
- `presentation.tint`
- `presentation.scale`
- `presentation.badge`
- `presentation.bubble`
- `presentation.cadence_ms`

This verifies compatibility with desktop pets that do not provide separate images for every state.

## Visual Check

Observed in Chrome:

- Initial state: `读题理解 / reading_understanding`
- Initial bubble: `我先看看...`
- Initial badge: `读题`
- After playback: `红温调试 / overheat_debugging`
- Overheat bubble: `压力上来了`
- Overheat badge: `调试`
- Overheat presentation: `motion=shake`, `tint=hot`, `scale=1.08`

No layout-breaking overlap was observed in the desktop viewport. The demo remains usable with a single image.

## Performance

State engine throughput test:

```text
events: 5000
outputs: 5000
seconds: 0.1619
events_per_second: 30880.3
last_state: overheat_debugging
```

The state engine is far above the expected desktop-pet event rate. A realistic renderer update loop at 500-1000 ms per tick should not be bottlenecked by the state engine.

## Validation

Commands run:

```bash
/opt/miniconda3/bin/python /Users/gyc/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py /Users/gyc/plugins/wavepet
/opt/miniconda3/bin/python /Users/gyc/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/gyc/plugins/wavepet/skills/wavepet
python3 /Users/gyc/plugins/wavepet/scripts/pet_state_engine.py --events /Users/gyc/plugins/wavepet/examples/sample_events.jsonl
python3 -m unittest discover -s plugins/wavepet/tests -v
```

Results:

```text
Plugin validation passed
Skill is valid
3 unit tests passed
sample_events.jsonl produced valid state JSON
```

## Current Limitation

This is a local compatibility demo, not a full native floating desktop-pet app. It verifies the state interface and one-image rendering strategy. A native pet shell can consume the same JSON and map the `presentation` object to its own rendering system.
