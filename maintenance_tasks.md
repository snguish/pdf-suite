# Proposed Maintenance Tasks

## 1) Typo Fix Task
**Title:** Correct launcher filename casing in user docs

**Issue:** The README tells users to run `Run_PDF_Suite.bat`, but the repository file is actually named `run_pdf_suite.bat`.

**Why this matters:** On case-sensitive filesystems, this mismatch can confuse users and break copy/paste launch instructions.

**Scope:**
- Update the README setup and desktop-integration sections to use the actual launcher filename.

**Acceptance criteria:**
- All launcher references in user-facing docs consistently use `run_pdf_suite.bat`.
- A quick repo search shows no stale `Run_PDF_Suite.bat` references in end-user instructions.

---

## 2) Bug Fix Task
**Title:** Guard annotation iteration when pages have no annotations

**Issue:** Several engine methods iterate directly over `page.annots()` (for example `get_comment_at_pos`, `update_comment_at_pos`, and `delete_highlight`). In PyMuPDF, `page.annots()` may be `None` when a page has no annotations.

**Why this matters:** Hovering, right-clicking, or editing notes on a page without annotations can raise runtime errors instead of safely returning "no note found" behavior.

**Scope:**
- Normalize annotation iteration behind a helper (e.g., `annots = page.annots() or []`).
- Apply this guard consistently in all annotation-walking methods.

**Acceptance criteria:**
- No crashes when interacting with a page that has zero annotations.
- Methods return default safe values (`""` / `False` / empty report additions) without exceptions.

---

## 3) Documentation/Comment Discrepancy Task
**Title:** Align technical docs with actual project filenames and startup behavior

**Issue:** The technical document and README reference `Run_PDF_Suite.bat` and a 4-column layout narrative, while the real launcher file is `run_pdf_suite.bat`, and some startup details are implemented differently in code.

**Why this matters:** Documentation drift increases onboarding time and creates avoidable support requests.

**Scope:**
- Update `technical_documentation.md` and README naming to match repository filenames.
- Verify startup flow text against `app.pyw` and `ui/main_window.py` behavior and adjust wording where needed.

**Acceptance criteria:**
- Documented filenames and startup sequence match the current codebase.
- No conflicting statements between README and technical documentation for launch/setup flow.

---

## 4) Test Improvement Task
**Title:** Add unit tests for page-range parsing and validation logic

**Issue:** `apply_range_from_entry` in `MainWindow` contains non-trivial parsing and validation logic (ranges, comma-separated values, bounds checks), but there are currently no automated tests.

**Why this matters:** Parsing regressions are easy to introduce and hard to spot manually, especially for malformed input and edge cases.

**Scope:**
- Extract parsing into a pure helper function (e.g., `parse_page_ranges(text, page_count) -> list[int]`).
- Add tests for:
  - single page (`"3"`)
  - range (`"1-5"`)
  - mixed list (`"1-3, 7, 10-12"`)
  - duplicates and ordering
  - out-of-bounds values
  - malformed input (`"a-b"`, `"3-"`, empty tokens)

**Acceptance criteria:**
- Tests run in CI/local and cover valid + invalid paths.
- `MainWindow.apply_range_from_entry` delegates to the helper and only handles UI messaging.
