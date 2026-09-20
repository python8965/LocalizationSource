#!/usr/bin/env python3
"""Recover vanilla WARNO localisation dictionaries as mod CSV files.

The game ships compiled TRAD (.dic) dictionaries.  Their token names are
hashed, so simply unpacking a .dic cannot produce a usable CSV.  This tool
collects token references from the text NDF files, compiles a temporary CSV
containing unique marker strings with the official mod generator, and uses
the resulting hash/marker pairs to join the vanilla English .dic values back
to TOKEN names.

Only dictionaries with recovered, non-empty rows are written.  Unresolved
hashes are reported and never assigned fabricated token names.
"""

import argparse
import csv
import os
import re
import shutil
import struct
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


TOKEN_FIELDS = re.compile(
    r"\b(?P<field>(?!(?:[A-Za-z0-9_]*(?:Color|Texture|Typeface|Size|Thickness|Background|Border|Icon|Dico)Token)\b)(?:(?:Name|Text|Title|Description|Hint|Tooltip|Company|Platoon|Briefing|Summary|History|WeaponDescription|SpecialtyHint|TraitHint|Header|Body|Localization)[A-Za-z0-9_]*)Token)\s*=\s*(['\"])(?P<token>[^'\"]+)\2"
)
DICO_RE = re.compile(r"dico_(interface_ingame|interface_outgame|units|companies|platoons)", re.I)
VALID_TOKEN = re.compile(r"^[A-Za-z0-9_#./-]{1,10}$")


def run(cmd: List[str], cwd: Path, log: Optional[Path] = None, allow_failure: bool = False) -> None:
    if log:
        with log.open("ab") as stream:
            subprocess.run(cmd, cwd=str(cwd), stdout=stream, stderr=subprocess.STDOUT, check=not allow_failure)
    else:
        subprocess.run(cmd, cwd=str(cwd), check=not allow_failure)


def iter_ndf_sources(mod_root: Path):
    """Yield the game's text NDF sources, preferring the complete base.zip."""
    seen = set()
    base_zip = mod_root / "base.zip"
    if base_zip.exists():
        with zipfile.ZipFile(str(base_zip)) as archive:
            for name in archive.namelist():
                if not name.lower().endswith(".ndf"):
                    continue
                rel = name.replace("\\", "/").lower()
                seen.add(rel)
                yield rel, archive.read(name).decode("utf-8", errors="ignore")
    paths = list((mod_root / "GameData").rglob("*.ndf")) + list((mod_root / "CommonData").rglob("*.ndf"))
    for path in paths:
        rel = str(path.relative_to(mod_root)).replace("\\", "/").lower()
        if rel not in seen:
            yield rel, path.read_text(encoding="utf-8", errors="ignore")


def collect_tokens(mod_root: Path) -> Dict[str, Set[str]]:
    result = {"UNITS": set(), "INTERFACE_INGAME": set(), "INTERFACE_OUTGAME": set(), "COMPANIES": set(), "PLATOONS": set()}
    # Eugen's shipped ExampleAssets contains the complete public UNITS token list.
    example_units = mod_root.parent / "ExampleAssets" / "Localisation" / "UNITS.csv"
    if example_units.exists():
        with example_units.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.reader(stream, delimiter=";"):
                if row and row[0] != "TOKEN" and VALID_TOKEN.match(row[0]):
                    result["UNITS"].add(row[0])

    for rel, text in iter_ndf_sources(mod_root):
        # Army General names are plain Name fields inside these typed descriptors,
        # not *Token fields.  These are exact game TOKEN references.
        if rel.endswith("/strategiccombatgroups.ndf"):
            result["COMPANIES"].update(
                token[1] for token in re.findall(
                    r"TDeckCombatGroupDescriptor\s*\(\s*Name\s*=\s*([\"'])([^\"']+)\1",
                    text,
                    re.S,
                )
                if VALID_TOKEN.match(token[1])
            )
            result["PLATOONS"].update(
                token[1] for token in re.findall(
                    r"TDeckSmartGroupDescriptor\s*\(\s*Name\s*=\s*([\"'])([^\"']+)\1",
                    text,
                    re.S,
                )
                if VALID_TOKEN.match(token[1])
            )

        for match in TOKEN_FIELDS.finditer(text):
            token = match.group("token")
            if not VALID_TOKEN.match(token):
                continue
            field = match.group("field").lower()
            window = text[max(0, match.start() - 1600):match.start()]
            dico_match = list(DICO_RE.finditer(window))
            dico = dico_match[-1].group(1).upper() if dico_match else None
            if ("generated/gameplay/gfx" in rel or "generated/gameplay/unit" in rel or "unitnames" in rel or "ammunition" in rel):
                result["UNITS"].add(token)
                continue
            if "company" in field:
                result["COMPANIES"].add(token)
            elif "platoon" in field:
                result["PLATOONS"].add(token)
            elif dico == "UNITS":
                result["UNITS"].add(token)
            elif dico == "INTERFACE_INGAME":
                result["INTERFACE_INGAME"].add(token)
            elif dico == "INTERFACE_OUTGAME":
                result["INTERFACE_OUTGAME"].add(token)
            elif any(key in field for key in ("name", "description", "weapon", "summary", "history")) and ("gameplay" in rel or "unit" in rel):
                result["UNITS"].add(token)
            else:
                result["INTERFACE_OUTGAME"].add(token)
    return result

def parse_dic(path: Path) -> List[Tuple[str, str]]:
    data = path.read_bytes()
    if data[:4] != b"TRAD":
        raise ValueError(f"Not a TRAD dictionary: {path}")
    count = struct.unpack_from("<I", data, 4)[0]
    table_end = 8 + count * 16
    entries = []
    for i in range(count):
        pos = 8 + i * 16
        digest = data[pos:pos + 8].hex()
        offset, length = struct.unpack_from("<II", data, pos + 8)
        start = offset
        raw = data[start:start + length * 2]
        entries.append((digest, raw.decode("utf-16-le", errors="replace")))
    return entries


def write_csv(path: Path, rows: List[Tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter=";", quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writerow(("TOKEN", "REFTEXT"))
        writer.writerows(rows)


def locate_vanilla_dats(game_root: Path, data_packer: Path) -> List[Path]:
    candidates = list((game_root / "Data" / "PC").rglob("ZZ_1.dat"))
    selected = []
    for path in candidates:
        probe = subprocess.run([str(data_packer), "-y", "unpack", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if "Localisation/DEV" in probe.stdout or "Localisation/DEV" in probe.stderr:
            selected.append(path)
    def version_key(path: Path):
        return tuple(int(x) for x in re.findall(r"\d+", str(path)))
    return sorted(selected, key=version_key)
def locate_dic(root: Path, stem: str) -> Path:
    exact = [p for p in root.rglob("*.dic") if p.name.lower() == stem.lower()]
    matches = exact or [p for p in root.rglob("*.dic") if p.name.lower().startswith(Path(stem).stem.lower())]
    if not matches:
        raise FileNotFoundError(f"Could not locate extracted {stem}")
    return max(matches, key=lambda p: p.stat().st_size)


def locate_us_dic(root: Path, stem: str) -> Path:
    """Locate the vanilla English dictionary, never the DEV dictionary."""
    us = [
        p for p in root.rglob("*.dic")
        if p.name.lower() == stem.lower()
        and any(part.lower() == "us" for part in p.parts)
    ]
    if us:
        return max(us, key=lambda p: p.stat().st_size)
    raise FileNotFoundError(f"Could not locate vanilla US dictionary {stem}")


def infer_game_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here.parent, *here.parents):
        if (candidate / "Data" / "PC").exists() and (candidate / "Mods").exists():
            return candidate
    return here.parents[3]

def extract_csvs(output_root: Path, generated: Path, vanilla: Path, marker_to_token: Dict[str, Dict[str, str]], dic_names: Dict[str, str]) -> List[str]:
    report = []
    for category, dic_name in dic_names.items():
        compiled = locate_dic(generated, dic_name)
        vanilla_dic = locate_us_dic(vanilla, dic_name)
        compiled_entries = parse_dic(compiled)
        vanilla_entries = parse_dic(vanilla_dic)
        hash_to_token = {}
        for digest, string in compiled_entries:
            token = marker_to_token.get(category, {}).get(string)
            if token:
                hash_to_token[digest] = token
        rows = []
        unresolved = 0
        unresolved_nonempty = 0
        unresolved_rows = []
        matched_tokens = set()
        for digest, english in vanilla_entries:
            token = hash_to_token.get(digest)
            if token is None:
                unresolved += 1
                if english:
                    unresolved_nonempty += 1
                unresolved_rows.append((digest, english))
                continue
            if english:
                rows.append((token, english))
                matched_tokens.add(token)
        rows.sort(key=lambda row: row[0])
        if rows:
            write_csv(output_root / f"{category}.csv", rows)
        write_csv(output_root / f"UNRESOLVED_{category}.csv", unresolved_rows)
        unused_tokens = sorted(set(marker_to_token.get(category, {}).values()) - matched_tokens)
        (output_root / f"UNMATCHED_TOKENS_{category}.txt").write_text(
            "\n".join(unused_tokens) + ("\n" if unused_tokens else ""), encoding="utf-8"
        )
        total = len(vanilla_entries)
        nonempty = sum(1 for _digest, english in vanilla_entries if english)
        coverage = "OK" if len(rows) == nonempty and unresolved == 0 else "INCOMPLETE"
        empty_unresolved = unresolved - unresolved_nonempty
        report.append(
            f"{category}: {len(rows)} rows / {total} DIC entries ({nonempty} nonempty), "
            f"{unresolved} unresolved ({unresolved_nonempty} nonempty, {empty_unresolved} empty), "
            f"{len(unused_tokens)} CSV tokens absent from DIC [{coverage}]"
        )
    (output_root / "EXTRACTION_REPORT.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-root", type=Path, default=infer_game_root())
    parser.add_argument("--mod-name", default="KoreanPatch")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--keep-work", action="store_true")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    game_root = args.game_root.resolve()
    mods = game_root / "Mods"
    mod_root = mods / args.mod_name
    source_root = mod_root / "LocalizationSource"
    output_root = (args.output or (source_root / "Test" if args.test else source_root / "English")).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    dic_names = {"UNITS": "UNITS.dic", "INTERFACE_INGAME": "INTERFACE_INGAME.dic", "INTERFACE_OUTGAME": "INTERFACE_OUTGAME.dic", "COMPANIES": "companies.dic", "PLATOONS": "platoons.dic"}
    if args.test:
        dic_names = {"UNITS": "UNITS.dic"}

    tasklist = subprocess.run(["tasklist", "/FI", "IMAGENAME eq WARNO.exe"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if "WARNO.exe" in tasklist.stdout:
        raise RuntimeError("WARNO.exe is already running; close it before extraction")
    tokens = collect_tokens(mod_root)
    if args.test:
        tokens = {"UNITS": set(sorted(tokens["UNITS"])[:25]), "INTERFACE_INGAME": set(), "INTERFACE_OUTGAME": set(), "COMPANIES": set(), "PLATOONS": set()}
    else:
        # Interface token references are often consumed by both UI dictionaries.
        # Compile the union into both so the vanilla DIC hash decides placement.
        interface_union = tokens["INTERFACE_INGAME"] | tokens["INTERFACE_OUTGAME"]
        tokens["INTERFACE_INGAME"] = set(interface_union)
        tokens["INTERFACE_OUTGAME"] = set(interface_union)
    if not any(tokens.values()):
        raise RuntimeError("No localisation token references found in NDF sources")

    work_name = f"__LocExtract_{os.getpid()}_{uuid.uuid4().hex[:8]}"
    work_mod = mods / work_name
    source_logs = source_root / "Logs"
    source_logs.mkdir(parents=True, exist_ok=True)
    work_log = source_logs / f"{work_name}.log"
    datapacks = game_root / "Tools" / "Datapacks"
    temp_datapack = datapacks / "AllPlatforms"
    generated = work_mod / "Gen"
    try:
        run(["cmd", "/c", str(mods / "CreateNewMod.bat"), work_name], mods, work_log)
        cal_loc = work_mod / "GameData" / "Localisation" / work_name
        marker_to_token = {key: {} for key in tokens}
        for category, values in tokens.items():
            rows = []
            for index, token in enumerate(sorted(values)):
                marker = f"__LOC_{category[:3]}_{index:06d}__"
                rows.append((token, marker))
                marker_to_token[category][marker] = token
            write_csv(cal_loc / f"{category}.csv", rows)

        run([str(mods / "Utils" / "Python" / "python.exe"), str(mods / "Utils" / "Scripts" / "GenerateMod.py"), "WARNO", work_name], work_mod, work_log, allow_failure=True)
        for _ in range(120):
            check = subprocess.run(["tasklist", "/FI", "IMAGENAME eq WARNO.exe"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            if "WARNO.exe" not in check.stdout:
                break
            import time
            time.sleep(1)
        else:
            raise RuntimeError("WARNO.exe did not exit after generation")
        data_packer = game_root / "Tools" / "DataPacker.exe"
        if temp_datapack.exists():
            shutil.rmtree(temp_datapack, ignore_errors=True)
        vanilla_dats = ([game_root / "Data" / "PC" / "169425" / "ZZ_1.dat"] if args.test else locate_vanilla_dats(game_root, data_packer))
        if not vanilla_dats:
            raise RuntimeError("No ZZ_1.dat containing localisation dictionaries found")
        for vanilla_dat in vanilla_dats:
            run([str(data_packer), "unpack", str(vanilla_dat)], game_root, work_log)

        # Use only fresh dictionaries from this run; never persist a cache.
        report = extract_csvs(output_root, generated, datapacks, marker_to_token, dic_names)
        print("\n".join(report))
        return 0
    finally:
        if temp_datapack.exists():
            shutil.rmtree(temp_datapack, ignore_errors=True)
        if not args.keep_work:
            shutil.rmtree(work_mod, ignore_errors=True)
            if work_log.exists():
                work_log.unlink()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise










