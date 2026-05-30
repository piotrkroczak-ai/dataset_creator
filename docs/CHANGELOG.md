# Changelog (public) — Controlled Dataset Generator

A condensed, public-facing history of how the tool evolved.
Internal implementation notes, local environment details, and full debugging traces are kept in the private project documentation.

---

## v1 — Local MVP
- Generates a clean reference dataset, a dirty dataset, a JSON specification, and an error manifest.
- Fully local: no API, no cloud, no database.
- Focused on simple, customer-style datasets.

## v2 — Error difficulty distribution
- Introduced three difficulty levels: Type 1 (simple), Type 2 (intermediate), Type 3 (advanced).
- Added percentage-based distribution (default 65 / 25 / 10) and a manual exact-count mode.
- Added a live numeric preview of the resulting distribution.

## v3 — Profile UI and generation flow
- Restored a compact dataset-profile layout and a generated-files summary.
- Added preset profiles and a clear primary generate action.
- Added a natural-feeling progress animation.
- **v3.x** refinements: kept the generate button always visible, made calculated counts read-only in percentage mode, and collapsed exact counts by default to save space.
- **Stability fix:** resolved a dtype conflict when injecting missing values into boolean columns.

## v4 — Row-impact model and unique error events
- Replaced raw total-error counting with a clearer model: **affected-rows percentage** + **total unique error events**.
- Defined one manifest row = one unique error event; the same error is never counted twice.
- Schema-level errors (dirty column names, noise columns) are counted once per column, not per cell.
- Richer JSON spec separating requested vs actual counts, row-level vs schema-level, and affected-row statistics.
- **v4.1** added pre-flight bounds validation with a warning before generation.
- **v4.2** added a one-click randomized distribution that respects all physical bounds.

## v5 — UI reliability
- **v5.1** made the show/hide distribution control reliable in every mode.
- **v5.2** made the manual-mode header fields fully editable without being overwritten.

## v6 — Unit test mode
- **v6.0** added a one-click mode to generate a single-error-type dataset with a predictable output name.
- **v6.1** fixed layout, dropdown population, and preset-value application in unit test mode *(current)*.

---

*This is a summarized public log. Each version was developed iteratively with a clear before/after rationale recorded privately.*
