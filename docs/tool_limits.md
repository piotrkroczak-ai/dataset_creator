# Tool Limits — Controlled Dataset Generator v6.1

Analysis of the current calibration boundaries enforced by the generation engine.

The limits fall into two categories:

- **Level 1 — Hard limits**: explicit numeric bounds enforced by the engine. Predictable, validated, and reported.
- **Level 2 — Calibration traps**: silent shortfalls where the *actual* injected count falls below the *requested* count without any pre-flight warning. These are the dangerous ones for benchmark calibration.

---

# Level 1 — Hard limits

Explicit bounds clamped by `safe_int` / `safe_pct` and the validation helpers.

## Numeric input bounds

| Parameter | Min | Max |
|---|---|---|
| Rows | 1 | 1 000 000 |
| Columns | 8 | 20 |
| Affected rows % | 0 | 100 |
| Total errors | 0 | 2 000 000 |
| Seed | 0 | 2 147 483 647 |

Columns are drawn from a fixed internal schema of 20 columns, always in the same positional order — requesting `N` columns yields the first `N` of that fixed list (see column map below).

## Schema-level error caps

| Error type | Cap | At 20 columns |
|---|---|---|
| `dirty_column_names` | `columns − 1` | 19 |
| `irrelevant_noise_columns` | `min(10, columns // 3)` | 6 |

Overflow is **automatically redistributed** within the same difficulty type, so Type 1 / Type 2 / Type 3 totals stay exact. This redistribution is the one case where overflow is handled gracefully rather than silently dropped.

## Row-level (duplicate) caps

| Error type | Cap |
|---|---|
| `full_duplicates` | number of affected rows |
| `partial_duplicates` | number of affected rows |

## Global cell budget

All cell-level errors share a single pool of unique `(row, column)` cells:

```
total cell-level events ≤ affected_rows × (columns − 1)
```

The shared pool means every cell-level error type competes for the same cells (`used_cells` is global across all injectors).

## Pre-flight validation coverage

`validate_counts_against_bounds()` warns before generation **only** for:

- `dirty_column_names` exceeding `columns − 1`
- `irrelevant_noise_columns` exceeding `min(10, columns // 3)`
- `full_duplicates` / `partial_duplicates` exceeding affected rows
- aggregate row-level total exceeding the global cell budget

Anything outside this list fails silently — see Level 2.

---

# Level 2 — Calibration traps (silent shortfalls)

Cases where `actual < requested` with **no UI warning**. The gap is only visible *after* generation, by comparing `requested_error_counts` vs `actual_error_counts` in `demo_dataset_spec.json`.

## Per-error column eligibility

Each cell-level error only injects into specific columns. If those columns are absent (because of the `columns` setting), the error silently produces fewer events — or zero.

| Error | Target column(s) | Min columns to work |
|---|---|---|
| `boolean_variants` | `active` | **9** |
| `negative_ages` | `age` | **10** |
| `decimal_commas` | amount, score, discount_rate | 8 (amount only until ≥15 / ≥18) |
| `simple_outliers` | amount, score, support_tickets | 8 (amount only until ≥15 / ≥17) |
| `country_variants` | `country` | 5 (always present) |
| `invalid_emails` | `email` | 4 (always present) |
| `mixed_date_formats` | signup_date, last_login | always present |
| `future_dates` | signup_date, last_login | always present |
| `multi_column_date_inconsistency` | needs **both** signup_date + last_login | always present |

### Fixed column order (positional)

```
 1 id              6 signup_date    11 category    16 notes
 2 first_name      7 last_login     12 city        17 support_tickets
 3 last_name       8 amount         13 plan        18 discount_rate
 4 email           9 active         14 source      19 region
 5 country        10 age            15 score       20 segment
```

### Consequence: the 8-column minimum disables two error types

At `columns = 8` (the minimum), `active` (col 9) and `age` (col 10) **do not exist**, so:

- `boolean_variants` → **0 events**, silently
- `negative_ages` → **0 events**, silently

`score` requires ≥ 15 columns, `support_tickets` ≥ 17, `discount_rate` ≥ 18 — below those, `decimal_commas` and `simple_outliers` collapse onto `amount` alone.

## Single-column error types capped at affected_rows

`boolean_variants`, `negative_ages`, `country_variants`, `invalid_emails` each target exactly **one** column. Their real cap is therefore the number of affected rows — *not* the global cell budget. Requesting more silently truncates.

## Shared cell-pool contention

Because `used_cells` is global, requesting many cell-level errors that target the same narrow set of columns (e.g. both date errors fighting over `signup_date` / `last_login`) exhausts those cells early. Later injectors get fewer cells than their quota.

## pick_cell retry ceiling

`pick_cell()` gives up after 1 000 failed attempts to find an unused cell and returns `None`, ending that injector's loop. At high density it can stop **below** the theoretical cell budget.

## Silent skips on parse failure

`decimal_commas`, `mixed_date_formats`, and `simple_outliers` mark a cell as used, then `continue` (skip) if value parsing fails — consuming a cell slot without recording an event.

---

# Unit test mode

Fixed parameters — not editable via the UI:

| Parameter | Value |
|---|---|
| Rows | 1 000 |
| Columns | 10 |
| Affected rows | 10% |
| Total errors | 100 |

At 10 columns, `score` / `support_tickets` / `discount_rate` are absent, so `simple_outliers` and `decimal_commas` run on `amount` only. The seed field is ignored — output is fully deterministic regardless.

---

# Seed behaviour

In percentage mode, **everything is reproducible** from the user seed. Derived streams:

| Stream | Seed used |
|---|---|
| Affected-row selection | `seed + 777` |
| Intra-type sub-type split | `seed + 404` |
| Error injection | `seed + 1000` |

The **only** path that ignores the user seed is the 🎲 **Random distribution** button (`fresh_seed = 9999 + click_index × 31337`), which deliberately produces a new split per click.

---

# Generation performance

`_worker_generate` runs an **artificial 5–10 s progress animation** independent of dataset size. The real generation happens *after* the bar reaches 100%, so the progress bar is not a true work indicator and there is no real-time signal for large datasets — a blocker for batch generation.

---

# Profiles (presets)

| Profile | Rows | Columns | Affected % | Total errors | Type 1 % | Type 2 % | Type 3 % |
|---|---|---|---|---|---|---|---|
| DEMO_SMALL | 300 | 12 | 20 | 168 | 65 | 25 | 10 |
| BEGINNER_LEVEL_1 | 1 000 | 12 | 20 | 250 | 75 | 20 | 5 |
| BEGINNER_LEVEL_2 | 3 000 | 15 | 20 | 650 | 60 | 30 | 10 |
| CUSTOM | 1 000 | 15 | 20 | 500 | 80 | 10 | 10 |

---

# Detecting shortfalls

`demo_dataset_spec.json` records both `requested_error_counts` and `actual_error_counts` (plus by-difficulty and by-scope breakdowns). Comparing the two is currently the **only** way to catch the Level 2 traps — none of them are surfaced in the UI before generation.
