# PDF Suite technical documentation

- **Version:** 1.1.0
- **Platform:** Windows desktop
- **Last verified:** July 20, 2026

## 1. Scope

PDF Suite is a local desktop PDF review and organization tool. It renders documents, manages pages, creates annotations, fills AcroForms, and places visual signatures. Document content, annotations, signature images, and user information remain local.

The application does not implement certificate-backed digital signing. A placed signature is flattened image content and provides no identity or integrity guarantee.

## 2. Technology stack

- Python 3.11+
- CustomTkinter and Tk for the desktop interface
- PyMuPDF (`fitz`) for PDF rendering and mutation
- Pillow for image conversion and signature creation
- uv with `uv.lock` for dependency management
- PyInstaller for the portable Windows build

Runtime dependencies are declared in `pyproject.toml`. Build-only dependencies are in the `build` dependency group.

## 3. Repository layout

```text
pdf-suite/
|-- app.pyw                     Application entry point
|-- app_icon.ico                Window and executable icon
|-- build_windows.ps1           Locked Windows build workflow
|-- PDF Suite.spec              PyInstaller specification
|-- pyproject.toml              Project metadata and dependencies
|-- uv.lock                     Locked dependency graph
|-- core/
|   |-- engine.py               PDF rendering and document operations
|   `-- session.py              Unsaved-change state
|-- ui/
|   |-- canvas.py               Page canvas and pointer interactions
|   |-- layout.py               Responsive breakpoints and width bounds
|   |-- main_window.py          UI composition and command coordination
|   |-- menu_bar.py             Dark in-window menu and popups
|   |-- sidebar.py              Progressive thumbnails and page actions
|   `-- tooltip.py              Pointer and keyboard-focus tooltips
`-- tests/
    |-- test_engine_forms.py
    |-- test_engine_signatures.py
    |-- test_layout.py
    `-- visual_smoke.ps1
```

Generated environments, build output, and smoke-test artifacts are excluded through `.gitignore`.

## 4. Architecture

### Entry point

`app.pyw` configures the dark CustomTkinter theme, creates the root window, resolves bundled resources through `sys._MEIPASS` when packaged, accepts an optional PDF path as the first command-line argument, and starts `MainWindow`.

### Session state

`SessionManager` owns the `unsaved_changes` flag and exposes explicit changed, saved, and reset transitions. The window title shows an asterisk for unsaved changes. Opening another document or closing the window asks before discarding them.

### PDF engine

`PDFEngine` owns the active PyMuPDF document and provides:

- Full-page and thumbnail rendering.
- Form-widget discovery and updates by cross-reference ID.
- Highlight creation and audit-note metadata.
- Note reading, editing, deletion, and CSV report data.
- Visual-signature image insertion with aspect-ratio preservation.
- Crop, rotation, movement, deletion, extraction, and combining operations.
- Incremental overwrite of a source-backed PDF and full saves for copies.

Combining is transactional at the application level: sources are inserted into a separate in-memory document, and the active document is replaced only after every insertion succeeds. Temporary documents and opened sources are closed through explicit cleanup paths.

Text-snap highlighting groups extracted words by both PyMuPDF block and line identifiers. This prevents unrelated text blocks with matching line numbers from being merged into one highlight rectangle.

### User interface

`MainWindow` owns the application workflow and connects the engine, canvas, sidebar, menus, dialogs, session state, and Details panel.

The main layout is:

```text
Dark menu bar
File, page, zoom, Details, and File Actions toolbar
Thumbnail panel | Tool rail | PDF canvas | Details workspace
Status bar
```

The custom dark menu is intentional. Native `tkinter.Menu` uses the Windows system appearance and does not match the established dark interface.

`PDFCanvas` owns the rendered page image, scrolling, panning, selection rectangles, and mouse-event routing. Crop, highlight, and signature operations use one shared conversion path that clamps selections to the current page and rejects undersized rectangles.

`Sidebar` creates thumbnails incrementally through cancellable Tk callbacks. Rendering and widget updates stay on Tk's owning thread, and the event loop receives time between pages. Replacing or closing a document cancels the outstanding thumbnail job.

## 5. Responsive layout

Layout decisions are isolated in `ui/layout.py`:

- Below 850 pixels: drawer layout.
- From 850 through 1179 pixels: compact layout.
- At 1180 pixels and above: wide layout.
- Sidebar width is bounded from 176 through 360 pixels, with a default of 224 pixels.

At narrower sizes, the toolbar wraps to two rows. Thumbnails and Details behave as temporary drawers so they do not compress the document canvas beyond usability.

## 6. Forms

The Forms tab maps PyMuPDF widgets to CustomTkinter controls:

- Text and unsupported editable values use text entries.
- Checkboxes use boolean controls and the PDF widget's on-state.
- Radio widgets sharing a field name are presented as a group.
- Combo boxes and list boxes use their embedded choices.
- Read-only widgets are visible but disabled.
- Certificate-signature fields are identified but not edited.

Controls are retained while the same page rerenders, so zooming does not discard unsubmitted values. **Apply Form Changes** writes controls to the PDF widgets, rerenders the page, and marks the session changed. Navigating away without applying can discard pending UI values.

## 7. Visual signatures

The Sign tab accepts:

- PNG, JPEG, or BMP files, normalized to PNG.
- Typed names rendered with an available Windows script or italic font.
- Mouse-drawn strokes converted to a cropped transparent PNG.

After choosing a source, the user drags a bounded placement rectangle. Rectangles smaller than 10 PDF points in either dimension are rejected. The image is inserted proportionally and becomes page content. Escape cancels pending placement.

## 8. Annotations and exported notes

Highlight annotations store content in this format:

```text
CREATED: <user> @ <timestamp>
MODIFIED: <user> @ <timestamp>
---
<comment>
```

Editing preserves the original creation line and replaces the modified identity and timestamp. This metadata is useful for review traceability but is not cryptographically protected.

CSV export contains page, user, creation time, last-modified time, and comment. String cells beginning with `=`, `+`, `-`, or `@` after leading whitespace are prefixed before writing to reduce spreadsheet formula-injection risk.

## 9. Saving and page operations

Document-changing operations mark the session unsaved. These include form updates, signatures, highlights, note edits and deletion, cropping, rotation, combining, page movement, and page deletion.

- **Update Original File** uses an incremental save when the active PyMuPDF document is backed by the same path.
- **Save Copy as PDF** performs a full save and does not change the original association.
- Combined in-memory documents use a full save.

Page extraction accepts checkbox selections or comma-separated, inclusive ranges such as `1-5, 10`. Invalid syntax is reported; out-of-range page numbers are ignored. Extraction closes its temporary document even when saving fails.

The application prevents deletion of the only remaining page.

## 10. Build and distribution

From PowerShell:

```powershell
.\build_windows.ps1
```

The script:

1. Sets `.build-venv` as the uv project environment.
2. Synchronizes locked runtime and build dependencies.
3. Runs PyInstaller in windowed, one-folder mode.
4. Embeds the icon and collects CustomTkinter assets.

Output:

```text
dist\PDF Suite\PDF Suite.exe
```

Ship the entire `dist\PDF Suite` directory. One-folder packaging is intentional for predictable startup and easier resource diagnosis.

## 11. Verification

Automated verification:

```powershell
$env:PDF_SUITE_TEST_TMP = (Resolve-Path ".test-temp").Path
.\.build-venv\Scripts\python.exe -m unittest discover -s tests -v
.\.build-venv\Scripts\python.exe -m compileall -q app.pyw core ui
git diff --check
```

The current suite contains five tests covering form persistence, signature insertion and minimum-size rejection, responsive breakpoints, and sidebar width bounds.

Packaged visual verification:

```powershell
.\tests\visual_smoke.ps1 -PdfPath ".\sample.pdf"
```

The smoke script launches the built executable and captures normal, Details, Forms, Sign, 800x600, and 1024x768 states. On July 20, 2026, the source tests, compilation, Windows build, and packaged visual smoke check all completed successfully.

The smoke script verifies launch and visible layout states; it does not automate every destructive edit or save workflow.

## 12. Known limitations

- Undo and redo are not implemented.
- Placed visual signatures cannot be selected, moved, or resized.
- Certificate-backed PDF signing and validation are not implemented.
- Complex scripted forms, radio-group edge cases, and fields spanning pages require broader testing.
- Thumbnail rendering is incremental but remains CPU work on the UI thread.
- Automated GUI coverage is limited to screenshot-based smoke checks.
- Distribution is a portable folder; there is no installer or automatic file-association registration.
