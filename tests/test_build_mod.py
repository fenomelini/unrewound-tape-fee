import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_mod", ROOT / "tools/build_mod.py")
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class PatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        workspace = ROOT.parent
        repak = workspace / "fast-customer-turns/tools/repak/repak_cli-x86_64-unknown-linux-gnu/repak"
        game_pak = (
            Path.home()
            / ".local/share/Steam/steamapps/common/RetroRewind"
            / "RetroRewind/Content/Paks/RetroRewind-Windows.pak"
        )
        if not repak.is_file() or not game_pak.is_file():
            raise unittest.SkipTest("build-matched game PAK or repak is unavailable")
        cls.sources = BUILD.extract_sources(repak, game_pak)
        cls.repak = repak
        cls.localization_base = (
            workspace
            / "18-genres-localization-fix/dist/zzzzzzzz_18Genres_L10N_Fix_P.pak"
        )
        dotnet = workspace / "fast-customer-turns/tools/dotnet/dotnet"
        usmap = (
            Path.home()
            / ".local/share/Steam/steamapps/common/RetroRewind/RetroRewind/Binaries/Win64/ue4ss"
            / "RetroRewind-5.4.4-35576357+++UE5+Release-5.4-0196ef29.usmap"
        )
        patcher = ROOT / "tools/FeeTaskPatcher/FeeTaskPatcher.csproj"
        if not dotnet.is_file() or not usmap.is_file():
            raise unittest.SkipTest(".NET or build-matched mappings are unavailable")
        cls.fee_task = BUILD.build_fee_task_structure(
            dotnet,
            patcher,
            usmap,
            cls.sources[BUILD.FEE_TASK.with_suffix(".uasset")],
            cls.sources[BUILD.FEE_TASK.with_suffix(".uexp")],
        )

    def test_scanner_splice_matches_pinned_output(self):
        uasset, uexp = BUILD.patch_scanner(
            self.sources[BUILD.SCANNER.with_suffix(".uasset")],
            self.sources[BUILD.SCANNER.with_suffix(".uexp")],
        )
        self.assertEqual(BUILD.SCANNER_OUTPUT["uasset"], BUILD.sha256(uasset))
        self.assertEqual(BUILD.SCANNER_OUTPUT["uexp"], BUILD.sha256(uexp))
        self.assertEqual(2224, BUILD.read_int(uexp, 0x2621))
        self.assertEqual(3164, BUILD.read_int(uexp, 0x2625))
        self.assertEqual(1, BUILD.read_int(uexp, 0x2CC2))

    def test_checkout_text_and_price_are_complete(self):
        source = self.sources[BUILD.CHECKOUT.with_suffix(".uexp")]
        uasset, uexp = BUILD.patch_checkout(
            self.sources[BUILD.CHECKOUT.with_suffix(".uasset")], source
        )
        self.assertEqual(self.sources[BUILD.CHECKOUT.with_suffix(".uasset")], uasset)
        self.assertEqual(2.0, __import__("struct").unpack_from("<d", uexp, 0x168D)[0])
        self.assertEqual(2760, BUILD.read_int(uexp, 0x09D4))
        self.assertEqual(3872, BUILD.read_int(uexp, 0x09D8))
        self.assertEqual(2757, BUILD.read_int(uexp, 0x0D8C))
        self.assertEqual(2609, BUILD.read_int(uexp, 0x1CAE))
        for text in BUILD.LOCALIZED_TEXTS.values():
            expected = BUILD.localized_text_expression(text["source"], text["key"])
            self.assertEqual(expected, uexp[text["offset"]:text["offset"] + len(expected)])
        self.assertEqual(BUILD.CHECKOUT_OUTPUT_UEXP, BUILD.sha256(uexp))

    def test_merged_localizations_cover_every_non_english_culture(self):
        outputs = BUILD.build_localizations(self.repak, self.localization_base)
        self.assertEqual(set(BUILD.TRANSLATIONS) - {"en"}, {path.parent.name for path in outputs})
        for path, data in outputs.items():
            resource = BUILD.parse_locres(data)
            namespaces = [
                item for item in resource["namespaces"]
                if item["namespace"] == BUILD.LOCALIZATION_NAMESPACE
            ]
            self.assertEqual(1, len(namespaces))
            self.assertEqual(2, len(namespaces[0]["entries"]))
            entries = BUILD.locres_entries(resource)
            dialogue_identity = (
                BUILD.DIALOGUE_TEXT["namespace"],
                BUILD.DIALOGUE_TEXT["key"],
            )
            self.assertEqual(
                (
                    BUILD.DIALOGUE_TEXT["source_hash"],
                    BUILD.DIALOGUE_TRANSLATIONS[path.parent.name],
                ),
                entries[dialogue_identity],
            )
            self.assertEqual("Game.locres", path.name)
            self.assertEqual(data, BUILD.serialize_locres(resource), path)

    def test_standalone_changes_only_rewind_decisions(self):
        source = self.fee_task[1]
        _, uexp, changes = BUILD.patch_fee_task(
            self.fee_task[0], source, "standalone"
        )
        self.assertEqual(BUILD.FEE_TASK_OUTPUT["standalone"], BUILD.sha256(uexp))
        self.assertEqual(3, len(changes))
        for offset in (0xB76E, 0xC490, 0xC613):
            self.assertEqual(BUILD.ALWAYS, uexp[offset:offset + 4])
        for offset in (0xB6F9, 0xB747, 0xC41B, 0xC59E, 0xC469, 0xC5EC):
            self.assertEqual(source[offset:offset + 4], uexp[offset:offset + 4])

    def test_merged_variant_preserves_employee_fee_policy(self):
        source = self.fee_task[1]
        _, uexp, _ = BUILD.patch_fee_task(
            self.fee_task[0],
            source,
            "employee-fee-policy",
        )
        self.assertEqual(BUILD.FEE_TASK_OUTPUT["employee-fee-policy"], BUILD.sha256(uexp))
        for offset, _, _ in BUILD.ANSWER_SITES:
            self.assertEqual(BUILD.ALWAYS, uexp[offset:offset + 4])
        for sites in BUILD.CHARGE_SITES.values():
            for offset, _, _ in sites:
                self.assertEqual(BUILD.ALWAYS, uexp[offset:offset + 4])


if __name__ == "__main__":
    unittest.main()
