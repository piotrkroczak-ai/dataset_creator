# Roadmap (public) — Controlled Dataset Generator

A high-level view of where the project stands and where it is heading.
Detailed step-by-step specifications and acceptance criteria are maintained privately.

---

## Guiding principle

Keep the generator **simple and measurable**. It exists to create reproducible test data for benchmarking an AI Data Cleaner — not to grow into a complex platform.

---

## Done

| Milestone | Outcome |
|---|---|
| Local MVP | Clean + dirty + spec + manifest, fully offline |
| Difficulty model | Type 1 / 2 / 3 distribution, percentage and manual modes |
| Compact UI | Always-visible generate action, collapsible details |
| Row-impact model | Affected-rows % + unique error events, richer JSON spec |
| Bounds validation | Pre-flight warning when requested counts exceed limits |
| Random distribution | One-click bounded randomization |
| UI reliability | Stable show/hide and editable manual fields |
| Unit test mode | One-click single-error-type generation |

---

## Planned

| Milestone | Goal |
|---|---|
| Stronger presets | Better demo / beginner profiles (small, lightweight datasets) |
| Benchmark profile | ~100k rows × 20 columns, runs on a standard laptop |
| Output formats | Optional XLSX / JSON Lines / Parquet — CSV stays the default |
| Evaluation helper | Local script scoring detection, cleaning, residual and false-modification rates |
| Richer Type 2 / Type 3 | More date, category, and validation cases; safe advanced errors |
| Scenario presets | Domain templates (CRM, marketing, ecommerce, support) |
| Batch generation | Multiple datasets in one run, each in its own folder |
| Large-scale scenario | Larger multi-table benchmark for later-stage testing |

---

*The roadmap is intentionally incremental: each step ships a small, verifiable improvement before the next begins.*
