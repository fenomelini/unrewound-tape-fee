#!/usr/bin/env python3

import hashlib
import json
import zipfile
from pathlib import Path


VERSION = "1.0.0"
RELEASES = {
    "standalone": "Unrewound-Tape-Fee-1.0.0.zip",
    "employee-fee-policy": "Unrewound-Tape-Fee-Employee-Fee-Policy-1.0.0.zip",
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def zip_entry(archive, name, data):
    info = zipfile.ZipInfo(name, date_time=(2026, 8, 3, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main():
    project = Path(__file__).resolve().parents[1]
    dist = project / "dist"
    manifest_path = dist / "UnrewoundTapeFee.json"
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    if manifest["game_build"] != "23896268" or manifest["engine"] != "5.4.4":
        raise ValueError("unexpected build manifest target")

    outputs = []
    for variant in manifest["variants"]:
        name = variant["variant"]
        if name not in RELEASES:
            raise ValueError(f"unexpected release variant: {name}")
        pak = dist / variant["pak"]
        pak_data = pak.read_bytes()
        if sha256(pak_data) != variant["pak_sha256"]:
            raise ValueError(f"PAK hash mismatch: {pak.name}")
        zip_path = dist / RELEASES[name]
        with zipfile.ZipFile(zip_path, "w") as archive:
            zip_entry(archive, pak.name, pak_data)
            zip_entry(archive, "README.md", (project / "README.md").read_bytes())
            zip_entry(archive, "LICENSE", (project / "LICENSE").read_bytes())
        outputs.append({
            "variant": name,
            "zip": zip_path.name,
            "zip_sha256": sha256(zip_path.read_bytes()),
            "pak": pak.name,
            "pak_sha256": variant["pak_sha256"],
        })

    release = {
        "version": VERSION,
        "game_build": manifest["game_build"],
        "engine": manifest["engine"],
        "archives": outputs,
    }
    (dist / "Release.json").write_text(
        json.dumps(release, indent=2) + "\n",
        encoding="ascii",
    )
    print(json.dumps(release, indent=2))


if __name__ == "__main__":
    main()
