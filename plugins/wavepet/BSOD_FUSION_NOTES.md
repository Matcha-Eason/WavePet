# Codex BSOD Pet Fusion Notes

Date: 2026-06-24

## What Was Found

The installed Codex app contains official pet/avatar-related resources:

```text
/Applications/Codex.app/Contents/Resources/owl-electron-app.json
/Applications/Codex.app/Contents/Resources/native/avatar-overlay.node
```

The app bundle also contains pet-related code paths, including settings and install logic for avatar/pet spritesheets. The local feature cache currently shows:

```json
{"enabledOwlFeatureNames":[]}
```

This suggests Owl/pet capability is gated by app-side feature flags and internal runtime state.

## Current Limitation

No documented local API or obvious IPC/file input was found for directly pushing external state into the official BSOD pet. The Codex app owns its avatar overlay runtime. The `wavepet` plugin is installed and valid, but plugin state JSON is not automatically consumed by the official pet unless Codex exposes a hook.

## Bridge Implemented

Added:

```text
scripts/pet_state_bridge.py
```

It converts event JSONL into latest pet state and writes:

```text
~/Library/Application Support/Codex/wavepet/current_state.json
```

Optional history:

```text
~/Library/Application Support/Codex/wavepet/state_history.jsonl
```

Run:

```bash
python3 scripts/pet_state_bridge.py --demo --history
python3 scripts/pet_state_bridge.py --events examples/sample_events.jsonl --history
```

## Fusion Result

The bridge successfully writes state JSON in a Codex-readable application support directory. This is a working adapter boundary for:

- a future official pet file hook,
- a native sidecar overlay,
- or a custom renderer that mirrors the official BSOD pet behavior.

It does not yet force the official BSOD pet itself to animate by our state, because no public ingestion path has been identified.

## Recommended Next Step

If the official pet has a hidden developer setting or an internal route for state injection, wire that route to:

```text
~/Library/Application Support/Codex/wavepet/current_state.json
```

Otherwise, use the state bridge with a sidecar renderer until Codex exposes a supported pet-state API.
