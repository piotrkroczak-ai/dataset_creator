from __future__ import annotations

import json
import math
import random
import threading
import time
import queue
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText


APP_NAME = "Controlled Dataset Generator"
APP_VERSION = "6.1.0"

DEFAULT_PERCENTAGES = {
    "level_1": 65,
    "level_2": 25,
    "level_3": 10,
}

ERROR_GROUPS: Dict[str, List[str]] = {
    "level_1": [
        "missing_values",
        "full_duplicates",
        "leading_trailing_spaces",
        "dirty_column_names",
        "decimal_commas",
        "boolean_variants",
    ],
    "level_2": [
        "mixed_date_formats",
        "simple_outliers",
        "negative_ages",
        "country_variants",
        "invalid_emails",
        "future_dates",
    ],
    "level_3": [
        "corrupted_text_values",
        "partial_duplicates",
        "multi_column_date_inconsistency",
        "irrelevant_noise_columns",
    ],
}


ROW_LEVEL_ERRORS = {
    "missing_values",
    "full_duplicates",
    "leading_trailing_spaces",
    "decimal_commas",
    "boolean_variants",
    "mixed_date_formats",
    "simple_outliers",
    "negative_ages",
    "country_variants",
    "invalid_emails",
    "future_dates",
    "corrupted_text_values",
    "partial_duplicates",
    "multi_column_date_inconsistency",
}

SCHEMA_LEVEL_ERRORS = {
    "dirty_column_names",
    "irrelevant_noise_columns",
}

ERROR_LABELS = {
    "missing_values": "Missing values",
    "full_duplicates": "Full duplicates",
    "leading_trailing_spaces": "Leading/trailing spaces",
    "dirty_column_names": "Dirty column names",
    "decimal_commas": "Decimal commas",
    "boolean_variants": "Boolean variants",
    "mixed_date_formats": "Mixed date formats",
    "simple_outliers": "Simple outliers",
    "negative_ages": "Negative ages",
    "country_variants": "Country variants",
    "invalid_emails": "Invalid emails",
    "future_dates": "Future dates",
    "corrupted_text_values": "Corrupted text values",
    "partial_duplicates": "Partial duplicates",
    "multi_column_date_inconsistency": "Multi-column date inconsistency",
    "irrelevant_noise_columns": "Irrelevant noise columns",
}

UNIT_TEST_SHORTCODES: Dict[str, str] = {
    "missing_values":                  "MissingVal",
    "full_duplicates":                 "FullDup",
    "leading_trailing_spaces":         "TrimSpace",
    "dirty_column_names":              "DirtyCol",
    "decimal_commas":                  "DecComma",
    "boolean_variants":                "BoolVar",
    "mixed_date_formats":              "MixedDate",
    "simple_outliers":                 "Outlier",
    "negative_ages":                   "NegAge",
    "country_variants":                "CountryVar",
    "invalid_emails":                  "InvalidEmail",
    "future_dates":                    "FutureDate",
    "corrupted_text_values":           "CorruptText",
    "partial_duplicates":              "PartialDup",
    "multi_column_date_inconsistency": "MultiDateInc",
    "irrelevant_noise_columns":        "NoiseCol",
}

UNIT_TEST_TYPE_LABELS = {
    "level_1": "Type 1 — Simple",
    "level_2": "Type 2 — Intermediate",
    "level_3": "Type 3 — Advanced",
}

UNIT_TEST_ROWS        = 1000
UNIT_TEST_COLUMNS     = 10
UNIT_TEST_AFFECTED_PCT = 10
UNIT_TEST_TOTAL        = 100


EXPECTED_ACTIONS = {
    "missing_values": "standardize_missing_values_or_impute",
    "full_duplicates": "remove_duplicates",
    "leading_trailing_spaces": "trim_text",
    "dirty_column_names": "normalize_column_names",
    "decimal_commas": "convert_decimal_commas",
    "boolean_variants": "standardize_booleans",
    "mixed_date_formats": "parse_dates_safe",
    "simple_outliers": "flag_outliers",
    "negative_ages": "flag_logical_error",
    "country_variants": "standardize_categories",
    "invalid_emails": "flag_invalid_email",
    "future_dates": "flag_future_date",
    "corrupted_text_values": "flag_corrupted_values",
    "partial_duplicates": "flag_partial_duplicates",
    "multi_column_date_inconsistency": "flag_multi_column_inconsistency",
    "irrelevant_noise_columns": "flag_or_drop_irrelevant_columns",
}

DIFFICULTY_LABELS = {
    "level_1": "type_1_simple",
    "level_2": "type_2_intermediate",
    "level_3": "type_3_advanced",
}

PROFILE_PRESETS: Dict[str, Dict[str, int]] = {
    "DEMO_SMALL": {
        "rows": 300,
        "columns": 12,
        "affected_rows_pct": 20,
        "total_errors": 168,
        "type_1_pct": 65,
        "type_2_pct": 25,
        "type_3_pct": 10,
    },
    "BEGINNER_LEVEL_1": {
        "rows": 1000,
        "columns": 12,
        "affected_rows_pct": 20,
        "total_errors": 250,
        "type_1_pct": 75,
        "type_2_pct": 20,
        "type_3_pct": 5,
    },
    "BEGINNER_LEVEL_2": {
        "rows": 3000,
        "columns": 15,
        "affected_rows_pct": 20,
        "total_errors": 650,
        "type_1_pct": 60,
        "type_2_pct": 30,
        "type_3_pct": 10,
    },
    "CUSTOM": {
        "rows": 1000,
        "columns": 15,
        "affected_rows_pct": 20,
        "total_errors": 500,
        "type_1_pct": 80,
        "type_2_pct": 10,
        "type_3_pct": 10,
    },
}

GENERATED_FILES_TEXT = (
    "demo_clean_dataset.csv | demo_dirty_dataset.csv | "
    "demo_dataset_spec.json | demo_error_manifest.csv | README.md"
)


def safe_int(value: str, default: int = 0, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        n = int(str(value).strip())
    except Exception:
        n = default
    if minimum is not None:
        n = max(minimum, n)
    if maximum is not None:
        n = min(maximum, n)
    return n


def safe_pct(value: str, default: int = 0) -> int:
    return safe_int(value, default=default, minimum=0, maximum=100)


def validate_counts_against_bounds(counts: Dict[str, int], rows: int, columns: int, affected_rows_count: int) -> List[str]:
    """Return warning messages when requested counts exceed physical dataset bounds.

    Schema-level errors are bounded by the number of columns.
    Row-level duplicate errors are bounded by the affected-row pool.
    Total cell-level errors are bounded by available cells in affected rows.
    Returns an empty list when no warnings are found.
    """
    warnings: List[str] = []

    max_dirty_column_names = max(0, columns - 1)
    requested_dirty = counts.get("dirty_column_names", 0)
    if requested_dirty > max_dirty_column_names:
        warnings.append(
            f"dirty_column_names: requested {requested_dirty} but dataset has only "
            f"{columns} columns — will be capped to {max_dirty_column_names}."
        )

    max_noise_columns = max(1, min(10, columns // 3))
    requested_noise = counts.get("irrelevant_noise_columns", 0)
    if requested_noise > max_noise_columns:
        warnings.append(
            f"irrelevant_noise_columns: requested {requested_noise} but safe maximum "
            f"for {columns} columns is {max_noise_columns} — will be capped."
        )

    for error_type in ("full_duplicates", "partial_duplicates"):
        requested = counts.get(error_type, 0)
        if affected_rows_count > 0 and requested > affected_rows_count:
            warnings.append(
                f"{error_type}: requested {requested} but only {affected_rows_count} "
                f"affected rows available — excess events will be skipped."
            )

    total_row_level = sum(counts.get(e, 0) for e in ROW_LEVEL_ERRORS)
    available_cells = affected_rows_count * max(1, columns - 1)
    if total_row_level > available_cells:
        warnings.append(
            f"Total row-level errors ({total_row_level}) exceeds available cells "
            f"({affected_rows_count} rows x {max(1, columns - 1)} cols = {available_cells}) "
            f"— some events will be silently skipped."
        )

    return warnings


def distribute_integer(total: int, weights: List[int]) -> List[int]:
    """Return integer counts that sum exactly to total."""
    if total <= 0 or sum(weights) <= 0:
        return [0 for _ in weights]

    raw = [total * w / sum(weights) for w in weights]
    floors = [math.floor(x) for x in raw]
    remainder = total - sum(floors)

    fractional_order = sorted(
        range(len(raw)),
        key=lambda i: raw[i] - floors[i],
        reverse=True
    )

    for i in fractional_order[:remainder]:
        floors[i] += 1

    return floors


def random_split(total: int, keys: List[str], rng: random.Random) -> Dict[str, int]:
    """Randomly distribute an integer total across keys while preserving the exact sum.

    v4 deliberately avoids equal distribution inside a difficulty type. This makes
    generated datasets more realistic while keeping the requested Type 1 / Type 2 /
    Type 3 totals exact.
    """
    if total <= 0:
        return {k: 0 for k in keys}
    if not keys:
        return {}

    # Gamma weights produce a non-uniform but stable distribution with a fixed seed.
    weights = [max(0.01, rng.gammavariate(1.4, 1.0)) for _ in keys]
    raw = [total * w / sum(weights) for w in weights]
    floors = [math.floor(x) for x in raw]
    remainder = total - sum(floors)

    order = sorted(range(len(keys)), key=lambda i: raw[i] - floors[i], reverse=True)
    for i in order[:remainder]:
        floors[i] += 1

    return {k: v for k, v in zip(keys, floors)}


def redistribute_schema_overflow(counts: Dict[str, int], columns: int, rng: random.Random) -> Dict[str, int]:
    """Keep percentage-mode schema errors realistic and redistribute overflow.

    Dirty column names and noise columns are schema-level errors. Without a cap,
    random distribution could create too many schema changes for a small dataset.
    Overflow is redistributed inside the same difficulty type so Type 1 / Type 2 /
    Type 3 totals remain unchanged.
    """
    result = dict(counts)

    max_dirty_column_names = max(0, columns - 1)
    dirty_overflow = max(0, result.get("dirty_column_names", 0) - max_dirty_column_names)
    if dirty_overflow:
        result["dirty_column_names"] = max_dirty_column_names
        targets = [e for e in ERROR_GROUPS["level_1"] if e != "dirty_column_names"]
        add_back = random_split(dirty_overflow, targets, rng)
        for key, value in add_back.items():
            result[key] = result.get(key, 0) + value

    max_noise_columns = max(1, min(10, max(1, columns // 3)))
    noise_overflow = max(0, result.get("irrelevant_noise_columns", 0) - max_noise_columns)
    if noise_overflow:
        result["irrelevant_noise_columns"] = max_noise_columns
        targets = [e for e in ERROR_GROUPS["level_3"] if e != "irrelevant_noise_columns"]
        add_back = random_split(noise_overflow, targets, rng)
        for key, value in add_back.items():
            result[key] = result.get(key, 0) + value

    return result


def counts_from_percentages(total_errors: int, p1: int, p2: int, p3: int, seed: int = 42, columns: int = 12) -> Dict[str, int]:
    rng = random.Random(seed + 404)
    level_counts = distribute_integer(total_errors, [p1, p2, p3])
    result: Dict[str, int] = {}
    for level, level_total in zip(["level_1", "level_2", "level_3"], level_counts):
        result.update(random_split(level_total, ERROR_GROUPS[level], rng))
    return redistribute_schema_overflow(result, columns, rng)


def randomize_counts_from_percentages(
    total_errors: int,
    p1: int,
    p2: int,
    p3: int,
    columns: int,
    click_index: int = 0,
) -> Dict[str, int]:
    """Distribute total_errors randomly across sub-types using a fresh seed each call.

    The percentages p1/p2/p3 are normalised to 100 before use so the caller
    does not need to guarantee they already sum to 100.

    click_index is incremented by the UI on each button press so that every
    click produces a different distribution even with the same settings.
    """
    total_pct = p1 + p2 + p3
    if total_pct <= 0:
        p1, p2, p3 = 65, 25, 10
        total_pct = 100
    # Normalise to exact integer percentages that sum to 100.
    p1n = round(p1 * 100 / total_pct)
    p2n = round(p2 * 100 / total_pct)
    p3n = 100 - p1n - p2n  # guarantee exact sum = 100

    # Use a seed derived from the click index so each press gives a new result.
    fresh_seed = 9999 + click_index * 31337
    rng = random.Random(fresh_seed)
    level_counts = distribute_integer(total_errors, [p1n, p2n, p3n])
    result: Dict[str, int] = {}
    for level, level_total in zip(["level_1", "level_2", "level_3"], level_counts):
        result.update(random_split(level_total, ERROR_GROUPS[level], rng))
    return redistribute_schema_overflow(result, columns, rng)


def counts_by_difficulty(counts: Dict[str, int]) -> Dict[str, int]:
    return {
        level: sum(counts.get(e, 0) for e in errors)
        for level, errors in ERROR_GROUPS.items()
    }


def labeled_counts_by_difficulty(counts: Dict[str, int]) -> Dict[str, int]:
    raw = counts_by_difficulty(counts)
    return {DIFFICULTY_LABELS[level]: value for level, value in raw.items()}


def split_counts_by_scope(counts: Dict[str, int]) -> Tuple[Dict[str, int], Dict[str, int]]:
    row_level = {k: v for k, v in counts.items() if k in ROW_LEVEL_ERRORS}
    schema_level = {k: v for k, v in counts.items() if k in SCHEMA_LEVEL_ERRORS}
    return row_level, schema_level


def build_affected_rows(rows: int, affected_pct: int, seed: int) -> List[int]:
    rows = max(0, rows)
    if rows == 0:
        return []
    pct = max(0, min(100, affected_pct))
    count = int(round(rows * pct / 100))
    count = max(0, min(rows, count))
    rng = random.Random(seed + 777)
    return sorted(rng.sample(range(rows), count))


def infer_error_level(error_type: str) -> str:
    for level, errors in ERROR_GROUPS.items():
        if error_type in errors:
            return level
    return "unknown"


def make_clean_dataset(rows: int, columns: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    first_names = ["Marie", "Jan", "Anna", "Piotr", "Sophie", "Lucas", "Emma", "John", "Kasia", "Nicolas"]
    last_names = ["Curie", "Kowalski", "Nowak", "Martin", "Dupont", "Smith", "Brown", "Zielinski", "Durand", "Lewandowski"]
    countries = ["FR", "PL", "DE", "ES", "UK"]
    categories = ["A", "B", "C", "D"]
    cities = ["Paris", "Poznan", "Berlin", "Madrid", "London", "Wroclaw", "Lyon"]
    plans = ["free", "basic", "pro", "enterprise"]
    sources = ["seo", "ads", "social", "email", "referral"]

    start = datetime(2022, 1, 1)
    signup_offsets = rng.integers(0, 900, size=rows)
    login_offsets = signup_offsets + rng.integers(0, 120, size=rows)

    first = rng.choice(first_names, size=rows)
    last = rng.choice(last_names, size=rows)

    df = pd.DataFrame({
        "id": np.arange(1, rows + 1),
        "first_name": first,
        "last_name": last,
        "email": [f"{f.lower()}.{l.lower()}{i}@example.com" for i, (f, l) in enumerate(zip(first, last), start=1)],
        "country": rng.choice(countries, size=rows),
        "signup_date": [(start + timedelta(days=int(x))).date().isoformat() for x in signup_offsets],
        "last_login": [(start + timedelta(days=int(x))).date().isoformat() for x in login_offsets],
        "amount": np.round(rng.normal(loc=120.0, scale=35.0, size=rows).clip(5, 350), 2),
        "active": rng.choice([True, False], size=rows, p=[0.72, 0.28]),
        "age": rng.integers(18, 75, size=rows),
        "category": rng.choice(categories, size=rows),
        "city": rng.choice(cities, size=rows),
        "plan": rng.choice(plans, size=rows),
        "source": rng.choice(sources, size=rows),
        "score": np.round(rng.uniform(0, 100, size=rows), 2),
        "notes": rng.choice(["ok", "review", "priority", "standard", "follow up"], size=rows),
        "support_tickets": rng.poisson(lam=1.2, size=rows),
        "discount_rate": np.round(rng.uniform(0, 0.35, size=rows), 2),
        "region": rng.choice(["north", "south", "east", "west"], size=rows),
        "segment": rng.choice(["smb", "midmarket", "enterprise"], size=rows),
    })

    columns = max(8, min(columns, len(df.columns)))
    preferred = [
        "id", "first_name", "last_name", "email", "country",
        "signup_date", "last_login", "amount", "active", "age",
        "category", "city", "plan", "source", "score",
        "notes", "support_tickets", "discount_rate", "region", "segment"
    ]

    return df[preferred[:columns]].copy()


class ErrorInjector:
    def __init__(self, clean_df: pd.DataFrame, seed: int, affected_base_indices: List[int]) -> None:
        self.clean_df = clean_df.copy()
        # Keep the dirty dataframe as object dtype.
        # We intentionally inject strings, blanks, and missing markers into
        # numeric / boolean / date columns. Pandas nullable/strict dtypes can
        # reject those values, especially np.nan in boolean columns.
        self.dirty_df = clean_df.copy().astype("object")
        self.rng = random.Random(seed)
        self.affected_base_indices = [i for i in affected_base_indices if 0 <= i < len(clean_df)]
        if not self.affected_base_indices:
            self.affected_base_indices = list(range(len(clean_df)))
        self.used_cells: set[Tuple[int, str]] = set()
        self.used_event_keys: set[Tuple[str, str, str]] = set()
        self.used_duplicate_sources: set[Tuple[str, int]] = set()
        self.manifest: List[Dict[str, Any]] = []
        self.event_counter = 0

    def add_manifest(
        self,
        row_id: Any,
        column: str,
        error_type: str,
        clean_value: Any,
        dirty_value: Any,
        scope: str = "cell",
        affected_base_row_id: Any = None,
        dirty_row_id: Any = None,
    ) -> bool:
        """Record one unique error event.

        Counting unit in v4: one manifest row equals one unique error event.
        The same (row_id, column, error_type) combination is not counted twice.
        Multiple different errors may still exist on the same row.
        """
        key = (str(row_id), str(column), str(error_type))
        if key in self.used_event_keys:
            return False
        self.used_event_keys.add(key)
        self.event_counter += 1

        level = infer_error_level(error_type)
        self.manifest.append({
            "error_event_id": self.event_counter,
            "scope": scope,
            "affected_base_row_id": "" if affected_base_row_id is None else str(affected_base_row_id),
            "dirty_row_id": "" if dirty_row_id is None else str(dirty_row_id),
            "row_id": row_id,
            "column": column,
            "error_type": error_type,
            "clean_value": "" if pd.isna(clean_value) else str(clean_value),
            "dirty_value": "" if pd.isna(dirty_value) else str(dirty_value),
            "difficulty": DIFFICULTY_LABELS.get(level, level),
            "expected_action": EXPECTED_ACTIONS.get(error_type, "review"),
        })
        return True

    def available_columns(self, preferred: List[str]) -> List[str]:
        return [c for c in preferred if c in self.dirty_df.columns]

    def pick_cell(self, columns: List[str]) -> Tuple[int, str] | None:
        if not columns or self.dirty_df.empty:
            return None

        row_pool = [i for i in self.affected_base_indices if i < len(self.dirty_df)]
        if not row_pool:
            row_pool = list(range(min(len(self.clean_df), len(self.dirty_df))))

        for _ in range(1000):
            idx = self.rng.choice(row_pool)
            col = self.rng.choice(columns)
            if (idx, col) not in self.used_cells:
                self.used_cells.add((idx, col))
                return idx, col

        return None

    def pick_source_row_for_row_event(self, event_type: str) -> int | None:
        candidates = [i for i in self.affected_base_indices if (event_type, i) not in self.used_duplicate_sources]
        if not candidates:
            return None
        source_idx = self.rng.choice(candidates)
        self.used_duplicate_sources.add((event_type, source_idx))
        return source_idx

    def inject_missing_values(self, n: int) -> int:
        cols = [c for c in self.dirty_df.columns if c != "id"]
        done = 0
        for _ in range(n):
            cell = self.pick_cell(cols)
            if not cell:
                break
            idx, col = cell
            clean = self.dirty_df.at[idx, col]
            self.dirty_df.at[idx, col] = np.nan
            self.add_manifest(idx, col, "missing_values", clean, np.nan, scope="cell", affected_base_row_id=idx, dirty_row_id=idx)
            done += 1
        return done

    def inject_full_duplicates(self, n: int) -> int:
        if self.dirty_df.empty:
            return 0

        done = 0
        for _ in range(n):
            source_idx = self.pick_source_row_for_row_event("full_duplicates")
            if source_idx is None:
                break
            duplicate = self.clean_df.iloc[[source_idx]].copy()
            new_idx = len(self.dirty_df)
            self.dirty_df = pd.concat([self.dirty_df, duplicate], ignore_index=True)
            recorded = self.add_manifest(
                new_idx,
                "__row__",
                "full_duplicates",
                "new row should not exist",
                f"duplicate full row copied from base row {source_idx}",
                scope="row",
                affected_base_row_id=source_idx,
                dirty_row_id=new_idx,
            )
            if recorded:
                done += 1
        return done

    def inject_leading_trailing_spaces(self, n: int) -> int:
        cols = self.available_columns(["first_name", "last_name", "email", "country", "category", "city", "plan", "source", "notes"])
        done = 0
        for _ in range(n):
            cell = self.pick_cell(cols)
            if not cell:
                break
            idx, col = cell
            clean = self.dirty_df.at[idx, col]
            dirty = f"  {clean}  "
            self.dirty_df.at[idx, col] = dirty
            self.add_manifest(idx, col, "leading_trailing_spaces", clean, dirty, scope="cell", affected_base_row_id=idx, dirty_row_id=idx)
            done += 1
        return done

    def inject_dirty_column_names(self, n: int) -> int:
        candidates = [c for c in self.dirty_df.columns if c not in ["id"]]
        self.rng.shuffle(candidates)
        selected = candidates[:min(n, len(candidates))]
        rename_map = {}
        for col in selected:
            dirty_col = col.replace("_", " ").title()
            if self.rng.random() < 0.5:
                dirty_col = f" {dirty_col} "
            if dirty_col in self.dirty_df.columns or dirty_col in rename_map.values():
                dirty_col = f"Dirty {dirty_col}"
            rename_map[col] = dirty_col
            self.add_manifest("__columns__", col, "dirty_column_names", col, dirty_col, scope="schema_column")

        if rename_map:
            self.dirty_df = self.dirty_df.rename(columns=rename_map)
        return len(rename_map)

    def inject_decimal_commas(self, n: int) -> int:
        cols = self.available_columns(["amount", "score", "discount_rate"])
        done = 0
        for _ in range(n):
            cell = self.pick_cell(cols)
            if not cell:
                break
            idx, col = cell
            clean = self.dirty_df.at[idx, col]
            try:
                dirty = f"{float(clean):.2f}".replace(".", ",")
            except Exception:
                continue
            self.dirty_df.at[idx, col] = dirty
            self.add_manifest(idx, col, "decimal_commas", clean, dirty, scope="cell", affected_base_row_id=idx, dirty_row_id=idx)
            done += 1
        return done

    def inject_boolean_variants(self, n: int) -> int:
        cols = self.available_columns(["active"])
        variants_true = ["YES", "Yes ", "1", "true", "TRUE"]
        variants_false = ["NO", "No ", "0", "false", "FALSE"]
        done = 0
        for _ in range(n):
            cell = self.pick_cell(cols)
            if not cell:
                break
            idx, col = cell
            clean = self.dirty_df.at[idx, col]
            dirty = self.rng.choice(variants_true if bool(clean) else variants_false)
            self.dirty_df.at[idx, col] = dirty
            self.add_manifest(idx, col, "boolean_variants", clean, dirty, scope="cell", affected_base_row_id=idx, dirty_row_id=idx)
            done += 1
        return done

    def inject_mixed_date_formats(self, n: int) -> int:
        cols = self.available_columns(["signup_date", "last_login"])
        formats = ["%d/%m/%Y", "%m-%d-%Y", "%Y/%m/%d", "%d.%m.%Y"]
        done = 0
        for _ in range(n):
            cell = self.pick_cell(cols)
            if not cell:
                break
            idx, col = cell
            clean = self.dirty_df.at[idx, col]
            try:
                date_obj = pd.to_datetime(clean)
                dirty = date_obj.strftime(self.rng.choice(formats))
            except Exception:
                continue
            self.dirty_df.at[idx, col] = dirty
            self.add_manifest(idx, col, "mixed_date_formats", clean, dirty, scope="cell", affected_base_row_id=idx, dirty_row_id=idx)
            done += 1
        return done

    def inject_simple_outliers(self, n: int) -> int:
        cols = self.available_columns(["amount", "score", "support_tickets"])
        done = 0
        for _ in range(n):
            cell = self.pick_cell(cols)
            if not cell:
                break
            idx, col = cell
            clean = self.dirty_df.at[idx, col]
            try:
                if col == "support_tickets":
                    dirty = int(float(clean)) + self.rng.randint(30, 100)
                else:
                    dirty = round(float(clean) * self.rng.uniform(12, 40), 2)
            except Exception:
                continue
            self.dirty_df.at[idx, col] = dirty
            self.add_manifest(idx, col, "simple_outliers", clean, dirty, scope="cell", affected_base_row_id=idx, dirty_row_id=idx)
            done += 1
        return done

    def inject_negative_ages(self, n: int) -> int:
        cols = self.available_columns(["age"])
        done = 0
        for _ in range(n):
            cell = self.pick_cell(cols)
            if not cell:
                break
            idx, col = cell
            clean = self.dirty_df.at[idx, col]
            dirty = -abs(int(clean))
            self.dirty_df.at[idx, col] = dirty
            self.add_manifest(idx, col, "negative_ages", clean, dirty, scope="cell", affected_base_row_id=idx, dirty_row_id=idx)
            done += 1
        return done

    def inject_country_variants(self, n: int) -> int:
        cols = self.available_columns(["country"])
        variants = {
            "FR": ["fr", "France", " FR "],
            "PL": ["pl", "Poland", " PL "],
            "DE": ["de", "Germany", " DE "],
            "ES": ["es", "Spain", " ES "],
            "UK": ["uk", "United Kingdom", " UK "],
        }
        done = 0
        for _ in range(n):
            cell = self.pick_cell(cols)
            if not cell:
                break
            idx, col = cell
            clean = str(self.dirty_df.at[idx, col])
            dirty = self.rng.choice(variants.get(clean, [clean.lower()]))
            self.dirty_df.at[idx, col] = dirty
            self.add_manifest(idx, col, "country_variants", clean, dirty, scope="cell", affected_base_row_id=idx, dirty_row_id=idx)
            done += 1
        return done

    def inject_invalid_emails(self, n: int) -> int:
        cols = self.available_columns(["email"])
        done = 0
        for _ in range(n):
            cell = self.pick_cell(cols)
            if not cell:
                break
            idx, col = cell
            clean = str(self.dirty_df.at[idx, col])
            dirty = clean.replace("@", " at ") if self.rng.random() < 0.5 else clean.split("@")[0]
            self.dirty_df.at[idx, col] = dirty
            self.add_manifest(idx, col, "invalid_emails", clean, dirty, scope="cell", affected_base_row_id=idx, dirty_row_id=idx)
            done += 1
        return done

    def inject_future_dates(self, n: int) -> int:
        cols = self.available_columns(["signup_date", "last_login"])
        done = 0
        for _ in range(n):
            cell = self.pick_cell(cols)
            if not cell:
                break
            idx, col = cell
            clean = self.dirty_df.at[idx, col]
            dirty = (datetime.now() + timedelta(days=self.rng.randint(30, 900))).date().isoformat()
            self.dirty_df.at[idx, col] = dirty
            self.add_manifest(idx, col, "future_dates", clean, dirty, scope="cell", affected_base_row_id=idx, dirty_row_id=idx)
            done += 1
        return done

    def inject_corrupted_text_values(self, n: int) -> int:
        cols = self.available_columns(["first_name", "last_name", "email", "category", "city", "plan", "source", "notes"])
        corruptions = ["###ERROR###", "�INVALID�", "@@@", "N/A???", "###NULL###"]
        done = 0
        for _ in range(n):
            cell = self.pick_cell(cols)
            if not cell:
                break
            idx, col = cell
            clean = self.dirty_df.at[idx, col]
            dirty = self.rng.choice(corruptions)
            self.dirty_df.at[idx, col] = dirty
            self.add_manifest(idx, col, "corrupted_text_values", clean, dirty, scope="cell", affected_base_row_id=idx, dirty_row_id=idx)
            done += 1
        return done

    def inject_partial_duplicates(self, n: int) -> int:
        if self.dirty_df.empty:
            return 0

        done = 0
        for _ in range(n):
            source_idx = self.pick_source_row_for_row_event("partial_duplicates")
            if source_idx is None:
                break
            duplicate = self.clean_df.iloc[[source_idx]].copy()
            new_idx = len(self.dirty_df)
            if "id" in duplicate.columns:
                duplicate.loc[:, "id"] = int(pd.to_numeric(self.dirty_df["id"], errors="coerce").max()) + 1 if "id" in self.dirty_df.columns else new_idx + 1
            if "email" in duplicate.columns:
                duplicate.loc[:, "email"] = f"partial_duplicate_{new_idx}@example.com"
            self.dirty_df = pd.concat([self.dirty_df, duplicate], ignore_index=True)
            recorded = self.add_manifest(
                new_idx,
                "__row__",
                "partial_duplicates",
                "unique row",
                f"near duplicate row copied from base row {source_idx}",
                scope="row",
                affected_base_row_id=source_idx,
                dirty_row_id=new_idx,
            )
            if recorded:
                done += 1
        return done

    def inject_multi_column_date_inconsistency(self, n: int) -> int:
        if "signup_date" not in self.dirty_df.columns or "last_login" not in self.dirty_df.columns:
            return 0

        done = 0
        for _ in range(n):
            row_pool = [i for i in self.affected_base_indices if i < len(self.dirty_df)]
            if not row_pool:
                break
            idx = self.rng.choice(row_pool)
            col = "last_login"
            if (idx, col) in self.used_cells:
                continue
            self.used_cells.add((idx, col))
            clean = self.dirty_df.at[idx, col]
            signup = pd.to_datetime(self.dirty_df.at[idx, "signup_date"], errors="coerce")
            if pd.isna(signup):
                continue
            dirty = (signup - timedelta(days=self.rng.randint(1, 90))).date().isoformat()
            self.dirty_df.at[idx, col] = dirty
            recorded = self.add_manifest(idx, col, "multi_column_date_inconsistency", clean, dirty, scope="cell", affected_base_row_id=idx, dirty_row_id=idx)
            if recorded:
                done += 1
        return done

    def inject_irrelevant_noise_columns(self, n: int) -> int:
        done = 0
        for i in range(n):
            col = f"noise_column_{i + 1}"
            if col in self.dirty_df.columns:
                continue
            values = [self.rng.choice(["x", "unknown", "???", "", "not useful"]) for _ in range(len(self.dirty_df))]
            self.dirty_df[col] = values
            self.add_manifest("__columns__", col, "irrelevant_noise_columns", "column should not exist", "irrelevant noisy column", scope="schema_column")
            done += 1
        return done

    def apply(self, counts: Dict[str, int]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        dispatch = {
            "missing_values": self.inject_missing_values,
            "full_duplicates": self.inject_full_duplicates,
            "leading_trailing_spaces": self.inject_leading_trailing_spaces,
            "dirty_column_names": self.inject_dirty_column_names,
            "decimal_commas": self.inject_decimal_commas,
            "boolean_variants": self.inject_boolean_variants,
            "mixed_date_formats": self.inject_mixed_date_formats,
            "simple_outliers": self.inject_simple_outliers,
            "negative_ages": self.inject_negative_ages,
            "country_variants": self.inject_country_variants,
            "invalid_emails": self.inject_invalid_emails,
            "future_dates": self.inject_future_dates,
            "corrupted_text_values": self.inject_corrupted_text_values,
            "partial_duplicates": self.inject_partial_duplicates,
            "multi_column_date_inconsistency": self.inject_multi_column_date_inconsistency,
            "irrelevant_noise_columns": self.inject_irrelevant_noise_columns,
        }

        # Apply column-name and noise-column errors last so earlier cell-level injectors
        # can still find the expected base columns.
        delayed = {"dirty_column_names", "irrelevant_noise_columns"}
        ordered_error_types = [e for e in counts.keys() if e not in delayed]
        ordered_error_types.extend([e for e in counts.keys() if e in delayed])

        actual_counts = {}
        for error_type in ordered_error_types:
            requested = counts.get(error_type, 0)
            if requested <= 0:
                actual_counts[error_type] = 0
                continue
            actual_counts[error_type] = dispatch[error_type](requested)

        manifest_df = pd.DataFrame(self.manifest)
        return self.dirty_df, manifest_df


def write_outputs(output_dir: Path, clean_df: pd.DataFrame, dirty_df: pd.DataFrame, manifest_df: pd.DataFrame, spec: Dict[str, Any]) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    clean_path = output_dir / "demo_clean_dataset.csv"
    dirty_path = output_dir / "demo_dirty_dataset.csv"
    spec_path = output_dir / "demo_dataset_spec.json"
    manifest_path = output_dir / "demo_error_manifest.csv"
    readme_path = output_dir / "README.md"

    clean_df.to_csv(clean_path, index=False, encoding="utf-8")
    dirty_df.to_csv(dirty_path, index=False, encoding="utf-8")
    manifest_df.to_csv(manifest_path, index=False, encoding="utf-8")
    spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")

    readme = f"""# Controlled Dirty Dataset

Generated by {APP_NAME} v{APP_VERSION}

## v4 counting model

- One manifest row = one unique injected error event.
- The same `(row_id, column, error_type)` is not counted twice.
- Multiple different errors can exist on the same affected row.
- The affected-rows percentage controls how many base rows can receive row/cell-level errors.
- Schema-level errors such as dirty column names and noise columns are counted separately.

## Files

- `demo_clean_dataset.csv`: clean reference dataset
- `demo_dirty_dataset.csv`: dirty dataset to upload into AI Data Cleaner
- `demo_dataset_spec.json`: readable dataset characteristics
- `demo_error_manifest.csv`: ground truth of injected errors

## Dataset summary

- Rows clean: {len(clean_df)}
- Rows dirty: {len(dirty_df)}
- Columns clean: {len(clean_df.columns)}
- Columns dirty: {len(dirty_df.columns)}
- Generated at: {spec.get("generated_at")}

## Usage

1. Upload `demo_dirty_dataset.csv` into AI Data Cleaner.
2. Run analysis and cleaning.
3. Compare results with `demo_error_manifest.csv`.
4. Compare final cleaned output with `demo_clean_dataset.csv`.

"""
    readme_path.write_text(readme, encoding="utf-8")

    return {
        "clean": clean_path,
        "dirty": dirty_path,
        "spec": spec_path,
        "manifest": manifest_path,
        "readme": readme_path,
    }



class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1280x760")
        self.minsize(1180, 700)

        self.output_dir = Path(__file__).resolve().parent / "generated_cases"
        self.result_queue: queue.Queue = queue.Queue()
        self.is_generating = False
        self._syncing_manual_values = False
        self._randomize_click_count = 0
        self._toggling_visibility = False  # prevents trace re-entry during hide/show
        self._editing_manual_header = False  # blocks refresh from overwriting header fields while user types
        # Unit-test mode state
        self._unit_test_snapshot: dict | None = None   # snapshot of settings before unit-test mode was enabled
        self.var_unit_test_mode   = tk.BooleanVar(value=False)
        self.var_unit_test_type   = tk.StringVar(value="level_1")
        self.var_unit_test_subtype = tk.StringVar(value="missing_values")

        self.var_profile = tk.StringVar(value="DEMO_SMALL")
        self.var_rows = tk.StringVar(value="300")
        self.var_columns = tk.StringVar(value="12")
        self.var_affected_rows_pct = tk.StringVar(value="20")
        self.var_affected_rows_count = tk.StringVar(value="60")
        self.var_seed = tk.StringVar(value="42")
        self.var_total_errors = tk.StringVar(value="168")

        self.var_use_percentages = tk.BooleanVar(value=True)
        self.var_show_details = tk.BooleanVar(value=False)
        self.var_pct_l1 = tk.StringVar(value=str(DEFAULT_PERCENTAGES["level_1"]))
        self.var_pct_l2 = tk.StringVar(value=str(DEFAULT_PERCENTAGES["level_2"]))
        self.var_pct_l3 = tk.StringVar(value=str(DEFAULT_PERCENTAGES["level_3"]))
        self.var_output_dir = tk.StringVar(value=str(self.output_dir))
        self.var_status = tk.StringVar(value="Ready")
        self.var_distribution_summary = tk.StringVar(value="")

        self.manual_vars: Dict[str, tk.StringVar] = {
            error_type: tk.StringVar(value="0")
            for group in ERROR_GROUPS.values()
            for error_type in group
        }
        self.manual_entries: Dict[str, ttk.Entry] = {}

        self._build_ui()
        self._bind_updates()
        self.apply_profile_defaults("DEMO_SMALL")
        self.refresh_preview()
        self.after(150, self._poll_results)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)

        title = ttk.Label(root, text="Controlled Dataset Generator", font=("Segoe UI", 24, "bold"))
        title.pack(anchor="w")

        subtitle = ttk.Label(
            root,
            text="Generate one clean CSV, one dirty CSV, one JSON specification and one error manifest for testing AI Data Cleaner.",
            font=("Segoe UI", 10)
        )
        subtitle.pack(anchor="w", pady=(4, 12))

        profile_frame = ttk.LabelFrame(root, text="Dataset profile", padding=10)
        profile_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(profile_frame, text="Profile").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.cmb_profile = ttk.Combobox(
            profile_frame,
            textvariable=self.var_profile,
            values=list(PROFILE_PRESETS.keys()),
            state="readonly",
            width=24,
        )
        self.cmb_profile.grid(row=0, column=1, sticky="w", padx=(0, 26))

        ttk.Label(profile_frame, text="Rows").grid(row=0, column=2, sticky="w", padx=(0, 8))
        _e_rows = ttk.Entry(profile_frame, textvariable=self.var_rows, width=12)
        _e_rows.grid(row=0, column=3, sticky="w", padx=(0, 26))

        ttk.Label(profile_frame, text="Columns").grid(row=0, column=4, sticky="w", padx=(0, 8))
        _e_cols = ttk.Entry(profile_frame, textvariable=self.var_columns, width=10)
        _e_cols.grid(row=0, column=5, sticky="w", padx=(0, 20))

        ttk.Label(profile_frame, text="Affected rows %").grid(row=0, column=6, sticky="w", padx=(0, 8))
        _e_aff = ttk.Entry(profile_frame, textvariable=self.var_affected_rows_pct, width=8)
        _e_aff.grid(row=0, column=7, sticky="w", padx=(0, 10))
        ttk.Label(profile_frame, textvariable=self.var_affected_rows_count, font=("Segoe UI", 9, "bold")).grid(row=0, column=8, sticky="w", padx=(0, 20))

        ttk.Label(profile_frame, text="Seed").grid(row=0, column=9, sticky="w", padx=(0, 8))
        _e_seed = ttk.Entry(profile_frame, textvariable=self.var_seed, width=10)
        _e_seed.grid(row=0, column=10, sticky="w", padx=(0, 20))
        self._profile_entries = [_e_rows, _e_cols, _e_aff, _e_seed]

        # Main action placed near the dataset profile so it remains visible.
        profile_frame.columnconfigure(11, weight=1)
        self.btn_generate = tk.Button(
            profile_frame,
            text="GENERATE CONTROLLED DATASET",
            command=self.generate_clicked,
            bg="#d7ecff",
            fg="#0f3556",
            activebackground="#b9dcff",
            activeforeground="#0f3556",
            relief="raised",
            borderwidth=1,
            font=("Segoe UI", 11, "bold"),
            padx=22,
            pady=7,
            cursor="hand2",
        )
        self.btn_generate.grid(row=0, column=11, sticky="e", padx=(10, 0))

        output_frame = ttk.LabelFrame(root, text="Output", padding=10)
        output_frame.pack(fill="x", pady=(0, 10))
        ttk.Entry(output_frame, textvariable=self.var_output_dir).pack(side="left", fill="x", expand=True, padx=(0, 12))
        ttk.Button(output_frame, text="Choose folder", command=self.browse_output).pack(side="right")

        mode = ttk.LabelFrame(root, text="Error distribution mode", padding=10)
        mode.pack(fill="x", pady=(0, 10))

        ttk.Checkbutton(
            mode,
            text="Use percentage distribution by error difficulty (default: 65% Type 1, 25% Type 2, 10% Type 3)",
            variable=self.var_use_percentages,
            command=self.refresh_preview,
        ).grid(row=0, column=0, columnspan=7, sticky="w", pady=(0, 8))

        # Unit-test mode toggle — placed right of the percentage checkbutton
        self.chk_unit_test = ttk.Checkbutton(
            mode,
            text="🧪 Unit test mode",
            variable=self.var_unit_test_mode,
            command=self._on_unit_test_toggled,
        )
        self.chk_unit_test.grid(row=0, column=7, columnspan=3, sticky="e", padx=(12, 0), pady=(0, 8))

        # Unit-test type dropdown (hidden until unit-test mode is on)
        self.unit_test_type_frame = ttk.Frame(mode)
        self.unit_test_type_frame.grid(row=0, column=10, columnspan=4, sticky="e", padx=(8, 0), pady=(0, 8))
        ttk.Label(self.unit_test_type_frame, text="Type:").pack(side="left")
        self.cmb_unit_test_type = ttk.Combobox(
            self.unit_test_type_frame,
            textvariable=self.var_unit_test_type,
            values=list(UNIT_TEST_TYPE_LABELS.values()),
            state="readonly",
            width=22,
        )
        self.cmb_unit_test_type.pack(side="left", padx=(4, 8))
        # Map display label → key for var_unit_test_type
        self._unit_test_type_keys = list(UNIT_TEST_TYPE_LABELS.keys())
        self._unit_test_type_display = list(UNIT_TEST_TYPE_LABELS.values())
        # Set default display value
        self.var_unit_test_type.set(self._unit_test_type_display[0])
        ttk.Label(self.unit_test_type_frame, text="Error:").pack(side="left")
        # _unit_test_subtype_keys: parallel list of error_type keys for the current level
        self._unit_test_subtype_keys: List[str] = []
        self.cmb_unit_test_subtype = ttk.Combobox(
            self.unit_test_type_frame,
            textvariable=self.var_unit_test_subtype,
            state="readonly",
            width=22,
        )
        self.cmb_unit_test_subtype.pack(side="left", padx=(4, 0))
        self.unit_test_type_frame.grid_remove()  # hidden by default

        ttk.Label(mode, text="Total unique error events").grid(row=1, column=0, sticky="w")
        self.entry_total_errors = ttk.Entry(mode, textvariable=self.var_total_errors, width=10)
        self.entry_total_errors.grid(row=1, column=1, padx=(8, 24), sticky="w")

        ttk.Label(mode, text="Type 1 / simple %").grid(row=1, column=2, sticky="w")
        self.entry_pct_l1 = ttk.Entry(mode, textvariable=self.var_pct_l1, width=8)
        self.entry_pct_l1.grid(row=1, column=3, padx=(8, 24), sticky="w")

        ttk.Label(mode, text="Type 2 / intermediate %").grid(row=1, column=4, sticky="w")
        self.entry_pct_l2 = ttk.Entry(mode, textvariable=self.var_pct_l2, width=8)
        self.entry_pct_l2.grid(row=1, column=5, padx=(8, 24), sticky="w")

        ttk.Label(mode, text="Type 3 / advanced %").grid(row=1, column=6, sticky="w")
        self.entry_pct_l3 = ttk.Entry(mode, textvariable=self.var_pct_l3, width=8)
        self.entry_pct_l3.grid(row=1, column=7, padx=(8, 0), sticky="w")

        ttk.Label(mode, textvariable=self.var_distribution_summary, font=("Segoe UI", 9, "bold")).grid(
            row=2, column=0, columnspan=8, sticky="w", pady=(9, 0)
        )

        toggle_row = ttk.Frame(root)
        toggle_row.pack(fill="x", pady=(0, 8))
        self.btn_toggle_details = ttk.Button(toggle_row, text="Show exact error distribution", command=self.toggle_details)
        self.btn_toggle_details.pack(side="left")
        self.btn_randomize = tk.Button(
            toggle_row,
            text="🎲 Random distribution",
            command=self.randomize_distribution,
            bg="#f0e6ff",
            fg="#3b0764",
            activebackground="#ddd6fe",
            activeforeground="#3b0764",
            relief="raised",
            borderwidth=1,
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=3,
            cursor="hand2",
        )
        self.btn_randomize.pack(side="left", padx=(10, 0))
        ttk.Label(
            toggle_row,
            text="Hidden by default to keep the generator compact. Uncheck percentage mode to edit exact counts.",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(12, 0))

        self.counts_frame = ttk.LabelFrame(root, text="Error characteristics — exact numeric distribution", padding=10)
        # Packed/unpacked by refresh_counts_visibility(). Hidden by default.

        for col_idx, level in enumerate(["level_1", "level_2", "level_3"]):
            error_types = ERROR_GROUPS[level]
            group_frame = ttk.Frame(self.counts_frame, padding=(8, 2))
            group_frame.grid(row=0, column=col_idx, sticky="nsew", padx=(0, 18))
            self.counts_frame.columnconfigure(col_idx, weight=1)

            title = {
                "level_1": "Type 1 — Simple errors",
                "level_2": "Type 2 — Intermediate errors",
                "level_3": "Type 3 — Advanced errors",
            }[level]
            ttk.Label(group_frame, text=title, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

            for row_idx, error_type in enumerate(error_types, start=1):
                ttk.Label(group_frame, text=ERROR_LABELS[error_type], width=34).grid(row=row_idx, column=0, sticky="w", pady=2)
                entry = ttk.Entry(group_frame, textvariable=self.manual_vars[error_type], width=8)
                entry.grid(row=row_idx, column=1, sticky="w", pady=2)
                self.manual_entries[error_type] = entry

        self.generated_frame = ttk.LabelFrame(root, text="Generated files", padding=10)
        self.generated_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(self.generated_frame, text=GENERATED_FILES_TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w")

        bottom = ttk.Frame(root)
        bottom.pack(fill="x", pady=(0, 8))
        ttk.Label(bottom, textvariable=self.var_status, font=("Segoe UI", 10, "bold")).pack(side="right")

        self.progress = ttk.Progressbar(root, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(0, 8))

        footer = ttk.Label(root, text=f"{APP_NAME} v{APP_VERSION} — local only, no API, no Azure, no internet connection required")
        footer.pack(anchor="w")

    def set_button_visual_state(self, state: str) -> None:
        """Update the main generate button color based on the last generation state."""
        if not hasattr(self, "btn_generate"):
            return
        styles = {
            "ready": {"bg": "#d7ecff", "fg": "#0f3556", "activebackground": "#b9dcff", "text": "GENERATE CONTROLLED DATASET", "state": "normal"},
            "running": {"bg": "#fff3cd", "fg": "#5f4300", "activebackground": "#ffe69c", "text": "GENERATING...", "state": "disabled"},
            "success": {"bg": "#c9f7d2", "fg": "#155724", "activebackground": "#a9eeb8", "text": "GENERATE CONTROLLED DATASET", "state": "normal"},
            "error": {"bg": "#ffd2d2", "fg": "#842029", "activebackground": "#ffb6b6", "text": "GENERATE CONTROLLED DATASET", "state": "normal"},
        }
        cfg = styles.get(state, styles["ready"])
        self.btn_generate.config(**cfg)

    def toggle_details(self) -> None:
        # Guard against re-entry through manual_vars traces that fire when
        # refresh_preview writes back calculated counts into the fields.
        if self._toggling_visibility:
            return
        self._toggling_visibility = True
        try:
            self.var_show_details.set(not self.var_show_details.get())
            self._apply_counts_visibility()
        finally:
            self._toggling_visibility = False

    def _apply_counts_visibility(self) -> None:
        """Core show/hide logic.

        Priority rules:
        1. If _toggling_visibility guard is active, this is a direct user click —
           honour var_show_details exactly, ignore manual_mode override.
        2. Otherwise (called from refresh_preview traces), use the combined rule:
           show if explicitly requested OR if manual mode forces the panel open.
        """
        if not hasattr(self, "counts_frame") or not hasattr(self, "btn_toggle_details"):
            return
        explicitly_shown = self.var_show_details.get()
        manual_mode = not self.var_use_percentages.get()
        if self._toggling_visibility:
            # Direct user click: respect the flag exactly, no override.
            should_show = explicitly_shown
        else:
            # Called from a trace (refresh_preview, randomize, profile change).
            # Manual mode always forces the panel open; otherwise follow the flag.
            should_show = explicitly_shown or manual_mode
        if should_show:
            if not self.counts_frame.winfo_manager():
                self.counts_frame.pack(fill="x", pady=(0, 10), before=self.generated_frame)
            self.btn_toggle_details.config(text="Hide exact error distribution")
        else:
            if self.counts_frame.winfo_manager():
                self.counts_frame.pack_forget()
            self.btn_toggle_details.config(text="Show exact error distribution")

    def refresh_counts_visibility(self) -> None:
        """Called by refresh_preview. Resets var_show_details when switching to
        percentage mode so the panel closes if the user had it open manually."""
        if not hasattr(self, "counts_frame") or not hasattr(self, "btn_toggle_details"):
            return
        # When switching back to percentage mode, collapse the panel unless the
        # user explicitly opened it in this session.
        if self.var_use_percentages.get() and not self.var_show_details.get():
            pass  # already collapsed — nothing to do
        self._apply_counts_visibility()

    def _bind_updates(self) -> None:
        self.var_profile.trace_add("write", lambda *_: self.on_profile_change())

        # Dataset structure vars always just refresh preview.
        for var in [self.var_rows, self.var_columns, self.var_affected_rows_pct, self.var_seed]:
            var.trace_add("write", lambda *_: self.refresh_preview())

        # Header error vars: set flag so refresh_preview does not overwrite them
        # while the user is typing in manual mode.
        def _header_changed(*_):
            if not self._syncing_manual_values:
                self._editing_manual_header = True
                try:
                    self.refresh_preview()
                finally:
                    self._editing_manual_header = False

        for var in [self.var_total_errors, self.var_pct_l1, self.var_pct_l2, self.var_pct_l3]:
            var.trace_add("write", _header_changed)

        for var in self.manual_vars.values():
            var.trace_add("write", lambda *_: self._manual_value_changed())

        self.var_use_percentages.trace_add("write", lambda *_: self.refresh_preview())

        # Unit-test mode combobox traces
        self.var_unit_test_type.trace_add("write", self._on_unit_test_type_changed)
        self.var_unit_test_subtype.trace_add("write", self._on_unit_test_subtype_changed)

    def _manual_value_changed(self) -> None:
        if not self._syncing_manual_values:
            self.refresh_preview()

    def on_profile_change(self) -> None:
        profile = self.var_profile.get()
        if profile in PROFILE_PRESETS and profile != "CUSTOM":
            self.apply_profile_defaults(profile)
        self.refresh_preview()

    def apply_profile_defaults(self, profile: str) -> None:
        preset = PROFILE_PRESETS.get(profile, PROFILE_PRESETS["DEMO_SMALL"])
        self.var_rows.set(str(preset["rows"]))
        self.var_columns.set(str(preset["columns"]))
        self.var_affected_rows_pct.set(str(preset.get("affected_rows_pct", 20)))
        self.var_total_errors.set(str(preset["total_errors"]))
        self.var_pct_l1.set(str(preset["type_1_pct"]))
        self.var_pct_l2.set(str(preset["type_2_pct"]))
        self.var_pct_l3.set(str(preset["type_3_pct"]))

    def browse_output(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.var_output_dir.get())
        if selected:
            self.var_output_dir.set(selected)

    def current_counts(self) -> Dict[str, int]:
        if self.var_use_percentages.get():
            total = safe_int(self.var_total_errors.get(), default=0, minimum=0, maximum=2_000_000)
            p1 = safe_pct(self.var_pct_l1.get(), DEFAULT_PERCENTAGES["level_1"])
            p2 = safe_pct(self.var_pct_l2.get(), DEFAULT_PERCENTAGES["level_2"])
            p3 = safe_pct(self.var_pct_l3.get(), DEFAULT_PERCENTAGES["level_3"])
            return counts_from_percentages(total, p1, p2, p3, seed=safe_int(self.var_seed.get(), default=42), columns=safe_int(self.var_columns.get(), default=12, minimum=8, maximum=20))

        return {
            error_type: safe_int(var.get(), default=0, minimum=0, maximum=2_000_000)
            for error_type, var in self.manual_vars.items()
        }

    def refresh_preview(self) -> None:
        if not hasattr(self, "manual_entries"):
            return

        counts = self.current_counts()

        if self.var_use_percentages.get():
            self._syncing_manual_values = True
            try:
                for error_type, value in counts.items():
                    self.manual_vars[error_type].set(str(value))
            finally:
                self._syncing_manual_values = False

        use_pct = self.var_use_percentages.get()

        # Sub-type count entries: read-only in percentage mode, editable in manual mode.
        for error_type, entry in self.manual_entries.items():
            entry.config(state="readonly" if use_pct else "normal")

        # Header entries (total, pct l1/l2/l3): editable in both modes.
        # In manual mode they are the source of truth typed by the user —
        # never overwrite them from a trace while the user is editing.
        for entry in (self.entry_total_errors, self.entry_pct_l1, self.entry_pct_l2, self.entry_pct_l3):
            if hasattr(self, entry.winfo_name().__class__.__name__):
                pass  # always keep normal
            entry.config(state="normal")

        self.refresh_counts_visibility()

        level_totals = counts_by_difficulty(counts)
        requested_total = sum(counts.values())

        rows = safe_int(self.var_rows.get(), default=300, minimum=1, maximum=1_000_000)
        affected_pct = safe_pct(self.var_affected_rows_pct.get(), 20)
        affected_count = int(round(rows * affected_pct / 100))
        self.var_affected_rows_count.set(f"= {affected_count} rows")

        if not use_pct and not self._syncing_manual_values and not self._editing_manual_header:
            # In manual mode, sub-type counts are the source of truth.
            # Recalculate total and percentages from sub-type values ONLY
            # when the change did NOT originate from a header field edit.
            self._syncing_manual_values = True
            try:
                self.var_total_errors.set(str(requested_total))
                if requested_total > 0:
                    self.var_pct_l1.set(str(round(level_totals['level_1'] * 100 / requested_total)))
                    self.var_pct_l2.set(str(round(level_totals['level_2'] * 100 / requested_total)))
                    self.var_pct_l3.set(str(round(level_totals['level_3'] * 100 / requested_total)))
            finally:
                self._syncing_manual_values = False

        pct_sum = (
            safe_pct(self.var_pct_l1.get(), 65)
            + safe_pct(self.var_pct_l2.get(), 25)
            + safe_pct(self.var_pct_l3.get(), 10)
        )
        warning = " | Warning: percentages will be normalized" if self.var_use_percentages.get() and pct_sum != 100 else ""
        mode = "percentage mode" if self.var_use_percentages.get() else "manual mode"
        row_density = round(requested_total / affected_count, 2) if affected_count else 0
        self.var_distribution_summary.set(
            f"Calculated distribution ({mode}): Type 1 = {level_totals['level_1']} | "
            f"Type 2 = {level_totals['level_2']} | Type 3 = {level_totals['level_3']} | "
            f"Total = {requested_total} | Affected rows = {affected_count}/{rows} "
            f"({affected_pct}%) | Avg errors per affected row ≈ {row_density}{warning}"
        )

    def randomize_distribution(self) -> None:
        """Re-distribute errors randomly across sub-types using current % settings.

        Works in both percentage mode and manual mode.
        In both cases the Type 1 / Type 2 / Type 3 percentages are read from the
        three % fields and normalised to 100 before distributing.
        Each click uses a fresh seed so the result changes every time.
        """
        total = safe_int(self.var_total_errors.get(), default=0, minimum=0)
        if total <= 0:
            messagebox.showwarning(
                "Random distribution",
                "Total unique error events is 0. Set a total before randomizing.",
            )
            return

        p1 = safe_pct(self.var_pct_l1.get(), DEFAULT_PERCENTAGES["level_1"])
        p2 = safe_pct(self.var_pct_l2.get(), DEFAULT_PERCENTAGES["level_2"])
        p3 = safe_pct(self.var_pct_l3.get(), DEFAULT_PERCENTAGES["level_3"])
        columns = safe_int(self.var_columns.get(), default=12, minimum=8, maximum=20)

        self._randomize_click_count += 1
        new_counts = randomize_counts_from_percentages(
            total, p1, p2, p3, columns, click_index=self._randomize_click_count
        )

        # Write new counts into manual fields and make the panel visible.
        self._syncing_manual_values = True
        try:
            for error_type, value in new_counts.items():
                if error_type in self.manual_vars:
                    self.manual_vars[error_type].set(str(value))
        finally:
            self._syncing_manual_values = False

        # Show the details panel so the user can see the new distribution.
        self.var_show_details.set(True)
        self._apply_counts_visibility()

        # In percentage mode keep entries read-only; in manual mode they stay editable.
        for error_type, entry in self.manual_entries.items():
            entry.config(state="readonly" if self.var_use_percentages.get() else "normal")

        # Refresh the summary line.
        self.refresh_preview()

    # ── Unit-test mode helpers ─────────────────────────────────────────────

    def _ut_level_key(self) -> str:
        """Return the level key (level_1/2/3) from the current type display value."""
        display = self.var_unit_test_type.get()
        try:
            idx = self._unit_test_type_display.index(display)
            return self._unit_test_type_keys[idx]
        except (ValueError, AttributeError):
            return "level_1"

    def _on_unit_test_type_changed(self, *_) -> None:
        """Refresh subtype combobox when the type dropdown changes."""
        if not self.var_unit_test_mode.get():
            return
        level = self._ut_level_key()
        keys = ERROR_GROUPS.get(level, [])
        self._unit_test_subtype_keys = keys
        labels = [ERROR_LABELS.get(k, k) for k in keys]
        self.cmb_unit_test_subtype.configure(values=labels)
        if labels:
            self.var_unit_test_subtype.set(labels[0])
        self._apply_unit_test_settings()

    def _on_unit_test_subtype_changed(self, *_) -> None:
        """Apply settings when the error subtype changes."""
        if self.var_unit_test_mode.get():
            self._apply_unit_test_settings()
            self._update_unit_test_output_path()

    def _ut_subtype_key(self) -> str:
        """Return the error_type key from the current subtype display value."""
        display = self.var_unit_test_subtype.get()
        keys = getattr(self, "_unit_test_subtype_keys", [])
        for k in keys:
            if ERROR_LABELS.get(k, k) == display:
                return k
        return keys[0] if keys else ""

    def _on_unit_test_toggled(self) -> None:
        if self.var_unit_test_mode.get():
            self._enter_unit_test_mode()
        else:
            self._exit_unit_test_mode()

    def _enter_unit_test_mode(self) -> None:
        self._unit_test_snapshot = {
            "rows":             self.var_rows.get(),
            "columns":          self.var_columns.get(),
            "affected_rows_pct": self.var_affected_rows_pct.get(),
            "seed":             self.var_seed.get(),
            "total_errors":     self.var_total_errors.get(),
            "pct_l1":           self.var_pct_l1.get(),
            "pct_l2":           self.var_pct_l2.get(),
            "pct_l3":           self.var_pct_l3.get(),
            "use_percentages":  self.var_use_percentages.get(),
            "output_dir":       self.var_output_dir.get(),
            "manual_counts":    {k: v.get() for k, v in self.manual_vars.items()},
        }
        self.unit_test_type_frame.grid()
        # Populate type combobox
        self.cmb_unit_test_type.configure(values=self._unit_test_type_display)
        self.var_unit_test_type.set(self._unit_test_type_display[0])
        # Populate subtype combobox for level_1
        level = self._ut_level_key()
        keys = ERROR_GROUPS.get(level, [])
        self._unit_test_subtype_keys = keys
        labels = [ERROR_LABELS.get(k, k) for k in keys]
        self.cmb_unit_test_subtype.configure(values=labels)
        if labels:
            self.var_unit_test_subtype.set(labels[0])
        self._set_unit_test_lock(locked=True)
        self._apply_unit_test_settings()

    def _exit_unit_test_mode(self) -> None:
        self.unit_test_type_frame.grid_remove()
        self._set_unit_test_lock(locked=False)
        if self._unit_test_snapshot is not None:
            snap = self._unit_test_snapshot
            self._syncing_manual_values = True
            try:
                self.var_rows.set(snap["rows"])
                self.var_columns.set(snap["columns"])
                self.var_affected_rows_pct.set(snap["affected_rows_pct"])
                self.var_seed.set(snap["seed"])
                self.var_total_errors.set(snap["total_errors"])
                self.var_pct_l1.set(snap["pct_l1"])
                self.var_pct_l2.set(snap["pct_l2"])
                self.var_pct_l3.set(snap["pct_l3"])
                self.var_use_percentages.set(snap["use_percentages"])
                self.var_output_dir.set(snap["output_dir"])
                for k, v in snap["manual_counts"].items():
                    if k in self.manual_vars:
                        self.manual_vars[k].set(v)
            finally:
                self._syncing_manual_values = False
            self._unit_test_snapshot = None
        self.refresh_preview()

    def _set_unit_test_lock(self, locked: bool) -> None:
        ro = "readonly" if locked else "normal"
        dis = "disabled" if locked else "normal"
        self.cmb_profile.configure(state=ro)
        for entry in (self.entry_total_errors, self.entry_pct_l1, self.entry_pct_l2, self.entry_pct_l3):
            entry.configure(state=ro)
        if hasattr(self, "_profile_entries"):
            for e in self._profile_entries:
                e.configure(state=dis)
        for entry in self.manual_entries.values():
            entry.configure(state=ro)
        self.btn_randomize.configure(state=dis)

    def _apply_unit_test_settings(self) -> None:
        level_key   = self._ut_level_key()
        subtype_key = self._ut_subtype_key()
        if not subtype_key:
            return
        self._syncing_manual_values = True
        try:
            self.var_rows.set(str(UNIT_TEST_ROWS))
            self.var_columns.set(str(UNIT_TEST_COLUMNS))
            self.var_affected_rows_pct.set(str(UNIT_TEST_AFFECTED_PCT))
            self.var_total_errors.set(str(UNIT_TEST_TOTAL))
            self.var_pct_l1.set("100" if level_key == "level_1" else "0")
            self.var_pct_l2.set("100" if level_key == "level_2" else "0")
            self.var_pct_l3.set("100" if level_key == "level_3" else "0")
            self.var_use_percentages.set(False)
            for et in self.manual_vars:
                self.manual_vars[et].set("100" if et == subtype_key else "0")
        finally:
            self._syncing_manual_values = False
        self._update_unit_test_output_path()
        self.refresh_preview()

    def _update_unit_test_output_path(self) -> None:
        level   = self._ut_level_key()
        subtype = self._ut_subtype_key()
        if not subtype:
            return
        type_num = {"level_1": "1", "level_2": "2", "level_3": "3"}.get(level, "1")
        short = UNIT_TEST_SHORTCODES.get(subtype, subtype)
        folder_name = f"Type{type_num}_{short}_Test100"
        base = self._unit_test_snapshot["output_dir"] if self._unit_test_snapshot else self.var_output_dir.get()
        base_path = Path(base)
        # If base is already a unit-test folder, go up one level
        if base_path.name.startswith("Type") and "_Test100" in base_path.name:
            base_path = base_path.parent
        new_path = base_path / folder_name
        self.var_output_dir.set(str(new_path))

    def generate_clicked(self) -> None:
        if self.is_generating:
            return

        rows = safe_int(self.var_rows.get(), default=300, minimum=1)
        columns = safe_int(self.var_columns.get(), default=12, minimum=8)
        affected_rows_pct = safe_pct(self.var_affected_rows_pct.get(), 20)
        affected_rows_count = int(round(rows * affected_rows_pct / 100))
        counts = self.current_counts()

        bound_warnings = validate_counts_against_bounds(counts, rows, columns, affected_rows_count)
        if bound_warnings:
            warning_text = (
                "The following values exceed the physical limits of this dataset.\n"
                "Generation will proceed but the actual injected counts will be lower "
                "than requested.\n\n"
                + "\n\n".join(f"• {w}" for w in bound_warnings)
                + "\n\nContinue anyway?"
            )
            proceed = messagebox.askyesno(
                "Input bounds warning",
                warning_text,
                icon="warning",
            )
            if not proceed:
                return

        self.is_generating = True
        self.set_button_visual_state("running")
        self.progress["value"] = 0
        self.var_status.set("Preparing generation")

        t = threading.Thread(target=self._worker_generate, daemon=True)
        t.start()

    def _worker_generate(self) -> None:
        try:
            total_seconds = random.uniform(5.0, 10.0)
            steps = 100
            for i in range(steps + 1):
                if i == 5:
                    self.result_queue.put(("STATUS", "Reading settings"))
                elif i == 25:
                    self.result_queue.put(("STATUS", "Generating clean reference dataset"))
                elif i == 50:
                    self.result_queue.put(("STATUS", "Injecting controlled errors"))
                elif i == 75:
                    self.result_queue.put(("STATUS", "Writing CSV, JSON and manifest files"))
                self.result_queue.put(("PROGRESS", i))
                time.sleep(total_seconds / steps)

            result = self._generate_outputs_now()
            self.result_queue.put(("SUCCESS", result))
        except Exception as e:
            self.result_queue.put(("ERROR", f"{type(e).__name__}: {e}"))

    def _generate_outputs_now(self) -> Dict[str, Path]:
        rows = safe_int(self.var_rows.get(), default=300, minimum=1, maximum=1_000_000)
        columns = safe_int(self.var_columns.get(), default=12, minimum=8, maximum=20)
        affected_rows_pct = safe_pct(self.var_affected_rows_pct.get(), 20)
        seed = safe_int(self.var_seed.get(), default=42, minimum=0, maximum=2_147_483_647)
        counts = self.current_counts()
        output_dir = Path(self.var_output_dir.get()).expanduser().resolve()

        clean_df = make_clean_dataset(rows, columns, seed)
        affected_base_indices = build_affected_rows(len(clean_df), affected_rows_pct, seed)
        injector = ErrorInjector(clean_df, seed + 1000, affected_base_indices)
        dirty_df, manifest_df = injector.apply(counts)

        actual_counts = manifest_df["error_type"].value_counts().to_dict() if not manifest_df.empty else {}
        level_counts = manifest_df["difficulty"].value_counts().to_dict() if not manifest_df.empty else {}
        scope_counts = manifest_df["scope"].value_counts().to_dict() if not manifest_df.empty and "scope" in manifest_df.columns else {}
        row_level_requested, schema_level_requested = split_counts_by_scope(counts)
        actual_row_level_counts = {k: v for k, v in actual_counts.items() if k in ROW_LEVEL_ERRORS}
        actual_schema_level_counts = {k: v for k, v in actual_counts.items() if k in SCHEMA_LEVEL_ERRORS}

        if not manifest_df.empty and "affected_base_row_id" in manifest_df.columns:
            affected_values = [x for x in manifest_df["affected_base_row_id"].astype(str).tolist() if x not in ("", "nan", "None")]
            actual_affected_rows_count = len(set(affected_values))
        else:
            actual_affected_rows_count = 0
        actual_affected_rows_pct = round(actual_affected_rows_count * 100 / len(clean_df), 2) if len(clean_df) else 0

        spec = {
            "app_name": APP_NAME,
            "app_version": APP_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "profile": self.var_profile.get(),
            "seed": seed,
            "generation_model": "v4_row_impact_and_unique_error_events",
            "counting_unit": "one row in demo_error_manifest.csv equals one unique injected error event",
            "counting_rules": {
                "same_error_not_counted_twice": "The same (row_id, column, error_type) is recorded once.",
                "multiple_errors_per_row_allowed": True,
                "affected_rows_apply_to": "row-level and cell-level errors",
                "schema_level_errors": sorted(SCHEMA_LEVEL_ERRORS),
                "schema_level_note": "Column-name and noise-column errors are counted as schema-level events, not as thousands of cell-level errors."
            },
            "rows_clean": len(clean_df),
            "rows_dirty": len(dirty_df),
            "columns_clean": len(clean_df.columns),
            "columns_dirty": len(dirty_df.columns),
            "affected_rows": {
                "requested_percentage": affected_rows_pct,
                "requested_count": len(affected_base_indices),
                "actual_count": actual_affected_rows_count,
                "actual_percentage": actual_affected_rows_pct,
                "selection_policy": "deterministic_random_sample_from_clean_rows_using_seed",
            },
            "error_density": {
                "requested_total_error_events": sum(counts.values()),
                "requested_error_events_per_affected_row": round(sum(row_level_requested.values()) / len(affected_base_indices), 3) if affected_base_indices else 0,
                "actual_total_error_events": int(len(manifest_df)),
                "actual_error_events_per_affected_row": round(len(manifest_df[manifest_df.get('scope', '') != 'schema_column']) / actual_affected_rows_count, 3) if actual_affected_rows_count else 0,
            },
            "mode": "percentage_distribution" if self.var_use_percentages.get() else "manual_exact_counts",
            "distribution_policy": {
                "difficulty_split": "percentage-based" if self.var_use_percentages.get() else "manual-exact-counts",
                "within_difficulty_split": "randomized_with_fixed_seed" if self.var_use_percentages.get() else "manual",
                "schema_level_safeguard": "In percentage mode, excessive schema-level allocations are capped and redistributed inside the same difficulty type.",
                "note": "v4 avoids equal distribution inside a difficulty type while preserving requested Type 1 / Type 2 / Type 3 totals."
            },
            "percentage_distribution": {
                "type_1_simple": safe_pct(self.var_pct_l1.get(), 65),
                "type_2_intermediate": safe_pct(self.var_pct_l2.get(), 25),
                "type_3_advanced": safe_pct(self.var_pct_l3.get(), 10),
            } if self.var_use_percentages.get() else {
                "type_1_simple": safe_pct(self.var_pct_l1.get(), 0),
                "type_2_intermediate": safe_pct(self.var_pct_l2.get(), 0),
                "type_3_advanced": safe_pct(self.var_pct_l3.get(), 0),
                "note": "Derived from manual exact counts."
            },
            "requested_total_error_events": sum(counts.values()),
            "requested_error_counts": counts,
            "requested_error_counts_by_difficulty": labeled_counts_by_difficulty(counts),
            "requested_row_level_error_counts": row_level_requested,
            "requested_schema_level_error_counts": schema_level_requested,
            "actual_error_counts": actual_counts,
            "actual_error_counts_by_difficulty": level_counts,
            "actual_error_counts_by_scope": scope_counts,
            "actual_row_level_error_counts": actual_row_level_counts,
            "actual_schema_level_error_counts": actual_schema_level_counts,
            "difficulty_framework": {
                "type_1_simple": "Basic missing values, duplicates, simple formatting and obvious conversions.",
                "type_2_intermediate": "Mixed types, moderate logical issues, outliers, category variants and validation issues.",
                "type_3_advanced": "Corruption, partial duplicates, multi-column inconsistencies and irrelevant noisy columns."
            },
            "expected_usage": {
                "dirty_dataset": "Upload into AI Data Cleaner.",
                "manifest": "Use as ground truth to evaluate detection and cleaning.",
                "clean_dataset": "Use as reference after cleaning.",
                "dataset_spec": "Use for count-level calibration and sanity checks."
            }
        }

        return write_outputs(output_dir, clean_df, dirty_df, manifest_df, spec)

    def _poll_results(self) -> None:
        try:
            while True:
                kind, payload = self.result_queue.get_nowait()
                if kind == "PROGRESS":
                    self.progress["value"] = int(payload)
                elif kind == "STATUS":
                    self.var_status.set(str(payload))
                elif kind == "SUCCESS":
                    self.progress["value"] = 100
                    self.var_status.set("Done")
                    self.is_generating = False
                    self.set_button_visual_state("success")
                    message = "Generated files:\n\n" + "\n".join(f"- {name}: {path}" for name, path in payload.items())
                    messagebox.showinfo("Done", message)
                elif kind == "ERROR":
                    self.var_status.set("Error")
                    self.is_generating = False
                    self.set_button_visual_state("error")
                    messagebox.showerror("Generation failed", str(payload))
        except queue.Empty:
            pass

        if self.winfo_exists():
            self.after(150, self._poll_results)


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
