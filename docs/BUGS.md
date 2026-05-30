# Bug-fix log (public) — Controlled Dataset Generator

A public summary of the notable issues found and resolved, written to show the
**debugging approach** rather than the internal code details.
Each fix followed the same loop: reproduce → identify root cause → fix → document.

Full traces, exact symbols, and code-level resolutions are kept in the private log.

---

## Silent count truncation (v4.1)
- **Symptom:** requesting more errors than the dataset could physically hold produced fewer than requested, with no feedback.
- **Cause:** the safeguard existed in one mode only; the other had no pre-flight check.
- **Fix:** added a validation step that warns before generation and lets the user cancel or proceed. Applies to both modes.

## Show/hide control not responding (v4.1 → v5.1)
- **Symptom:** hiding the detailed distribution panel had no visible effect; it reopened immediately.
- **Cause:** a refresh chain re-triggered the visibility logic and reverted the user action.
- **Fix:** separated direct user actions from automatic refreshes and added a re-entry guard so a user click is always honored. Required two iterations to make it definitive.

## Manual fields overwritten while typing (v5.2)
- **Symptom:** typing into the header fields in manual mode was immediately undone.
- **Cause:** an automatic recalculation wrote values back into the fields the user was editing.
- **Fix:** suppressed the recalculation while the user is actively editing those fields.

## Unit test mode regressions (v6.0 → v6.1)
- **Symptom:** startup crash, dropdowns rendered off-screen, the sub-type list failed to populate, and preset values were not applied.
- **Causes:** an uninitialized reference, a layout placed beyond the visible area, a duplicated code block shadowing the correct one, and a guard comparing display labels against internal keys.
- **Fix:** corrected initialization and layout, removed the duplicate block, and resolved labels to internal keys consistently.

---

### Lessons that shaped later work
- Never silently cap user input — always surface it before generation.
- UI state driven by automatic refreshes needs explicit guards against re-entry.
- Duplicate definitions are a silent hazard; keep a single source of truth per behavior.

*Public summary. The private log keeps one detailed entry per fix.*
