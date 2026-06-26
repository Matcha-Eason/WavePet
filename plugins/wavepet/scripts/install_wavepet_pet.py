#!/usr/bin/env python3
"""Install a packaged WavePet custom pet into the local Codex pets directory.

This script supports two sources:
1. An embedded packaged pet under plugins/wavepet/pets/<pet-id>/
2. A hatch-pet run directory with final/spritesheet.webp and pet_request.json
3. The official Rocky spritesheet extracted from the local Codex.app install
"""

from __future__ import annotations

import argparse
import json
import shutil
import struct
from pathlib import Path
from typing import Any


DEFAULT_PET_ID = "wavepet-rocky"
DEFAULT_DISPLAY_NAME = "WavePet Rocky"
DEFAULT_DESCRIPTION = (
    "A WavePet custom pet built from the local Codex official Rocky spritesheet "
    "with WavePet state-aware mapping."
)
DEFAULT_CODEX_APP = Path("/Applications/Codex.app")
ROCKY_ASSET_PREFIX = "webview/assets/rocky-spritesheet-v4-"
ROCKY_ASSET_SUFFIX = ".webp"

WAVEPET_STATE_MAP: dict[str, Any] = {
    "contract": "codex_pet_8x9_192x208",
    "source": "local_codex_official_rocky",
    "states": {
        "reading_understanding": {
            "atlas_row": 0,
            "codex_state": "idle",
            "motion": "reading",
            "tint": "cool",
            "cadence_ms": 900,
            "note": "Use Rocky's calm idle loop for low-pressure reading and context understanding.",
        },
        "steady_work": {
            "atlas_row": 7,
            "codex_state": "running",
            "motion": "typing",
            "tint": "neutral",
            "cadence_ms": 650,
            "note": "Use Rocky's laptop work loop for ordinary visible progress.",
        },
        "deep_output": {
            "atlas_row": 7,
            "codex_state": "running",
            "motion": "intense_typing",
            "tint": "focus",
            "cadence_ms": 420,
            "note": "Use the same laptop row with faster cadence and focus tint for long output or thinking.",
        },
        "overheat_debugging": {
            "atlas_row": 5,
            "codex_state": "failed",
            "motion": "shake",
            "tint": "hot",
            "cadence_ms": 320,
            "note": "Use Rocky's panic/failure row for errors, failed tests, and debugging pressure.",
        },
        "closing": {
            "atlas_row": 8,
            "codex_state": "review",
            "motion": "settle",
            "tint": "cool",
            "cadence_ms": 780,
            "note": "Use Rocky's friendly closing/review row for wrap-up and final response states.",
        },
    },
}


def build_manifest(pet_id: str, display_name: str, description: str) -> dict[str, str]:
    return {
        "id": pet_id,
        "displayName": display_name,
        "description": description,
        "spritesheetPath": "spritesheet.webp",
    }


def copy_packaged_pet(source_dir: Path, dest_dir: Path) -> None:
    pet_json = source_dir / "pet.json"
    spritesheet = source_dir / "spritesheet.webp"
    if not pet_json.exists() or not spritesheet.exists():
        raise FileNotFoundError(
            f"Packaged pet is incomplete under {source_dir}. Expected pet.json and spritesheet.webp."
        )
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(spritesheet, dest_dir / "spritesheet.webp")
    normalize_transparent_pixels(dest_dir / "spritesheet.webp")
    shutil.copy2(pet_json, dest_dir / "pet.json")
    state_map = source_dir / "wavepet-state-map.json"
    if state_map.exists():
        shutil.copy2(state_map, dest_dir / "wavepet-state-map.json")


def install_from_run(run_dir: Path, dest_dir: Path, pet_id: str) -> None:
    request_path = run_dir / "pet_request.json"
    spritesheet = run_dir / "final" / "spritesheet.webp"
    if not request_path.exists() or not spritesheet.exists():
        raise FileNotFoundError(
            f"Run directory {run_dir} is incomplete. Expected pet_request.json and final/spritesheet.webp."
        )

    request = json.loads(request_path.read_text(encoding="utf-8"))
    display_name = request.get("display_name") or DEFAULT_DISPLAY_NAME
    description = request.get("description") or DEFAULT_DESCRIPTION
    manifest = build_manifest(pet_id=pet_id, display_name=display_name, description=description)

    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(spritesheet, dest_dir / "spritesheet.webp")
    normalize_transparent_pixels(dest_dir / "spritesheet.webp")
    (dest_dir / "pet.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_state_map(dest_dir)


def iter_asar_files(node: dict[str, Any], prefix: str = "") -> list[tuple[str, dict[str, Any]]]:
    files = node.get("files")
    if not isinstance(files, dict):
        return [(prefix, node)]
    result: list[tuple[str, dict[str, Any]]] = []
    for name, child in files.items():
        child_path = f"{prefix}/{name}" if prefix else name
        result.extend(iter_asar_files(child, child_path))
    return result


def read_asar_header(asar_path: Path) -> tuple[dict[str, Any], int]:
    with asar_path.open("rb") as handle:
        header = handle.read(16)
        if len(header) != 16:
            raise ValueError(f"{asar_path} is not a valid asar file.")
        _, _, _, header_size = struct.unpack("<IIII", header)
        raw_header = handle.read(header_size)
    return json.loads(raw_header.decode("utf-8")), 16 + header_size


def extract_asar_file(asar_path: Path, asset_path: str, output_path: Path) -> None:
    header, content_start = read_asar_header(asar_path)
    node: dict[str, Any] = header
    for part in asset_path.split("/"):
        node = node["files"][part]
    size = int(node["size"])
    offset = int(node["offset"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with asar_path.open("rb") as handle:
        handle.seek(content_start + offset)
        data = handle.read(size)
    if len(data) != size:
        raise ValueError(f"Could not read complete asset {asset_path} from {asar_path}.")
    output_path.write_bytes(data)


def find_official_rocky_asset(codex_app: Path) -> tuple[Path, str]:
    asar_path = codex_app / "Contents" / "Resources" / "app.asar"
    if not asar_path.exists():
        raise FileNotFoundError(f"Codex app asar not found: {asar_path}")

    header, _ = read_asar_header(asar_path)
    matches = [
        path
        for path, node in iter_asar_files(header)
        if path.startswith(ROCKY_ASSET_PREFIX)
        and path.endswith(ROCKY_ASSET_SUFFIX)
        and isinstance(node.get("size"), int)
    ]
    if not matches:
        raise FileNotFoundError(f"No official Rocky spritesheet found in {asar_path}.")
    return asar_path, sorted(matches)[-1]


def write_state_map(dest_dir: Path) -> None:
    (dest_dir / "wavepet-state-map.json").write_text(
        json.dumps(WAVEPET_STATE_MAP, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def normalize_transparent_pixels(image_path: Path) -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is required to normalize the WavePet spritesheet: python3 -m pip install pillow") from exc

    image = Image.open(image_path).convert("RGBA")
    alpha = image.getchannel("A")
    transparent_mask = alpha.point(lambda value: 255 if value == 0 else 0)
    transparent_black = Image.new("RGBA", image.size, (0, 0, 0, 0))
    image.paste(transparent_black, mask=transparent_mask)
    image.save(image_path, "WEBP", lossless=True, exact=True, method=6)


def install_from_official_rocky(codex_app: Path, dest_dir: Path, pet_id: str) -> None:
    asar_path, asset_path = find_official_rocky_asset(codex_app)
    dest_dir.mkdir(parents=True, exist_ok=True)
    extract_asar_file(asar_path, asset_path, dest_dir / "spritesheet.webp")
    normalize_transparent_pixels(dest_dir / "spritesheet.webp")
    manifest = build_manifest(
        pet_id=pet_id,
        display_name=DEFAULT_DISPLAY_NAME,
        description=DEFAULT_DESCRIPTION,
    )
    (dest_dir / "pet.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_state_map(dest_dir)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    plugin_dir = script_dir.parent

    parser = argparse.ArgumentParser()
    parser.add_argument("--pet-id", default=DEFAULT_PET_ID)
    parser.add_argument("--run-dir", type=Path, help="Optional hatch-pet run directory to install from.")
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path.home() / ".codex",
        help="Codex home directory. Defaults to ~/.codex.",
    )
    parser.add_argument(
        "--codex-app",
        type=Path,
        default=DEFAULT_CODEX_APP,
        help="Codex.app path used to extract the official Rocky spritesheet when no packaged pet is embedded.",
    )
    parser.add_argument(
        "--no-official-rocky-fallback",
        action="store_true",
        help="Fail instead of extracting the local official Rocky spritesheet when the embedded pet package is absent.",
    )
    args = parser.parse_args()

    dest_dir = args.codex_home / "pets" / args.pet_id
    if args.run_dir:
        install_from_run(run_dir=args.run_dir, dest_dir=dest_dir, pet_id=args.pet_id)
    else:
        packaged_source = plugin_dir / "pets" / args.pet_id
        try:
            copy_packaged_pet(source_dir=packaged_source, dest_dir=dest_dir)
        except FileNotFoundError:
            if args.no_official_rocky_fallback:
                raise
            install_from_official_rocky(codex_app=args.codex_app, dest_dir=dest_dir, pet_id=args.pet_id)

    print(json.dumps({"ok": True, "pet_id": args.pet_id, "installed_to": str(dest_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
