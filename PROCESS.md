# WARNO KoreanPatch localisation workflow

## Canonical files

- Extractor: `Mods/KoreanPatch/LocalizationSource/ExtractLocalisationCsv.py`
- English source snapshot: `English/`
- Translation staging: `Translated/COMPANIES.csv`, `Translated/PLATOONS.csv`, `Translated/UNITS.csv`, `Translated/INTERFACE_INGAME.csv`, and `Translated/INTERFACE_OUTGAME.csv`
- Active WARNO pack: `../GameData/Localisation/KoreanPatch/`
- Official example source retained: `Raw/ExampleAssets_UNITS.csv`

The source snapshot is kept separate from the active mod. Do not translate or overwrite `English/`.

## Extraction method

1. Read the text NDF files from `Mods/KoreanPatch/base.zip` (4,564 files). This is the authoritative token source available in the installed toolkit.
2. Read exact localisation fields such as `TextToken`, `HintBodyToken`, and `NameToken` for UI and unit dictionaries.
3. Read `GameData/Generated/Gameplay/Decks/StrategicCombatGroups.ndf` directly:
   - `TDeckCombatGroupDescriptor.Name` -> `COMPANIES`
   - `TDeckSmartGroupDescriptor.Name` -> `PLATOONS`
4. Unpack the vanilla language archives and use only `Localisation/US/.../*.dic` as the English source. Never use `Localisation/DEV` for English; DEV is not the English language pack.
5. Use one WARNO generation as a hash oracle to join those exact tokens to the US English strings.
6. Never invent a TOKEN. Unmatched `.dic` entries stay unresolved and are reported as `INCOMPLETE`.

The extractor does not persist a cache. It uses fresh NDF, WARNO generation, and DataPacker output on every run. Run WARNO only when it is not already running:

```powershell
python Mods\KoreanPatch\LocalizationSource\ExtractLocalisationCsv.py --mod-name KoreanPatch
```

## Current last extraction

- UNITS: 9,166 rows
- INTERFACE_INGAME: 655 rows
- INTERFACE_OUTGAME: 534 rows
- COMPANIES: 9,342 rows
- PLATOONS: 8,043 rows

The report is `English/EXTRACTION_REPORT.txt`. These are exact matched rows, not fabricated completion; unresolved DIC entries are listed there.

## Build and translation

1. Copy reviewed English CSVs from `English/` to `../GameData/Localisation/KoreanPatch/`.
2. Keep `Translations.csv` at `../GameData/Localisation/Database/Translations.csv` with four columns: `TOKEN;LANG;REFTEXT;TEXT`.
3. Translate only the copies in `Translated/`; never edit `English/`. Preserve TOKEN rows and placeholders/markup. The current pass is direct, context-aware Korean authored for WARNO; no Google, Argos, or other external/local translation engine is used.
4. Copy the five reviewed CSVs into the active mod.
5. Keep `Translations.csv` as the four-column database header unless explicit language mapping is needed.
6. Run `GenerateMod.bat` from `Mods/KoreanPatch` (or the equivalent `GenerateMod.py` command) after changes.
7. Test with `Text = US` and `ActivatedMods = KoreanPatch`; check main menu, tactical battle UI, Army General company/platoon screens, and armory. WARNO must not already be running when launching a test instance.

## Cleanup policy

Persistent extraction caches and DataPacker output are not project sources and should be removed after a run. The active `Gen/` output is kept because it is the generated mod result. The legacy script under `Mods/Utils/Scripts/ExtractLocalisationCsv.py` is not the canonical project extractor; use the copy in this folder.
