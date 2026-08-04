# Unrewound Tape Fee

Cooked gameplay mod for Retro Rewind - Video Store Simulator that adds the
missing fee for tapes returned without rewinding.

[Releases](https://github.com/fenomelini/unrewound-tape-fee/releases) |
[Source](https://github.com/fenomelini/unrewound-tape-fee) |
[Issues](https://github.com/fenomelini/unrewound-tape-fee/issues)

## Important: Employee Fee Policy

**Do not install this mod alongside `zzzzzzzz_EmployeeFeePolicy_P.pak`.** Both
mods replace `BTTask_Checkout-Fees`, so load order would silently discard part
of one mod.

Employee Fee Policy users must install only:

```text
zzzzzzzz_UnrewoundTapeFee_EmployeeFeePolicy_P.pak
```

That merged variant already incorporates the complete Employee Fee Policy
`1.0.0` behavior plus all Unrewound Tape Fee features. Remove the original
Employee Fee Policy PAK before installing it.

## Behavior

- Registers one vanilla `Fees.Rewind` entry when the drop-box scanner finds an
  unrewound tape.
- Displays and charges `$2` for that rewind fee.
- Shows a dedicated localized rewind-fee title and description instead of the
  vanilla `NOTSET` placeholders.
- Adds one checkout row for every pending rewind fee, including memberships
  that also have late or damaged-tape charges.
- Makes employees always answer and keep valid rewind charges, including
  employees with the Complaint Handler trait.
- Leaves vanilla late and damaged-tape policy unchanged in the standalone
  variant.
- Uses the game's original `RentSystem.Add Fees to Membership` and checkout
  flow for money, customer reactions, statistics, XP, inventory, and saves.

The mod does not edit money directly and does not require UE4SS.

## Localization

The checkout monitor uses dedicated translatable text identities and displays:

```text
Taxa de rebobinamento
A fita não foi rebobinada.
```

The vanilla rewind dialogue identity is also supplied because the game ships
the English source line but no localized resource entry. In Brazilian
Portuguese the customer says:

```text
E aí. O filme era tão bom que eu apaguei e esqueci de rebobinar. Por favor, mano.
```

Merged localization resources are included for German, Spanish, French,
Italian, Japanese, European Portuguese, Brazilian Portuguese, Russian,
Simplified Chinese, and Traditional Chinese. Each resource preserves every
vanilla and 18 Genres entry and adds two monitor identities plus the existing
vanilla dialogue identity. English uses the cooked source-text fallback and
does not override the English `Game.locres` supplied by the game or other mods.

## Variants

Install exactly one PAK:

- `zzzzzzzz_UnrewoundTapeFee_P.pak`: standalone rewind-fee behavior; vanilla
  late and damaged-tape employee decisions remain unchanged.
- `zzzzzzzz_UnrewoundTapeFee_EmployeeFeePolicy_P.pak`: the same rewind fee plus
  the complete Employee Fee Policy behavior, which always answers supported fee
  disputes and keeps valid late, damaged, and rewind charges.

The compatibility variant replaces
`zzzzzzzz_EmployeeFeePolicy_P.pak`. Do not install both because they override
the same `BTTask_Checkout-Fees` cooked asset.

## Requirements

- Retro Rewind Steam App ID `3552140`, build `23896268`.
- Unreal Engine `5.4.4` game assets.
- No UE4SS installation is required.

## Installation

1. Open the Retro Rewind installation directory in Steam.
2. Create `RetroRewind/Content/Paks/~mods` if it does not exist.
3. Place exactly one Unrewound Tape Fee PAK in `~mods`.
4. Remove the separate Employee Fee Policy PAK when using the merged variant.
5. Restart the game completely.

## Compatibility

Mods replacing any of these cooked assets conflict and require a merged PAK:

```text
RetroRewind/Content/VideoStore/asset/prop/DropBox/Scanner_Dropbox
RetroRewind/Content/VideoStore/asset/prop/CheckOut/UI_Screen_Checkout_Fees
RetroRewind/Content/VideoStore/core/ai/Task/BTTask_Checkout-Fees
```

Faster Returns does not currently package `Scanner_Dropbox`, so its released
PAK does not conflict with this scanner override. The combined automated return
and rewind workflow was tested in game.

## Build

The deterministic builder extracts six pinned source files from the installed
vanilla game PAK, applies guarded byte-level patches, and packs both variants as
PAK version V11:

```bash
python tools/build_mod.py
python -m unittest discover -s tests -v
python tools/verify_build.py
```

Set `RETRO_REWIND_PAK` or pass `--game-pak` when the game is installed in a
different location. The builder refuses source files from another build and
records all source, output, and PAK hashes in `dist/UnrewoundTapeFee.json`.
The localization merge uses the public
[18 Genres Universal Localization Fix](https://github.com/fenomelini/18-genres-localization-fix)
v1.0.0 PAK as its pinned base; pass its path with `--localization-base-pak`
when that repository is not beside this one in the workspace. The build also
requires the build-matched `.usmap`, .NET 8, and `repak` paths exposed by the
command-line options.

To stage the merged PAK for an in-game test while preserving an installed
Employee Fee Policy PAK in a separate backup directory:

```bash
python tools/stage_test.py --variant employee-fee-policy
```

Restore the exact pre-test PAK after testing:

```bash
python tools/stage_test.py --restore
```

## Validation Status

Offline validation covers source identity, package metadata, byte-diff
allowlists, control-flow relocation, localized-text identities, all 10 merged
localization resources, output hashes, PAK membership, and both
employee-policy variants.

The vanilla checkout builds rows only for late and damaged-tape fees, then
removes the complete membership fee record. The patched task adds the missing
counted rewind loop before that original removal, so mixed and accumulated
rewind charges are represented in the bill instead of being discarded.

The checkout patch preserves its `6020`-byte export and `3872`-byte serialized
script while recalculating the logical bytecode size to `2760`. All affected
jump, switch, and entry-point targets are guarded by the builder.

In-game validation on build `23896268` covered multiple store days, cold starts,
save/reload, automated Faster Returns scans, standalone and mixed fee records,
accumulated rewind counts, Employee Fee Policy behavior, the `$2` checkout row,
and Brazilian Portuguese monitor and dialogue text. The final source-preserving
scanner did not reproduce the undefined-opcode crash from an earlier discarded
serialization experiment.

## Uninstallation

Delete the installed Unrewound Tape Fee PAK and restart the game. The mod uses
the original fee and save systems and does not require a migration step.

## Version

`1.0.0`
