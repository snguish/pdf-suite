# PDF Suite Technical Documentation

**Current development version:** 1.1

**Platform:** Windows desktop

**Last updated:** July 2026

## 1. Purpose and scope

PDF Suite is a local desktop application for reviewing and organizing PDF documents. It supports page rendering and navigation, audit-aware highlights and notes, cropping, page extraction, PDF combining, page reordering, rotation, image snapshots, and note export.

All document processing is local. The application does not upload PDFs, annotations, signatures, or user information to a remote service.

Form filling and visual signatures are planned for the next implementation milestone. Certificate-backed cryptographic signing is a separate advanced capability and is not currently implemented.

## 2. Technology stack

- **Language:** Python 3
- **GUI:** CustomTkinter and Tk
- **PDF engine:** PyMuPDF (`fitz`)
- **Image handling:** Pillow
- **Windows packaging:** PyInstaller
- **Source control:** Git

Runtime dependencies are declared in `requirements.txt`. Build-only dependencies are declared in `requirements-build.txt`.

## 3. Repository structure

```text
pdf-suite/
|-- app.pyw                    Application entry point
|-- app_icon.ico               Window and executable icon
|-- build_windows.ps1          Reproducible Windows build script
|-- requirements.txt           Runtime dependencies
|-- requirements-build.txt     Runtime and packaging dependencies
|-- README.md                  User-facing instructions
|-- technical_documentation.md Maintainer documentation
|-- core/
|   |-- engine.py              PDF rendering, annotation, and page operations
|   `-- session.py             Session and unsaved-change state
|-- ui/
|   |-- main_window.py         Window layout, menus, commands, and coordination
|   |-- canvas.py              Rendering surface and pointer interaction
|   `-- sidebar.py             Thumbnails, selection, and page context actions
`-- utils/
    `-- math_tools.py          Shared utility functions
```

`run_pdf_suite.bat` remains in the repository as a legacy development launcher. Packaged releases should use `PDF Suite.exe` instead.

## 4. Application architecture

### 4.1 Entry layer

`app.pyw` configures CustomTkinter, creates the root window, resolves bundled resources, reads an optional PDF path from the Windows command line, and starts `MainWindow`.

Resource lookup supports both source execution and PyInstaller's temporary bundle location through `sys._MEIPASS`. This ensures that `app_icon.ico` works in development and in the packaged executable.

### 4.2 Session layer

`SessionManager` owns transient document state:

- `unsaved_changes` indicates whether the open document differs from its saved source.
- `history` is reserved for the planned undo/redo implementation.
- `mark_changed()`, `mark_saved()`, and `reset()` provide explicit state transitions.

The window title contains an asterisk when changes are unsaved. Opening another document or closing the window requires confirmation before those changes are discarded.

### 4.3 PDF engine

`PDFEngine` wraps the active PyMuPDF document. Its responsibilities include:

- Rendering full pages and thumbnails.
- Rotating, cropping, moving, deleting, and extracting pages.
- Atomically combining the active document with additional PDFs.
- Creating, reading, editing, deleting, and exporting highlight notes.
- Saving incrementally when overwriting a source-backed document.
- Performing a full save for a new in-memory combined document or a copy.
- Closing the native PDF handle when a document is replaced or the window closes.

The combine operation constructs a separate in-memory document and only replaces the active document after all selected sources have been inserted successfully. This prevents a failed source from leaving a partially combined active document.

### 4.4 User-interface layer

`MainWindow` coordinates commands and document state. Version 1.1 introduces File, Pages, and View menus together with a compact toolbar for common navigation, saving, zoom, and editing actions.

The current layout is:

```text
Menu bar
Compact toolbar with page counter and Fit Page/Fit Width controls
Thumbnail panel | Document canvas | Contextual Details workspace
Status bar
```

The right-side Details workspace contains Notes, Forms, and Sign tabs. Notes are connected to the existing annotation workflow. Forms and Sign reserve stable locations for the next editing milestone and are explicitly labeled as upcoming rather than presenting inactive controls as complete features.

The Pages menu and thumbnail context menu expose document organization commands. After page structure changes, the thumbnail view is rebuilt against the updated document.

`PDFCanvas` owns pointer coordinates, selection rectangles, panning, and wheel-event routing. It prevents handled wheel events from propagating to the root window twice.

`Sidebar` loads thumbnails progressively and provides page selection plus context actions for rotation, movement, and deletion.

## 5. Navigation and input behavior

Normal mouse-wheel input changes pages. `Ctrl + Mouse Wheel` zooms around the pointer position rather than the center of the page.

Cursor-focused zoom follows this sequence:

1. Translate the pointer's canvas position into a PDF coordinate at the old zoom.
2. Render the page at the bounded new zoom level.
3. Calculate the PDF coordinate's new canvas position.
4. Adjust the canvas view so that the same document location remains beneath the pointer.

Zoom is constrained to 10–800 percent. Fit Page considers both available height and width. Fit Width uses 96 percent of the canvas width and is available through the toolbar, View menu, and `Ctrl + 2`.

Single-letter document shortcuts are ignored when an Entry, Text, ComboBox, or Spinbox has focus. This prevents commands such as crop, highlight, or sidebar toggle from firing while a user types.

## 6. Annotation and audit metadata

Highlights store structured text in the PDF annotation content:

```text
CREATED: <user> @ <timestamp>
MODIFIED: <user> @ <timestamp>
---
<comment>
```

Editing a note preserves its original `CREATED` line and replaces the `MODIFIED` identity and timestamp. CSV note export includes page, user, creation time, last-modified time, and comment.

The metadata improves traceability but is not a cryptographic audit mechanism. Anyone with a capable PDF editor can alter annotation metadata.

## 7. Saving and document lifecycle

Document-changing operations call `mark_document_changed()`. This currently includes highlights, note edits, note deletion, cropping, rotation, combining, page movement, and page deletion.

Saving behavior is divided into two paths:

- **Update Original File:** uses incremental saving when the PyMuPDF document is still backed by the same source path.
- **Save Copy as PDF:** performs a full save to a new path and leaves the original document association unchanged.

Combined documents are created in memory and therefore have no PyMuPDF source name. They use a full save even when the user elects to update the path originally opened by the application.

Open and save failures are presented through user-facing dialogs. An existing PDF engine is replaced only after a new document has opened successfully.

## 8. Page organization

The following page operations are implemented:

- Combine one or more PDFs with the active document.
- Extract checkbox-selected pages or a typed page range.
- Rotate a page by 90 degrees.
- Move a page one position up or down.
- Delete a page after confirmation.

Deletion of the only remaining page is rejected because a valid PDF must contain at least one page.

The typed range parser accepts comma-separated pages and inclusive ranges, for example `1-5, 10`. Invalid syntax produces an error dialog, while page numbers outside the document are ignored.

## 9. Windows executable build

Run the following from PowerShell at the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_windows.ps1
```

The script:

1. Creates or repairs `.build-venv`.
2. Installs the declared runtime and build dependencies.
3. Runs PyInstaller in windowed, one-folder mode.
4. Embeds the application icon and includes CustomTkinter assets.

The output is:

```text
dist\PDF Suite\PDF Suite.exe
```

The complete `dist\PDF Suite` directory is the portable application. The executable should not be distributed without its adjacent `_internal` content.

One-folder packaging is intentional for the initial release because it starts faster and makes missing-resource problems easier to diagnose than one-file extraction.

## 10. Git workflow

Modernization work is isolated on:

```text
feature/modernize-pdf-suite
```

The first modernization milestone is recorded by commit:

```text
82707b9 Modernize PDF navigation and document workflow
```

Generated environments and PyInstaller output are excluded by `.gitignore`.

## 11. Verification

The current milestone has been checked with:

- Python bytecode compilation for the application modules.
- `git diff --check` for patch formatting errors.
- An integration test that generates PDFs, combines them, reorders pages, deletes a page, saves the result, reopens it, and validates page content.
- A successful PyInstaller Windows build.

Interactive GUI testing is still required for pointer positioning, high-DPI behavior, menus, dialogs, and Windows file association before release.

## 12. Known limitations and roadmap

The following work remains:

1. Add undo and redo using the reserved session history.
2. Detect and fill existing AcroForm fields in the Forms tab.
3. Add typed, drawn, and imported-image visual signatures in the Sign tab.
4. Add form and signature flattening during export.
5. Continue responsive-layout testing and retire remaining legacy toolbar behavior.
6. Improve thumbnail worker isolation and cancellation for large PDFs.
7. Add automated unit and GUI tests.
8. Add a Windows installer and optional file-association registration.
9. Evaluate certificate-backed digital signatures as a separate security-focused project.

Visual signatures must not be described as digital signatures. A visual mark does not validate document integrity or signer identity. Cryptographic signing requires certificate handling, byte-range signing, validation, and preservation rules beyond the current annotation and image workflows.
