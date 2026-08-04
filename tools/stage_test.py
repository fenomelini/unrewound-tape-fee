#!/usr/bin/env python3

import argparse
import hashlib
import json
import shutil
from pathlib import Path


VARIANTS = {
    "standalone": "zzzzzzzz_UnrewoundTapeFee_P.pak",
    "employee-fee-policy": "zzzzzzzz_UnrewoundTapeFee_EmployeeFeePolicy_P.pak",
}
EMPLOYEE_FEE_POLICY = "zzzzzzzz_EmployeeFeePolicy_P.pak"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    project_root = Path(__file__).resolve().parents[1]
    default_paks = (
        Path.home()
        / ".local/share/Steam/steamapps/common/RetroRewind"
        / "RetroRewind/Content/Paks"
    )
    parser = argparse.ArgumentParser(description="Stage an Unrewound Tape Fee in-game test")
    parser.add_argument("--variant", choices=VARIANTS, default="employee-fee-policy")
    parser.add_argument("--paks", type=Path, default=default_paks)
    parser.add_argument("--restore", action="store_true")
    args = parser.parse_args()

    mods = args.paks / "~mods"
    backup = args.paks / "~mods-disabled-unrewound-tape-fee-test"
    state_path = project_root / "dist/test-install.json"
    if not mods.is_dir():
        raise FileNotFoundError(f"mods directory not found: {mods}")

    if args.restore:
        state = json.loads(state_path.read_text(encoding="ascii"))
        installed = Path(state["installed"])
        restored = state_path.with_name(
            f"test-install.restored-{state['installed_sha256'][:12]}.json"
        )
        if not installed.is_file() or sha256(installed) != state["installed_sha256"]:
            raise ValueError(f"installed test PAK changed or is missing: {installed}")
        if restored.exists():
            raise FileExistsError(f"refusing to replace restore record: {restored}")
        for item in state["moved"]:
            source = Path(item["to"])
            destination = Path(item["from"])
            if destination.exists():
                raise FileExistsError(f"refusing to replace installed PAK: {destination}")
            if not source.is_file() or sha256(source) != item["sha256"]:
                raise ValueError(f"test backup changed or is missing: {source}")

        installed.unlink()
        for item in state["moved"]:
            source = Path(item["to"])
            destination = Path(item["from"])
            source.replace(destination)
            if sha256(destination) != item["sha256"]:
                raise ValueError(f"restored PAK verification failed: {destination}")
        state_path.replace(restored)
        print(json.dumps({"restored": state}, indent=2))
        return

    backup.mkdir(exist_ok=True)

    manifest_path = project_root / "dist/UnrewoundTapeFee.json"
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    selected = next(item for item in manifest["variants"] if item["variant"] == args.variant)
    source = project_root / "dist" / selected["pak"]
    if sha256(source) != selected["pak_sha256"]:
        raise ValueError(f"build hash mismatch: {source}")

    moved = []
    for filename in (EMPLOYEE_FEE_POLICY, *VARIANTS.values()):
        installed = mods / filename
        if not installed.exists():
            continue
        destination = backup / filename
        if destination.exists():
            raise FileExistsError(f"refusing to replace test backup: {destination}")
        before = sha256(installed)
        installed.replace(destination)
        if sha256(destination) != before:
            raise ValueError(f"backup verification failed: {destination}")
        moved.append({
            "from": str(installed),
            "to": str(destination),
            "sha256": before,
        })

    installed = mods / selected["pak"]
    shutil.copy2(source, installed)
    if sha256(installed) != selected["pak_sha256"]:
        raise ValueError(f"installed PAK verification failed: {installed}")

    state = {
        "variant": args.variant,
        "installed": str(installed),
        "installed_sha256": selected["pak_sha256"],
        "moved": moved,
    }
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="ascii")
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
