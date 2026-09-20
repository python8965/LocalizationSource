# KoreanPatch localisation project

This folder contains the reproducible localisation workflow for the WARNO KoreanPatch mod.

- `English/`: extracted English source snapshot. Keep separate and unchanged.
- `Translated/`: translation staging area; currently only the empty `Translations.csv` template.
- `Raw/`: retained official example source (`ExampleAssets_UNITS.csv`).
- `ExtractLocalisationCsv.py`: the only canonical extractor.
- `PROCESS.md`: full extraction, build, validation, and cleanup procedure.
- `External/`: optional WarnoModEditor source; it is not an extraction source.

The active WARNO files are under `../GameData/Localisation/KoreanPatch/`. Translation is not included yet. Do not use old cache files, synthetic TOKEN maps, or generated `HarvestedStrings.csv` files as source data.
