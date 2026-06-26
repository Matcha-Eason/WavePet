# WavePet Rocky Pet Package

This directory is reserved for an optional packaged WavePet Rocky custom pet.

The default install flow intentionally does not vendor Codex's official Rocky artwork in this repository. When `pet.json` and `spritesheet.webp` are absent, `scripts/install_wavepet_pet.py` extracts the current official Rocky spritesheet from the user's local Codex app bundle and writes the installed package under `~/.codex/pets/wavepet-rocky/`.

Expected files:

- `pet.json`
- `spritesheet.webp`
- `wavepet-state-map.json`

Default local install from the current Codex official Rocky asset:

```bash
python3 plugins/wavepet/scripts/install_wavepet_pet.py
```

During development, the authoritative image-generation workflow is the hatch-pet run under `dist/wavepet-rocky-run/`.

To install directly from a completed hatch-pet run instead of an embedded package:

```bash
python3 plugins/wavepet/scripts/install_wavepet_pet.py \
  --run-dir dist/wavepet-rocky-run
```
