# Changelog

## 1.0.0 - 2026-08-03

- Register rewind fees through the vanilla membership fee system.
- Set the rewind fee to `$2`.
- Replace the rewind monitor's `NOTSET` placeholders with a dedicated title and
  description localized for all supported game cultures.
- Correct every logical bytecode target affected by the localized text
  expressions so the checkout widget passes Unreal's cold-start serial-size
  validation.
- Add the missing counted rewind-fee rows to checkout so mixed late, damaged,
  and rewind records are all billed before vanilla removes the membership fee
  record.
- Merge the rewind title and description into the culture-specific
  `Game.locres` resources after confirming Unreal does not discover an
  arbitrarily named supplemental locres in this localization target.
- Add the missing localized resource entry for the vanilla rewind dialogue in
  every supported non-English culture.
- Make employees always answer and keep rewind charges.
- Add a merged Employee Fee Policy variant.
- Add deterministic source-preserving patch, test, and V11 packaging tools.
