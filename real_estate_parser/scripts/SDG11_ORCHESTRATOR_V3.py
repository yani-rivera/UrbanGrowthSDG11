#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SDG11_ORCHESTRATOR_V3

Data-driven SDG-11 workflow orchestrator.

V3 refactor goals:
1. Keep main() simple.
2. Preserve V2/V2.1 behavior.
3. Preserve CLI compatibility.
4. Add month-aware merge forwarding.
5. Preserve discovery summary.
6. Preserve missing configuration report.
7. Preserve missing configuration CSV output.
8. Prepare step-registry architecture for future phases.

Examples:

Parse only:
python scripts/SDG11_ORCHESTRATOR_V3.py \
  --all-agencies \
  --year 2011 \
  --month 01 \
  --steps parse

Parse + merge:
python scripts/SDG11_ORCHESTRATOR_V3.py \
  --all-agencies \
  --year 2011 \
  --month 01 \
  --steps parse merge

Merge only:
python scripts/SDG11_ORCHESTRATOR_V3.py \
  --all-agencies \
  --year 2011 \
  --month 01 \
  --steps merge
"""

from __future__ import annotations

import argparse
import csv
import glob
from html import parser
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


VERSION = "SDG11_ORCHESTRATOR_V3"

LOG_COLUMNS = [
    "run_id",
    "run_date",
    "step",
    "agency",
    "agency_folder",
    "mnemonic",
    "year",
    "month",
    "input_file",
    "input_path",
    "config_file",
    "output_file_expected",
    "status",
    "return_code",
    "error_message",
]

AGGREGATION_TASKS = [

    {
        "name": "neighborhood",
        "script": "tools/Aggregate_2010_Neighborhood_Summary.py",
        "output": "neighborhood_{year}monthly.csv",
        "needs_year": False,
    },

    {
        "name": "bedrooms",
        "script": "tools/Aggregate_Neighborhood_Summary_ByYear_Bedrooms.py",
        "output": "neighborhood_monthly_bedrooms_price.csv",
        "needs_year": True,
    },

    {
        "name": "area",
        "script": "tools/Aggregate_Neighborhood_Summary_ByYear_Area.py",
        "output": "neighborhood_{year}_monthly_area.csv",
        "needs_year": True,
    },

    {
        "name": "area_beds",
        "script": (
            "tools/"
            "Aggregate_Neighborhood_"
            "Summary_ByYear_AreaBeds_Flexible.py"
        ),
        "output": "neighborhood_{year}_monthly_area_beds.csv",
        "needs_year": True,
    },
]

# =============================================================================
# Basic Helpers
# =============================================================================

def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_name(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def month_to_str(month: Optional[str]) -> Optional[str]:
    if month in (None, "", "ALL"):
        return None
    return f"{int(month):02d}"

import pandas as pd


def check_missing_mnemonics(
    input_csv: str,
    mnemonics_csv: str,
) -> list[str]:

    df = pd.read_csv(
        input_csv,
        encoding="utf-8-sig"
    )

    agencies = (
        df["agency"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.lower()
        .unique()
    )

    mdf = pd.read_csv(
        mnemonics_csv,
        encoding="utf-8-sig"
    )

    known = (
        mdf["agency"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.lower()
        .unique()
    )

    missing = sorted(
        set(agencies) - set(known)
    )

    return missing


# =============================================================================
# Discovery EXPECTED
# =============================================================================


def expected_deduplicate_outputs(
    consolidated_root: str,
    year: int,
    month: Optional[str] = None,
) -> tuple[str, str]:

    month_str = month_to_str(month)

    if month_str:
        base = f"merged_{year}{month_str}"
    else:
        base = f"merged_{year}"

    canonical = os.path.join(
        consolidated_root,
        str(year),
        f"{base}_c.csv"
    )

    duplicates = os.path.join(
        consolidated_root,
        str(year),
        f"{base}_duplicates.csv"
    )

    return canonical, duplicates


def expected_word_filter_output(
    consolidated_root: str,
    year: int,
    month: Optional[str] = None,
) -> str:

    month_str = month_to_str(month)

    if month_str:
        base = f"merged_{year}{month_str}"
    else:
        base = f"merged_{year}"

    return os.path.join(
        consolidated_root,
        str(year),
        f"{base}_flt.csv"
    )

def expected_uid_output(
    consolidated_root: str,
    year: int,
    month: Optional[str] = None,
) -> str:

    month_str = month_to_str(month)

    if month_str:
        base = f"merged_{year}{month_str}"
    else:
        base = f"merged_{year}"

    return os.path.join(
        consolidated_root,
        str(year),
        f"{base}_uid.csv"
    )

def expected_clean_output(
    consolidated_root: str,
    year: int,
    month: Optional[str] = None,
) -> str:

    month_str = month_to_str(month)

    if month_str:
        base = f"merged_{year}{month_str}"
    else:
        base = f"merged_{year}"

    return os.path.join(
        consolidated_root,
        str(year),
        f"{base}_clean.csv"
    )

def expected_ptype_outputs(
    consolidated_root: str,
    year: int,
    month: Optional[str] = None,
) -> tuple[str, str]:

    month_str = month_to_str(month)

    if month_str:
        base = f"merged_{year}{month_str}"
    else:
        base = f"merged_{year}"

    main_output = os.path.join(
        consolidated_root,
        str(year),
        f"{base}_clean_ptype_fixed.csv"
    )

    scores_output = os.path.join(
        consolidated_root,
        str(year),
        f"{base}_clean_ptype_fixed_scores.csv"
    )

    return main_output, scores_output

def expected_filter_outputs(
    consolidated_root: str,
    year: int,
    month: Optional[str] = None,
) -> tuple[str, str]:

    month_str = month_to_str(month)

    if month_str:
        base = f"merged_{year}{month_str}"
    else:
        base = f"merged_{year}"

    filtered_file = os.path.join(
        consolidated_root,
        str(year),
        f"{base}_filtered.csv"
    )

    rejected_file = os.path.join(
        consolidated_root,
        str(year),
        f"{year}_filtered_rejected.csv"
    )

    return filtered_file, rejected_file

def expected_gis_match_outputs(
    consolidated_root: str,
    year: int,
    month: Optional[str] = None,
) -> tuple[str, str, str]:

    month_str = month_to_str(month)

    if month_str:
        base = f"merged_{year}{month_str}"
    else:
        base = f"merged_{year}"

    merged_file = os.path.join(
        consolidated_root,
        str(year),
        f"{base}_with_gis.csv"
    )

    matched_file = os.path.join(
        consolidated_root,
        str(year),
        "matched.csv"
    )

    unmatched_file = os.path.join(
        consolidated_root,
        str(year),
        "unmatched.csv"
    )

    return (
        merged_file,
        matched_file,
        unmatched_file,
    )

def expected_stdprice_output(
    consolidated_root: str,
    year: int,
    month: Optional[str] = None,
) -> str:

    month_str = month_to_str(month)

    if month_str:
        base = f"merged_{year}{month_str}"
    else:
        base = f"merged_{year}"

    return os.path.join(
        consolidated_root,
        str(year),
        f"{base}_STDPrice.csv"
    )

def step_price_standardize(ctx: Dict[str, Any]) -> None:

    args = ctx["args"]

    print("\n==============================================")
    print("STEP: PRICE STANDARDIZATION")
    print("==============================================")

    gis_input, _, _ = expected_gis_match_outputs(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    # Your command uses *_valid.csv
    gis_input = gis_input.replace(
        "_with_gis.csv",
        "_with_gis_valid.csv"
    )

    output_file = expected_stdprice_output(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    fx_file = "FXrate/fx_HNL_USD.csv"

    print(f"Input  : {gis_input}")
    print(f"FX     : {fx_file}")
    print(f"Output : {output_file}")

    if not os.path.exists(gis_input):
        print("❌ Valid GIS file not found")
        return

    if args.dry_run:

        status = "DRY_RUN"
        return_code = 0
        error_message = ""

    else:

        result = run_stdprice_subprocess(
            script=args.stdprice_script,
            input_file=gis_input,
            fx_file=fx_file,
            output_file=output_file,
        )

        return_code = result.returncode

        if result.stdout:
            print(result.stdout)

        if return_code == 0:
            status = "SUCCESS"
            error_message = ""
            print("✅ Price standardization completed")
        else:
            status = "FAILED"
            error_message = result.stderr.strip()
            print(error_message)

    append_log(
        ctx["log_file"],
        {
            "run_id": ctx["run_id"],
            "run_date": ctx["run_date"],
            "step": "price_standardize",
            "agency": "",
            "agency_folder": "",
            "mnemonic": "",
            "year": args.year,
            "month": args.month or "ALL",
            "input_file": os.path.basename(gis_input),
            "input_path": gis_input,
            "config_file": fx_file,
            "output_file_expected": output_file,
            "status": status,
            "return_code": return_code,
            "error_message": error_message,
        },
    )

def expected_transaction_output(
    consolidated_root: str,
    year: int,
    month: Optional[str] = None,
) -> str:

    month_str = month_to_str(month)

    if month_str:
        base = f"merged_{year}{month_str}"
    else:
        base = f"merged_{year}"

    return os.path.join(
        consolidated_root,
        str(year),
        f"{base}_STDPrice_t.csv"
    )

def expected_area_output(
    consolidated_root: str,
    year: int,
    month: Optional[str] = None,
) -> str:

    month_str = month_to_str(month)

    if month_str:
        base = f"merged_{year}{month_str}"
    else:
        base = f"merged_{year}"

    return os.path.join(
        consolidated_root,
        str(year),
        f"{base}_STDPrice_AreaM2.csv"
    )

def expected_neighborhood_output(
    consolidated_root: str,
    year: int,
    month: Optional[str] = None,
) -> str:

    return os.path.join(
        consolidated_root,
        str(year),
        f"neighborhood_{year}monthly.csv"
    )

def expected_bedroom_output(
    consolidated_root: str,
    year: int,
) -> str:

    return os.path.join(
        consolidated_root,
        str(year),
        "neighborhood_monthly_bedrooms_price.csv"
    )


# =============================================================================
# Discovery Helpers
# =============================================================================

def discover_agencies_with_files(
    input_root: str,
    year: int,
    month: Optional[str] = None,
) -> List[str]:
    if not os.path.isdir(input_root):
        raise FileNotFoundError(f"Input root not found: {input_root}")

    discovered = []

    for agency_folder in sorted(os.listdir(input_root)):
        year_dir = os.path.join(input_root, agency_folder, str(year))

        if not os.path.isdir(year_dir):
            continue

        txt_files = sorted(glob.glob(os.path.join(year_dir, "*.txt")))

        month_str = month_to_str(month)
        if month_str:
            pattern = f"{year}{month_str}"
            txt_files = [
                f for f in txt_files
                if pattern in os.path.basename(f)
            ]

        if txt_files:
            discovered.append(agency_folder)

    return discovered


def discover_txt_files(
    input_root: str,
    agency_folder: str,
    year: int,
    month: Optional[str] = None,
) -> List[str]:
    year_dir = os.path.join(input_root, agency_folder, str(year))

    if not os.path.isdir(year_dir):
        return []

    files = sorted(glob.glob(os.path.join(year_dir, "*.txt")))

    month_str = month_to_str(month)
    if month_str:
        pattern = f"{year}{month_str}"
        files = [
            f for f in files
            if pattern in os.path.basename(f)
        ]

    return files


def find_config_for_agency(config_dir: str, agency_folder: str) -> Optional[str]:
    candidate = os.path.join(
        config_dir,
        f"agency_{normalize_name(agency_folder)}.json"
    )

    if os.path.exists(candidate):
        return candidate

    for cfg_path in sorted(glob.glob(os.path.join(config_dir, "*.json"))):
        try:
            cfg = load_json(cfg_path)
        except Exception:
            continue

        cfg_agency = cfg.get("agency", "")

        if normalize_name(cfg_agency) == normalize_name(agency_folder):
            return cfg_path

    return None


def build_discovery_details(ctx: Dict[str, Any]) -> List[dict]:
    args = ctx["args"]

    if args.all_agencies:
        agency_folders = discover_agencies_with_files(
            input_root=args.input_root,
            year=args.year,
            month=args.month,
        )
    else:
        agency_folders = [args.agency]

    ctx["agency_folders"] = agency_folders

    discovery_details = []

    for agency_folder in agency_folders:
        files = discover_txt_files(
            input_root=args.input_root,
            agency_folder=agency_folder,
            year=args.year,
            month=args.month,
        )

        config_file = find_config_for_agency(
            config_dir=args.config_dir,
            agency_folder=agency_folder,
        )

        discovery_details.append(
            {
                "agency_folder": agency_folder,
                "file_count": len(files),
                "config_exists": bool(config_file),
                "config_file": config_file or "",
                "expected_config_file": expected_config_filename(
                    args.config_dir,
                    agency_folder,
                ),
            }
        )

    ctx["discovery_details"] = discovery_details

    return discovery_details


# =============================================================================
# Path Helpers
# =============================================================================

def infer_date_from_filename(path: str) -> str:
    filename = os.path.basename(path)
    m = re.search(r"(\d{8})", filename)
    return m.group(1) if m else "unknown"


def expected_output_path(
    output_root: str,
    agency_folder: str,
    mnemonic: str,
    input_file: str,
) -> str:
    date_value = infer_date_from_filename(input_file)
    year = date_value[:4] if date_value != "unknown" else "unknown"

    return os.path.join(
        output_root,
        agency_folder.lower(),
        year,
        f"{mnemonic}_{date_value}.csv"
    )


def build_log_file(
    run_id: str,
    agency: Optional[str],
    year: int,
    month: Optional[str],
) -> str:
    scope = agency if agency else "ALL"
    month_str = month if month else "ALL"

    run_dir = os.path.join("logs", run_id)
    os.makedirs(run_dir, exist_ok=True)

    return os.path.join(
        run_dir,
        f"log_{scope}_{year}_{month_str}.csv"
    )


def expected_config_filename(config_dir: str, agency_folder: str) -> str:
    return os.path.join(
        config_dir,
        f"agency_{normalize_name(agency_folder)}.json"
    )


def expected_merged_output(
    consolidated_root: str,
    year: int,
    month: Optional[str] = None,
) -> str:
    month_str = month_to_str(month)

    if month_str:
        filename = f"merged_{year}{month_str}.csv"
    else:
        filename = f"merged_{year}.csv"

    return os.path.join(
        consolidated_root,
        str(year),
        filename,
    )


def build_missing_config_report_file(run_id: str) -> str:
    run_dir = os.path.join("logs", run_id)
    os.makedirs(run_dir, exist_ok=True)
    return os.path.join(run_dir, "missing_configs.csv")


# =============================================================================
# Logging and Reports
# =============================================================================

def append_log(log_file: str, row: dict) -> None:
    log_dir = os.path.dirname(log_file)

    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    file_exists = os.path.exists(log_file)

    with open(log_file, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS)

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)


def write_missing_config_report(
    report_file: str,
    missing_config_details: List[dict],
) -> None:
    """
    Write a compact CSV report of agencies/folders discovered in input data
    that do not yet have a matching config file.
    """
    if not missing_config_details:
        return

    report_dir = os.path.dirname(report_file)
    if report_dir:
        os.makedirs(report_dir, exist_ok=True)

    columns = [
        "agency_folder",
        "file_count",
        "expected_config_file",
    ]

    with open(report_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for item in sorted(
            missing_config_details,
            key=lambda x: (-x["file_count"], x["agency_folder"].lower())
        ):
            writer.writerow(item)


def print_header(ctx: Dict[str, Any]) -> None:
    args = ctx["args"]

    print("\n==============================================")
    print(VERSION)
    print("==============================================")
    print(f"Run ID       : {ctx['run_id']}")
    print(f"Scope        : {'ALL AGENCIES WITH FILES' if args.all_agencies else args.agency}")
    print(f"Year         : {args.year}")
    print(f"Month        : {args.month if args.month else 'ALL'}")
    print(f"Steps        : {' '.join(args.steps)}")
    print(f"Config Dir   : {args.config_dir}")
    print(f"Input Root   : {args.input_root}")
    print(f"Output Root  : {args.output_root}")
    print(f"Consolidated : {args.consolidated_root}")
    print(f"Parser       : {args.parser_script}")
    print(f"Merge Script : {args.merge_script}")
    print(f"Dry Run      : {args.dry_run}")
    print("==============================================\n")


def print_discovery_summary(discovery_details: List[dict]) -> None:
    """
    Print a preflight table showing which discovered agency folders
    have matching config files.
    """
    if not discovery_details:
        print("\nNo agencies with matching files were discovered.")
        return

    discovered_count = len(discovery_details)
    configured_count = sum(1 for x in discovery_details if x["config_exists"])
    missing_count = discovered_count - configured_count

    print("\n==============================================")
    print("DISCOVERY SUMMARY")
    print("==============================================")
    print(f"Agencies discovered : {discovered_count}")
    print(f"Configured          : {configured_count}")
    print(f"Missing config      : {missing_count}")
    print("----------------------------------------------")
    print(f"{'Agency Folder':<28} {'Files':>7} {'Config':>8}")
    print("----------------------------------------------")

    for item in sorted(
        discovery_details,
        key=lambda x: (not x["config_exists"], x["agency_folder"].lower())
    ):
        config_label = "YES" if item["config_exists"] else "NO"
        print(
            f"{item['agency_folder']:<28} "
            f"{item['file_count']:>7} "
            f"{config_label:>8}"
        )

    print("==============================================")


def print_missing_config_summary(
    missing_config_details: List[dict],
    report_file: Optional[str] = None,
) -> None:
    """
    Print an actionable end-of-run missing config report, ranked by file count.
    """
    if not missing_config_details:
        return

    print("\nMissing Config Report")
    print("----------------------------------------------")
    print(f"{'Agency Folder':<28} {'Files':>7}  Expected Config")
    print("----------------------------------------------")

    sorted_items = sorted(
        missing_config_details,
        key=lambda x: (-x["file_count"], x["agency_folder"].lower())
    )

    for item in sorted_items:
        print(
            f"{item['agency_folder']:<28} "
            f"{item['file_count']:>7}  "
            f"{item['expected_config_file']}"
        )

    print("----------------------------------------------")

    print("\nSuggested Next Actions")
    print("----------------------------------------------")
    for i, item in enumerate(sorted_items, start=1):
        print(
            f"{i}. Create config for {item['agency_folder']} "
            f"({item['file_count']} file(s))"
        )

    if report_file:
        print(f"\nMissing config CSV  : {report_file}")


def print_execution_summary(ctx: Dict[str, Any]) -> None:
    args = ctx["args"]

    print("\n==============================================")
    print("EXECUTION SUMMARY")
    print("==============================================")
    print(f"Run ID              : {ctx['run_id']}")
    print(f"Steps               : {' '.join(args.steps)}")
    print(f"Agencies processed  : {ctx['total_agencies']}")
    print(f"Missing config      : {ctx['total_missing_config']}")

    if ctx["missing_config_details"]:
        report_file = build_missing_config_report_file(ctx["run_id"])
        write_missing_config_report(
            report_file,
            ctx["missing_config_details"],
        )
        print_missing_config_summary(
            ctx["missing_config_details"],
            report_file=report_file,
        )

    print(f"Missing files       : {ctx['total_missing_files']}")
    print(f"Files processed     : {ctx['total_files']}")

    if args.dry_run:
        print("Mode                : DRY RUN")
    else:
        print(f"Parse successful    : {ctx['total_parse_success']}")
        print(f"Parse failed        : {ctx['total_parse_failed']}")
        print(f"Merge status        : {ctx['merge_status']}")

    print(f"Log file            : {ctx['log_file']}")
    print("==============================================\n")


# =============================================================================
# Subprocess Wrappers
# =============================================================================

def run_parse_subprocess(
    parser_script: str,
    txt_file: str,
    config_file: str,
    output_root: str,
) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        parser_script,
        "--file",
        txt_file,
        "--config",
        config_file,
        "--output-dir",
        output_root,
    ]

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )


def run_merge_subprocess(
    merge_script: str,
    year: int,
    month: Optional[str],
    output_root: str,
    consolidated_root: str,
) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        merge_script,
        "--year",
        str(year),
        "--input",
        output_root,
        "--output",
        consolidated_root,
    ]

    month_str = month_to_str(month)
    if month_str:
        cmd.extend(["--month", month_str])

    print("\n[DEBUG] Merge command:")
    print(" ".join(cmd))

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )


def run_deduplicate_subprocess(
    deduplicate_script: str,
    input_file: str,
    canonical_file: str,
    duplicates_file: str,
) -> subprocess.CompletedProcess:

    cmd = [
        sys.executable,
        deduplicate_script,
        "--input",
        input_file,
        "--out-canonical",
        canonical_file,
        "--out-duplicates",
        duplicates_file,
    ]

    print("\n[DEBUG] Deduplicate command:")
    print(" ".join(cmd))

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )


def run_word_filter_subprocess(
    script: str,
    input_file: str,
    output_file: str,
    words_file: str,
) -> subprocess.CompletedProcess:

    cmd = [
        sys.executable,
        script,
        "--input",
        input_file,
        "--output",
        output_file,
        "--col",
        "neighborhood",
        "--words-file",
        words_file,
    ]

    print("\n[DEBUG] Word Filter command:")
    print(" ".join(cmd))

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )


def run_uid_subprocess(
    script: str,
    input_file: str,
    output_file: str,
    mnemonics_file: str,
) -> subprocess.CompletedProcess:

    cmd = [
        sys.executable,
        script,
        "-i",
        input_file,
        "-o",
        output_file,
        "--agency-col",
        "agency",
        "--date-col",
        "date",
        "--mnemonics",
        mnemonics_file,
        "--mnemonic-required",
        "--encoding",
        "utf-8-sig",
    ]

    print("\n[DEBUG] UID command:")
    print(" ".join(cmd))

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )


def run_clean_neighborhoods_subprocess(
    script: str,
    input_file: str,
    output_file: str,
) -> subprocess.CompletedProcess:

    cmd = [
        sys.executable,
        script,
        "--input_csv",
        input_file,
        "--input_col",
        "neighborhood",
        "--out_csv",
        output_file,
        "--add_norm",
    ]

    print("\n[DEBUG] Clean Neighborhoods command:")
    print(" ".join(cmd))

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

def run_ptype_subprocess(
    script: str,
    input_file: str,
    output_file: str,
    scores_file: str,
) -> subprocess.CompletedProcess:

    cmd = [
        sys.executable,
        script,
        "--input",
        input_file,
        "--output",
        output_file,
        "--scores-output",
        scores_file,
    ]

    print("\n[DEBUG] Property Type command:")
    print(" ".join(cmd))

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

def run_filter_subprocess(
    script: str,
    input_file: str,
    output_file: str,
    rejected_file: str,
) -> subprocess.CompletedProcess:

    cmd = [
        sys.executable,
        script,
        "-i",
        input_file,
        "-o",
        output_file,
        "--price-col",
        "price",
        "--type-col",
        "property_type_new",
        "--exclude-types-files",
        "config/exclude_types.csv:Type",
        "--exclude-neighborhoods-files",
        "config/outside_metro.txt",
        "--neigh-col",
        "neighborhood_clean_norm",
        "--rejected",
        rejected_file,
        "--neigh-match",
        "exact",
    ]

    print("\n[DEBUG] Filter command:")
    print(" ".join(cmd))

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

def run_gis_match_subprocess(
    script: str,
    listings_file: str,
    merged_file: str,
    matched_file: str,
    unmatched_file: str,
) -> subprocess.CompletedProcess:

    cmd = [
        sys.executable,
        script,
        "--listings_csv",
        listings_file,
        "--listings_col",
        "neighborhood_clean_norm",
        "--catalog_csv",
        "Catalog/standard_neighborhood_catalog.csv",
        "--out_merged",
        merged_file,
        "--out_matched",
        matched_file,
        "--out_unmatched",
        unmatched_file,
    ]

    print("\n[DEBUG] GIS Match command:")
    print(" ".join(cmd))

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

def run_unmatched_subprocess(
    script: str,
    input_file: str,
) -> subprocess.CompletedProcess:

    cmd = [
        sys.executable,
        script,
        "--input",
        input_file,
    ]

    print("\n[DEBUG] Unmatched Check command:")
    print(" ".join(cmd))

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

def run_stdprice_subprocess(
    script: str,
    input_file: str,
    fx_file: str,
    output_file: str,
) -> subprocess.CompletedProcess:

    cmd = [
        sys.executable,
        script,
        "--input",
        input_file,
        "--fx",
        fx_file,
        "--output",
        output_file,
    ]

    print("\n[DEBUG] StdPrice command:")
    print(" ".join(cmd))

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

def run_transaction_subprocess(
    script: str,
    input_file: str,
    output_file: str,
) -> subprocess.CompletedProcess:

    cmd = [
        sys.executable,
        script,
        "--input",
        input_file,
        "--output",
        output_file,
    ]

    print("\n[DEBUG] Transaction Validation command:")
    print(" ".join(cmd))

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

def run_area_subprocess(
    script: str,
    input_file: str,
    output_file: str,
) -> subprocess.CompletedProcess:

    cmd = [
        sys.executable,
        script,
        "--input",
        input_file,
        "--output",
        output_file,
    ]

    print("\n[DEBUG] Area Standardization command:")
    print(" ".join(cmd))

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

def run_neighborhood_aggregate_subprocess(
    script: str,
    input_file: str,
    output_file: str,
) -> subprocess.CompletedProcess:

    cmd = [
        sys.executable,
        script,
        "--input",
        input_file,
        "--min-n",
        "5",
        "--output",
        output_file,
    ]

    print("\n[DEBUG] Neighborhood aggregation command:")
    print(" ".join(cmd))

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

def run_bedroom_aggregate_subprocess(
    script: str,
    input_file: str,
    year: int,
    output_file: str,
) -> subprocess.CompletedProcess:

    cmd = [
        sys.executable,
        script,
        "--input",
        input_file,
        "--year",
        str(year),
        "--min-n",
        "5",
        "--output",
        output_file,
    ]

    print("\n[DEBUG] Bedroom aggregation command:")
    print(" ".join(cmd))

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )


def run_aggregation_task(
    task,
    input_file,
    year,
    output_file,
):
    cmd = [
        sys.executable,
        task["script"],
        "--input",
        input_file,
    ]

    if task["needs_year"]:
        cmd.extend([
            "--year",
            str(year),
        ])

    cmd.extend([
        "--min-n",
        "5",
        "--output",
        output_file,
    ])

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

# =============================================================================
# Context and CLI
# =============================================================================

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SDG11_ORCHESTRATOR_V3"
    )

    parser.add_argument("--agency", required=False)
    parser.add_argument("--all-agencies", action="store_true")

    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--month", required=False)

    parser.add_argument(
        "--steps",
        nargs="+",
        default=["parse"],
        choices=[
        "parse",
        "merge",
        "deduplicate",
        "word_filter",
        "uid",
        "clean_neighborhoods",
        "ptype_fix",
        "filter_records",
        "gis_match",
        "unmatched_check",
        "price_standardize",
        "transaction_validate",
        "area_standardize",
        "aggregate",
        ],
        help="Pipeline steps to execute in order",
    )

    parser.add_argument(
        "--config-dir",
        default="config/agencies",
    )

    parser.add_argument(
        "--input-root",
        default="data/raw",
    )

    parser.add_argument(
        "--output-root",
        default="output",
    )

    parser.add_argument(
        "--consolidated-root",
        default="consolidated",
    )

    parser.add_argument(
        "--parser-script",
        default="scripts/AgencyCoreParser_v1.py",
    )

    parser.add_argument(
        "--merge-script",
        default="tools/merge_output_csvs.py",
    )

    parser.add_argument(
        "--deduplicate-script",
        default="tools/MergeDeduplicate.py",
    )
    parser.add_argument(
    "--word-filter-script",
    default="tools/word_filter.py",
    ) 
    parser.add_argument(
    "--uid-script",
    default="tools/AddUid.py",
    )

    parser.add_argument(
    "--clean-neighborhoods-script",
    default="tools/clean_neighborhoods.py",
    )
    parser.add_argument(
    "--ptype-script",
    default="L1clean/ptype_l1_clean_v8.py",
    )

    parser.add_argument(
    "--filter-script",
    default="L1clean/FilterMergedFile.py",
    )

    parser.add_argument(
    "--gis-match-script",
    default="tools/match_cleaned_to_catalog.py",
    )

    parser.add_argument(
    "--unmatched-script",
    default="tools/unmatched.py",
    )

    parser.add_argument(
    "--stdprice-script",
    default="tools/StdPrice.py",
    )
    parser.add_argument(
    "--transaction-script",
    default="L1clean/ValidateTransaction.py",
    )

    parser.add_argument(
    "--area-script",
    default="tools/terrain_area_to_at.py",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
    )


    args = parser.parse_args()

    if args.all_agencies and args.agency:
        raise ValueError("Use either --agency or --all-agencies, not both.")

    if not args.all_agencies and not args.agency:
        raise ValueError("Use either --agency <AgencyName> or --all-agencies.")

    if args.month:
        args.month = month_to_str(args.month)

    return args


def initialize_context(args: argparse.Namespace) -> Dict[str, Any]:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_file = build_log_file(
        run_id=run_id,
        agency=args.agency,
        year=args.year,
        month=args.month,
    )

    return {
        "args": args,
        "run_id": run_id,
        "run_date": run_date,
        "log_file": log_file,

        "agency_folders": [],
        "discovery_details": [],
        "missing_config_details": [],

        "total_agencies": 0,
        "total_files": 0,
        "total_parse_success": 0,
        "total_parse_failed": 0,
        "total_missing_config": 0,
        "total_missing_files": 0,

        "merge_status": "NOT_REQUESTED",
        "merge_return_code": "",
        "merge_error": "",
    }


# =============================================================================
# Step Functions
# =============================================================================

def step_discovery(ctx: Dict[str, Any]) -> None:
    """
    Discover agencies/files and print a config coverage table.
    Discovery is run before selected steps so the operator can see coverage.
    """
    args = ctx["args"]

    print(f"Agencies with matching files: ", end="")

    discovery_details = build_discovery_details(ctx)

    print(len(ctx["agency_folders"]))

    # Print discovery only when parse is requested.
    # Merge-only runs do not require agency config discovery, but keeping this
    # available in context is still harmless and useful.
    if "parse" in args.steps:
        print_discovery_summary(discovery_details)


def step_parse(ctx: Dict[str, Any]) -> None:
    args = ctx["args"]

    print("\n==============================================")
    print("STEP: PARSE")
    print("==============================================")

    if not ctx["agency_folders"]:
        build_discovery_details(ctx)

    for agency_folder in ctx["agency_folders"]:

        files = discover_txt_files(
            input_root=args.input_root,
            agency_folder=agency_folder,
            year=args.year,
            month=args.month,
        )

        if not files:
            ctx["total_missing_files"] += 1
            print(
                f"⚠️ No files found for {agency_folder} / "
                f"{args.year} / {args.month or 'ALL'}"
            )
            continue

        config_file = find_config_for_agency(
            config_dir=args.config_dir,
            agency_folder=agency_folder,
        )

        if not config_file:
            handle_missing_config(ctx, agency_folder, files)
            continue

        try:
            cfg = load_json(config_file)
        except Exception as ex:
            handle_invalid_config(ctx, agency_folder, files, config_file, ex)
            continue

        process_agency_files(
            ctx=ctx,
            agency_folder=agency_folder,
            files=files,
            config_file=config_file,
            cfg=cfg,
        )


def handle_missing_config(
    ctx: Dict[str, Any],
    agency_folder: str,
    files: List[str],
) -> None:
    args = ctx["args"]

    ctx["total_missing_config"] += 1

    ctx["missing_config_details"].append(
        {
            "agency_folder": agency_folder,
            "file_count": len(files),
            "expected_config_file": expected_config_filename(
                args.config_dir,
                agency_folder,
            ),
        }
    )

    print(f"⚠️ Missing config for agency folder: {agency_folder}")

    for txt_file in files:
        append_log(
            ctx["log_file"],
            {
                "run_id": ctx["run_id"],
                "run_date": ctx["run_date"],
                "step": "parse",
                "agency": "",
                "agency_folder": agency_folder,
                "mnemonic": "",
                "year": args.year,
                "month": args.month or "ALL",
                "input_file": os.path.basename(txt_file),
                "input_path": txt_file,
                "config_file": "",
                "output_file_expected": "",
                "status": "MISSING_CONFIG",
                "return_code": "",
                "error_message": f"No config found for {agency_folder}",
            },
        )


def handle_invalid_config(
    ctx: Dict[str, Any],
    agency_folder: str,
    files: List[str],
    config_file: str,
    ex: Exception,
) -> None:
    args = ctx["args"]

    ctx["total_missing_config"] += 1

    print(f"⚠️ Invalid config skipped: {config_file}")
    print(ex)

    for txt_file in files:
        append_log(
            ctx["log_file"],
            {
                "run_id": ctx["run_id"],
                "run_date": ctx["run_date"],
                "step": "parse",
                "agency": "",
                "agency_folder": agency_folder,
                "mnemonic": "",
                "year": args.year,
                "month": args.month or "ALL",
                "input_file": os.path.basename(txt_file),
                "input_path": txt_file,
                "config_file": config_file,
                "output_file_expected": "",
                "status": "INVALID_CONFIG",
                "return_code": "",
                "error_message": str(ex),
            },
        )


def process_agency_files(
    ctx: Dict[str, Any],
    agency_folder: str,
    files: List[str],
    config_file: str,
    cfg: dict,
) -> None:
    args = ctx["args"]

    agency = cfg.get("agency", agency_folder)

    mnemonic = (
        cfg.get("mnemonic")
        or cfg.get("nemonic")
        or agency.upper()
    )

    ctx["total_agencies"] += 1

    print(f"\nAgency: {agency} ({mnemonic})")
    print(f"Folder: {agency_folder}")
    print(f"Config: {config_file}")
    print(f"Files found: {len(files)}")

    for txt_file in files:
        process_single_file(
            ctx=ctx,
            agency=agency,
            agency_folder=agency_folder,
            mnemonic=mnemonic,
            config_file=config_file,
            txt_file=txt_file,
        )


def process_single_file(
    ctx: Dict[str, Any],
    agency: str,
    agency_folder: str,
    mnemonic: str,
    config_file: str,
    txt_file: str,
) -> None:
    args = ctx["args"]

    ctx["total_files"] += 1

    expected_output = expected_output_path(
        args.output_root,
        agency_folder,
        mnemonic,
        txt_file,
    )

    print(f"  → {os.path.basename(txt_file)}")

    if args.dry_run:
        status = "DRY_RUN"
        return_code = 0
        error_message = ""
    else:
        result = run_parse_subprocess(
            parser_script=args.parser_script,
            txt_file=txt_file,
            config_file=config_file,
            output_root=args.output_root,
        )

        return_code = result.returncode

        if return_code == 0:
            status = "SUCCESS"
            error_message = ""
            ctx["total_parse_success"] += 1
        else:
            status = "FAILED"
            error_message = result.stderr.strip()
            ctx["total_parse_failed"] += 1
            print("    FAILED")
            print(error_message)

    append_log(
        ctx["log_file"],
        {
            "run_id": ctx["run_id"],
            "run_date": ctx["run_date"],
            "step": "parse",
            "agency": agency,
            "agency_folder": agency_folder,
            "mnemonic": mnemonic,
            "year": args.year,
            "month": args.month or "ALL",
            "input_file": os.path.basename(txt_file),
            "input_path": txt_file,
            "config_file": config_file,
            "output_file_expected": expected_output,
            "status": status,
            "return_code": return_code,
            "error_message": error_message,
        },
    )


def step_merge(ctx: Dict[str, Any]) -> None:
    args = ctx["args"]

    print("\n==============================================")
    print("STEP: MERGE")
    print("==============================================")

    merged_output = expected_merged_output(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    print(f"Expected merged output: {merged_output}")

    merge_return_code = ""
    merge_error = ""

    if args.dry_run:
        merge_status = "DRY_RUN"
        merge_return_code = 0
        merge_error = ""

        print("[DRY RUN] Merge skipped")

    else:
        result = run_merge_subprocess(
            merge_script=args.merge_script,
            year=args.year,
            month=args.month,
            output_root=args.output_root,
            consolidated_root=args.consolidated_root,
        )

        if result.stdout:
            print(result.stdout)

        merge_return_code = result.returncode

        if merge_return_code == 0:
            merge_status = "SUCCESS"
            merge_error = ""
            print("✅ Merge completed")
        else:
            merge_status = "FAILED"
            merge_error = result.stderr.strip()
            print("❌ Merge failed")
            print(merge_error)

    ctx["merge_status"] = merge_status
    ctx["merge_return_code"] = merge_return_code
    ctx["merge_error"] = merge_error

    append_log(
        ctx["log_file"],
        {
            "run_id": ctx["run_id"],
            "run_date": ctx["run_date"],
            "step": "merge",
            "agency": "",
            "agency_folder": "",
            "mnemonic": "",
            "year": args.year,
            "month": args.month or "ALL",
            "input_file": "",
            "input_path": args.output_root,
            "config_file": "",
            "output_file_expected": merged_output,
            "status": merge_status,
            "return_code": merge_return_code,
            "error_message": merge_error,
        },
    )

def step_deduplicate(ctx: Dict[str, Any]) -> None:

    args = ctx["args"]

    print("\n==============================================")
    print("STEP: DEDUPLICATE")
    print("==============================================")

    merged_input = expected_merged_output(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    canonical_file, duplicates_file = (
        expected_deduplicate_outputs(
            consolidated_root=args.consolidated_root,
            year=args.year,
            month=args.month,
        )
    )

    print(f"Input       : {merged_input}")
    print(f"Canonical   : {canonical_file}")
    print(f"Duplicates  : {duplicates_file}")

    if not os.path.exists(merged_input):
        print("❌ Merged input not found")
        return

    if args.dry_run:
        print("[DRY RUN] Deduplicate skipped")
        status = "DRY_RUN"
        return_code = 0
        error_message = ""

    else:
        result = run_deduplicate_subprocess(
            deduplicate_script=args.deduplicate_script,
            input_file=merged_input,
            canonical_file=canonical_file,
            duplicates_file=duplicates_file,
        )

        return_code = result.returncode

        if result.stdout:
            print(result.stdout)

        if return_code == 0:
            status = "SUCCESS"
            error_message = ""
            print("✅ Deduplication completed")
        else:
            status = "FAILED"
            error_message = result.stderr.strip()
            print("❌ Deduplication failed")
            print(error_message)

    append_log(
        ctx["log_file"],
        {
            "run_id": ctx["run_id"],
            "run_date": ctx["run_date"],
            "step": "deduplicate",
            "agency": "",
            "agency_folder": "",
            "mnemonic": "",
            "year": args.year,
            "month": args.month or "ALL",
            "input_file": os.path.basename(merged_input),
            "input_path": merged_input,
            "config_file": "",
            "output_file_expected": canonical_file,
            "status": status,
            "return_code": return_code,
            "error_message": error_message,
        },
    )


def step_word_filter(ctx: Dict[str, Any]) -> None:

    args = ctx["args"]

    print("\n==============================================")
    print("STEP: WORD FILTER")
    print("==============================================")

    canonical_file, _ = expected_deduplicate_outputs(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    filtered_output = expected_word_filter_output(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    words_file = "config/remove_words.txt"

    print(f"Input  : {canonical_file}")
    print(f"Output : {filtered_output}")
    print(f"Words  : {words_file}")

    if not os.path.exists(canonical_file):
        print("❌ Canonical file not found")
        return

    if args.dry_run:

        status = "DRY_RUN"
        return_code = 0
        error_message = ""

        print("[DRY RUN] Word filter skipped")

    else:

        result = run_word_filter_subprocess(
            script=args.word_filter_script,
            input_file=canonical_file,
            output_file=filtered_output,
            words_file=words_file,
        )

        return_code = result.returncode

        if result.stdout:
            print(result.stdout)

        if return_code == 0:
            status = "SUCCESS"
            error_message = ""
            print("✅ Word filtering completed")
        else:
            status = "FAILED"
            error_message = result.stderr.strip()
            print("❌ Word filtering failed")
            print(error_message)

    append_log(
        ctx["log_file"],
        {
            "run_id": ctx["run_id"],
            "run_date": ctx["run_date"],
            "step": "word_filter",
            "agency": "",
            "agency_folder": "",
            "mnemonic": "",
            "year": args.year,
            "month": args.month or "ALL",
            "input_file": os.path.basename(canonical_file),
            "input_path": canonical_file,
            "config_file": words_file,
            "output_file_expected": filtered_output,
            "status": status,
            "return_code": return_code,
            "error_message": error_message,
        },
    )


def step_uid(ctx: Dict[str, Any]) -> None:

    args = ctx["args"]

    print("\n==============================================")
    print("STEP: UID ASSIGNMENT")
    print("==============================================")

    filtered_input = expected_word_filter_output(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    uid_output = expected_uid_output(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    mnemonics_file = "config/agency_mnemonics.csv"

    print(f"Input     : {filtered_input}")
    print(f"Output    : {uid_output}")
    print(f"Mnemonics : {mnemonics_file}")

    if not os.path.exists(filtered_input):
        print("❌ Filtered file not found")
        return

    if args.dry_run:

        status = "DRY_RUN"
        return_code = 0
        error_message = ""

        print("[DRY RUN] UID stage skipped")

    else:
        missing = check_missing_mnemonics(
        filtered_input,
        mnemonics_file,
        )

        if missing:

            print("\n❌ UID PRECHECK FAILED")
            print("----------------------------------")
            print("Missing agency mnemonics:")
            print("----------------------------------")

            for agency in missing:
                print(f"  - {agency}")

            print("----------------------------------")
            print(
                f"Add {len(missing)} agency mnemonic(s) "
                f"to {mnemonics_file}"
            )

            status = "PRECHECK_FAILED"
            return_code = ""
            error_message = (
                "Missing mnemonics: "
                + ", ".join(missing)
            )

            append_log(
                ctx["log_file"],
                {
                    "run_id": ctx["run_id"],
                    "run_date": ctx["run_date"],
                    "step": "uid_precheck",
                    "agency": "",
                    "agency_folder": "",
                    "mnemonic": "",
                    "year": args.year,
                    "month": args.month or "ALL",
                    "input_file": os.path.basename(filtered_input),
                    "input_path": filtered_input,
                    "config_file": mnemonics_file,
                    "output_file_expected": uid_output,
                    "status": status,
                    "return_code": return_code,
                    "error_message": error_message,
                },
            )

            return
        
        #========

        result = run_uid_subprocess(
            script=args.uid_script,
            input_file=filtered_input,
            output_file=uid_output,
            mnemonics_file=mnemonics_file,
        )

        return_code = result.returncode

        if result.stdout:
            print(result.stdout)

        if return_code == 0:
            status = "SUCCESS"
            error_message = ""
            print("✅ UID assignment completed")
        else:
            status = "FAILED"
            error_message = result.stderr.strip()
            print("❌ UID assignment failed")
            print(error_message)

    append_log(
        ctx["log_file"],
        {
            "run_id": ctx["run_id"],
            "run_date": ctx["run_date"],
            "step": "uid",
            "agency": "",
            "agency_folder": "",
            "mnemonic": "",
            "year": args.year,
            "month": args.month or "ALL",
            "input_file": os.path.basename(filtered_input),
            "input_path": filtered_input,
            "config_file": mnemonics_file,
            "output_file_expected": uid_output,
            "status": status,
            "return_code": return_code,
            "error_message": error_message,
        },
    )

def step_clean_neighborhoods(ctx: Dict[str, Any]) -> None:

    args = ctx["args"]

    print("\n==============================================")
    print("STEP: CLEAN NEIGHBORHOODS")
    print("==============================================")

    uid_input = expected_uid_output(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    clean_output = expected_clean_output(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    print(f"Input  : {uid_input}")
    print(f"Output : {clean_output}")

    if not os.path.exists(uid_input):
        print("❌ UID file not found")
        return

    if args.dry_run:

        status = "DRY_RUN"
        return_code = 0
        error_message = ""

        print("[DRY RUN] Clean neighborhoods skipped")

    else:

        result = run_clean_neighborhoods_subprocess(
            script=args.clean_neighborhoods_script,
            input_file=uid_input,
            output_file=clean_output,
        )

        return_code = result.returncode

        if result.stdout:
            print(result.stdout)

        if return_code == 0:
            status = "SUCCESS"
            error_message = ""
            print("✅ Neighborhood normalization completed")
        else:
            status = "FAILED"
            error_message = result.stderr.strip()
            print("❌ Neighborhood normalization failed")
            print(error_message)

    append_log(
        ctx["log_file"],
        {
            "run_id": ctx["run_id"],
            "run_date": ctx["run_date"],
            "step": "clean_neighborhoods",
            "agency": "",
            "agency_folder": "",
            "mnemonic": "",
            "year": args.year,
            "month": args.month or "ALL",
            "input_file": os.path.basename(uid_input),
            "input_path": uid_input,
            "config_file": "",
            "output_file_expected": clean_output,
            "status": status,
            "return_code": return_code,
            "error_message": error_message,
        },
    )

def step_ptype_fix(ctx: Dict[str, Any]) -> None:

    args = ctx["args"]

    print("\n==============================================")
    print("STEP: PROPERTY TYPE CLASSIFICATION")
    print("==============================================")

    clean_input = expected_clean_output(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    output_file, scores_file = (
        expected_ptype_outputs(
            consolidated_root=args.consolidated_root,
            year=args.year,
            month=args.month,
        )
    )

    print(f"Input  : {clean_input}")
    print(f"Output : {output_file}")
    print(f"Scores : {scores_file}")

    if not os.path.exists(clean_input):
        print("❌ Clean file not found")
        return

    if args.dry_run:

        status = "DRY_RUN"
        return_code = 0
        error_message = ""

        print("[DRY RUN] Property classification skipped")

    else:

        result = run_ptype_subprocess(
            script=args.ptype_script,
            input_file=clean_input,
            output_file=output_file,
            scores_file=scores_file,
        )

        return_code = result.returncode

        if result.stdout:
            print(result.stdout)

        if return_code == 0:
            status = "SUCCESS"
            error_message = ""
            print("✅ Property classification completed")
        else:
            status = "FAILED"
            error_message = result.stderr.strip()
            print("❌ Property classification failed")
            print(error_message)

    append_log(
        ctx["log_file"],
        {
            "run_id": ctx["run_id"],
            "run_date": ctx["run_date"],
            "step": "ptype_fix",
            "agency": "",
            "agency_folder": "",
            "mnemonic": "",
            "year": args.year,
            "month": args.month or "ALL",
            "input_file": os.path.basename(clean_input),
            "input_path": clean_input,
            "config_file": "",
            "output_file_expected": output_file,
            "status": status,
            "return_code": return_code,
            "error_message": error_message,
        },
    )

def step_filter_records(ctx: Dict[str, Any]) -> None:

    args = ctx["args"]

    print("\n==============================================")
    print("STEP: FILTER RECORDS")
    print("==============================================")

    ptype_input, _ = expected_ptype_outputs(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    filtered_output, rejected_output = (
        expected_filter_outputs(
            consolidated_root=args.consolidated_root,
            year=args.year,
            month=args.month,
        )
    )

    print(f"Input    : {ptype_input}")
    print(f"Output   : {filtered_output}")
    print(f"Rejected : {rejected_output}")

    if not os.path.exists(ptype_input):
        print("❌ Property-type file not found")
        return

    if args.dry_run:

        status = "DRY_RUN"
        return_code = 0
        error_message = ""

        print("[DRY RUN] Filter stage skipped")

    else:

        result = run_filter_subprocess(
            script=args.filter_script,
            input_file=ptype_input,
            output_file=filtered_output,
            rejected_file=rejected_output,
        )

        return_code = result.returncode

        if result.stdout:
            print(result.stdout)

        if return_code == 0:
            status = "SUCCESS"
            error_message = ""
            print("✅ Filtering completed")
        else:
            status = "FAILED"
            error_message = result.stderr.strip()
            print("❌ Filtering failed")
            print(error_message)

    append_log(
        ctx["log_file"],
        {
            "run_id": ctx["run_id"],
            "run_date": ctx["run_date"],
            "step": "filter_records",
            "agency": "",
            "agency_folder": "",
            "mnemonic": "",
            "year": args.year,
            "month": args.month or "ALL",
            "input_file": os.path.basename(ptype_input),
            "input_path": ptype_input,
            "config_file": "",
            "output_file_expected": filtered_output,
            "status": status,
            "return_code": return_code,
            "error_message": error_message,
        },
    )

def step_gis_match(ctx: Dict[str, Any]) -> None:

    args = ctx["args"]

    print("\n==============================================")
    print("STEP: GIS MATCH")
    print("==============================================")

    filtered_input, _ = expected_filter_outputs(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    merged_file, matched_file, unmatched_file = (
        expected_gis_match_outputs(
            consolidated_root=args.consolidated_root,
            year=args.year,
            month=args.month,
        )
    )

    print(f"Input      : {filtered_input}")
    print(f"With GIS   : {merged_file}")
    print(f"Matched    : {matched_file}")
    print(f"Unmatched  : {unmatched_file}")

    if not os.path.exists(filtered_input):
        print("❌ Filtered dataset not found")
        return

    if args.dry_run:

        status = "DRY_RUN"
        return_code = 0
        error_message = ""

        print("[DRY RUN] GIS match skipped")

    else:

        result = run_gis_match_subprocess(
            script=args.gis_match_script,
            listings_file=filtered_input,
            merged_file=merged_file,
            matched_file=matched_file,
            unmatched_file=unmatched_file,
        )

        return_code = result.returncode

        if result.stdout:
            print(result.stdout)

        if return_code == 0:
            status = "SUCCESS"
            error_message = ""
            print("✅ GIS matching completed")
        else:
            status = "FAILED"
            error_message = result.stderr.strip()
            print("❌ GIS matching failed")
            print(error_message)

    append_log(
        ctx["log_file"],
        {
            "run_id": ctx["run_id"],
            "run_date": ctx["run_date"],
            "step": "gis_match",
            "agency": "",
            "agency_folder": "",
            "mnemonic": "",
            "year": args.year,
            "month": args.month or "ALL",
            "input_file": os.path.basename(filtered_input),
            "input_path": filtered_input,
            "config_file": "Catalog/standard_neighborhood_catalog.csv",
            "output_file_expected": merged_file,
            "status": status,
            "return_code": return_code,
            "error_message": error_message,
        },
    )

def step_unmatched_check(ctx: Dict[str, Any]) -> None:

    args = ctx["args"]

    print("\n==============================================")
    print("STEP: UNMATCHED QA CHECK")
    print("==============================================")

    gis_input, _, _ = expected_gis_match_outputs(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    print(f"Input : {gis_input}")

    if not os.path.exists(gis_input):
        print("❌ GIS matched file not found")
        return

    if args.dry_run:

        status = "DRY_RUN"
        return_code = 0
        error_message = ""

    else:

        result = run_unmatched_subprocess(
            script=args.unmatched_script,
            input_file=gis_input,
        )

        return_code = result.returncode

        if result.stdout:
            print(result.stdout)

        if return_code == 0:
            status = "SUCCESS"
            error_message = ""
            print("✅ Unmatched QA completed")
        else:
            status = "FAILED"
            error_message = result.stderr.strip()
            print(error_message)

    append_log(
        ctx["log_file"],
        {
            "run_id": ctx["run_id"],
            "run_date": ctx["run_date"],
            "step": "unmatched_check",
            "agency": "",
            "agency_folder": "",
            "mnemonic": "",
            "year": args.year,
            "month": args.month or "ALL",
            "input_file": os.path.basename(gis_input),
            "input_path": gis_input,
            "config_file": "",
            "output_file_expected": "",
            "status": status,
            "return_code": return_code,
            "error_message": error_message,
        },
    )

def step_transaction_validate(ctx: Dict[str, Any]) -> None:

    args = ctx["args"]

    print("\n==============================================")
    print("STEP: TRANSACTION VALIDATION")
    print("==============================================")

    stdprice_input = expected_stdprice_output(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    output_file = expected_transaction_output(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    print(f"Input  : {stdprice_input}")
    print(f"Output : {output_file}")

    if not os.path.exists(stdprice_input):
        print("❌ Standardized price file not found")
        return

    if args.dry_run:

        status = "DRY_RUN"
        return_code = 0
        error_message = ""

        print("[DRY RUN] Transaction validation skipped")

    else:

        result = run_transaction_subprocess(
            script=args.transaction_script,
            input_file=stdprice_input,
            output_file=output_file,
        )

        return_code = result.returncode

        if result.stdout:
            print(result.stdout)

        if return_code == 0:
            status = "SUCCESS"
            error_message = ""
            print("✅ Transaction validation completed")
        else:
            status = "FAILED"
            error_message = result.stderr.strip()
            print("❌ Transaction validation failed")
            print(error_message)

    append_log(
        ctx["log_file"],
        {
            "run_id": ctx["run_id"],
            "run_date": ctx["run_date"],
            "step": "transaction_validate",
            "agency": "",
            "agency_folder": "",
            "mnemonic": "",
            "year": args.year,
            "month": args.month or "ALL",
            "input_file": os.path.basename(stdprice_input),
            "input_path": stdprice_input,
            "config_file": "",
            "output_file_expected": output_file,
            "status": status,
            "return_code": return_code,
            "error_message": error_message,
        },
    )

def step_area_standardize(ctx: Dict[str, Any]) -> None:

    args = ctx["args"]

    print("\n==============================================")
    print("STEP: AREA STANDARDIZATION")
    print("==============================================")

    transaction_input = expected_transaction_output(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    output_file = expected_area_output(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    print(f"Input  : {transaction_input}")
    print(f"Output : {output_file}")

    if not os.path.exists(transaction_input):
        print("❌ Transaction validated file not found")
        return

    if args.dry_run:

        status = "DRY_RUN"
        return_code = 0
        error_message = ""

        print("[DRY RUN] Area standardization skipped")

    else:

        result = run_area_subprocess(
            script=args.area_script,
            input_file=transaction_input,
            output_file=output_file,
        )

        return_code = result.returncode

        if result.stdout:
            print(result.stdout)

        if return_code == 0:
            status = "SUCCESS"
            error_message = ""
            print("✅ Area standardization completed")
        else:
            status = "FAILED"
            error_message = result.stderr.strip()
            print("❌ Area standardization failed")
            print(error_message)

    append_log(
        ctx["log_file"],
        {
            "run_id": ctx["run_id"],
            "run_date": ctx["run_date"],
            "step": "area_standardize",
            "agency": "",
            "agency_folder": "",
            "mnemonic": "",
            "year": args.year,
            "month": args.month or "ALL",
            "input_file": os.path.basename(transaction_input),
            "input_path": transaction_input,
            "config_file": "",
            "output_file_expected": output_file,
            "status": status,
            "return_code": return_code,
            "error_message": error_message,
        },
    )



def step_aggregate(ctx):

    args = ctx["args"]

    input_file = expected_area_output(
        consolidated_root=args.consolidated_root,
        year=args.year,
        month=args.month,
    )

    for task in AGGREGATION_TASKS:

        output_file = os.path.join(
            args.consolidated_root,
            str(args.year),
            task["output"].format(
                year=args.year
            )
        )

        print(
            f"\nRunning aggregation: "
            f"{task['name']}"
        )

        result = run_aggregation_task(
            task,
            input_file,
            args.year,
            output_file,
        )

        if result.returncode != 0:

            print(
                f"❌ Aggregation failed: "
                f"{task['name']}"
            )

            print(result.stderr)

            return

        print(
            f"✅ Completed: "
            f"{task['name']}"
        )

# =============================================================================
# Step Registry
# =============================================================================

STEP_REGISTRY = {
    "parse": step_parse,
    "merge": step_merge,
    "deduplicate": step_deduplicate,
    "word_filter": step_word_filter,
    "uid": step_uid,
    "clean_neighborhoods": step_clean_neighborhoods,
    "ptype_fix": step_ptype_fix,
    "filter_records": step_filter_records,
    "gis_match": step_gis_match,
    "unmatched_check": step_unmatched_check,
    "price_standardize": step_price_standardize,
    "transaction_validate": step_transaction_validate,
    "area_standardize": step_area_standardize,
     "aggregate": step_aggregate,
}


def execute_requested_steps(ctx: Dict[str, Any]) -> None:
    args = ctx["args"]

    for step_name in args.steps:
        step_fn = STEP_REGISTRY.get(step_name)

        if step_fn is None:
            raise ValueError(f"Unknown step: {step_name}")

        step_fn(ctx)


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    args = parse_arguments()
    ctx = initialize_context(args)

    print_header(ctx)

    step_discovery(ctx)

    execute_requested_steps(ctx)

    print_execution_summary(ctx)


if __name__ == "__main__":
    main()
