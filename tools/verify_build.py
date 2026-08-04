#!/usr/bin/env python3

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    project_root = Path(__file__).resolve().parents[1]
    workspace_root = project_root.parent
    parser = argparse.ArgumentParser(description="Verify built Unrewound Tape Fee PAKs")
    parser.add_argument("--dist", type=Path, default=project_root / "dist")
    parser.add_argument(
        "--repak",
        type=Path,
        default=workspace_root / "fast-customer-turns/tools/repak/repak_cli-x86_64-unknown-linux-gnu/repak",
    )
    parser.add_argument(
        "--dotnet",
        type=Path,
        default=workspace_root / "fast-customer-turns/tools/dotnet/dotnet",
    )
    parser.add_argument(
        "--uasset-dump",
        type=Path,
        default=(
            workspace_root
            / "fast-customer-turns/tools/UAssetDump/bin/Debug/net8.0/UAssetDump.dll"
        ),
    )
    parser.add_argument(
        "--usmap",
        type=Path,
        default=(
            Path.home()
            / ".local/share/Steam/steamapps/common/RetroRewind/RetroRewind/Binaries/Win64/ue4ss"
            / "RetroRewind-5.4.4-35576357+++UE5+Release-5.4-0196ef29.usmap"
        ),
    )
    args = parser.parse_args()

    manifest_path = args.dist / "UnrewoundTapeFee.json"
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    if manifest["game_build"] != "23896268" or manifest["engine"] != "5.4.4":
        raise ValueError("manifest targets an unexpected game build")
    for required in (args.repak, args.dotnet, args.uasset_dump, args.usmap):
        if not required.is_file():
            raise FileNotFoundError(required)

    results = []
    with tempfile.TemporaryDirectory(prefix="unrewound-tape-fee-verify-") as directory:
        root = Path(directory)
        for variant in manifest["variants"]:
            pak = args.dist / variant["pak"]
            if sha256(pak) != variant["pak_sha256"]:
                raise ValueError(f"PAK hash mismatch: {pak.name}")
            output = root / variant["variant"]
            subprocess.run(
                [str(args.repak), "unpack", "-q", "-o", str(output), str(pak)],
                check=True,
            )
            members = sorted(
                path.relative_to(output).as_posix()
                for path in output.rglob("*")
                if path.is_file()
            )
            if members != variant["members"]:
                raise ValueError(f"unpacked membership mismatch: {pak.name}")
            for member, expected in variant["output_hashes"].items():
                path = output / member
                if sha256(path) != expected:
                    raise ValueError(f"unpacked hash mismatch: {pak.name}/{member}")

            inspection = root / f"{variant['variant']}-inspection"
            inspection.mkdir()
            for member in variant["members"]:
                if not member.endswith(".uasset"):
                    continue
                source = output / member
                target = inspection / (source.stem + ".json")
                subprocess.run(
                    [
                        str(args.dotnet),
                        str(args.uasset_dump),
                        str(source),
                        str(target),
                        str(args.usmap),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                )
                decoded = json.loads(target.read_text(encoding="utf-8-sig"))
                if not isinstance(decoded.get("Exports"), list) or not decoded["Exports"]:
                    raise ValueError(f"asset inspection has no exports: {member}")
                if source.stem == "UI_Screen_Checkout_Fees":
                    serialized = json.dumps(decoded, ensure_ascii=False)
                    for expected, count in (
                        ("UnrewoundTapeFeeUI", 2),
                        ("UI_Screen_Checkout_Fees_ErrorType2_Title", 1),
                        ("ErrorType2_DescKey", 1),
                    ):
                        if serialized.count(expected) != count:
                            raise ValueError(
                                f"checkout localized text identity mismatch: {expected}"
                            )
            results.append({
                "variant": variant["variant"],
                "pak_sha256": variant["pak_sha256"],
                "members_verified": len(members),
                "assets_inspected": sum(member.endswith(".uasset") for member in members),
            })

    print(json.dumps({"verified": results}, indent=2))


if __name__ == "__main__":
    main()
