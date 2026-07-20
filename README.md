# PDF Suite

PDF Suite is a local Windows desktop application for reviewing, annotating, filling, signing, and organizing PDF documents. Files are processed on the computer and are not uploaded to a remote service.

## Features

- Render PDFs with page thumbnails, direct page navigation, fit-to-page, fit-to-width, and pointer-centered zoom.
- Highlight text or arbitrary regions and attach timestamped notes.
- Inspect and edit AcroForm text fields, checkboxes, radio buttons, combo boxes, and list boxes.
- Import, type, or draw a visual signature and place it as flattened page content.
- Crop, rotate, reorder, delete, combine, and extract pages.
- Export a page as PNG or export notes as a formula-safe CSV file.
- Open a second window for side-by-side document review.
- Adapt the workspace for wide, compact, and narrow window sizes while retaining the dark interface.

> [!IMPORTANT]
> Visual signatures are images, not certificate-backed digital signatures. They do not verify signer identity or protect a document from later changes.

## Run from source

Requirements:

- Windows 10 or later
- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/)

From PowerShell in the repository root:

```powershell
uv sync
uv run python app.pyw
```

Open a PDF at startup by passing its path:

```powershell
uv run python app.pyw "C:\Documents\sample.pdf"
```

## Build the Windows application

Run:

```powershell
.\scripts\build_windows.ps1
```

The portable application is created at:

```text
dist\PDF Suite\PDF Suite.exe
```

Distribute the complete `dist\PDF Suite` directory. The executable depends on the adjacent packaged files.

## Main workflow

1. Select **Open** or pass a PDF on the command line.
2. Navigate with the thumbnail panel, page field, arrow controls, or mouse wheel.
3. Choose **Highlight**, **Crop**, **Forms**, or **Sign** from the tool rail.
4. Use **Details** to work with Notes, Forms, and Sign controls.
5. Select **Save** to update the original after confirmation, or choose **Save Copy as PDF...** from **File Actions**.

Form edits are not applied automatically. Select **Apply Form Changes** before leaving the page or saving.

## Keyboard and mouse controls

| Input | Action |
| --- | --- |
| `Up`, `Page Up` | Previous page |
| `Down`, `Page Down` | Next page |
| Mouse wheel | Previous or next page |
| `Ctrl` + mouse wheel | Zoom around the pointer |
| `+`, `=`, numpad `+` | Zoom in |
| `-`, numpad `-` | Zoom out |
| `Ctrl+0` or `f` | Fit page |
| `Ctrl+1` or `b` | Actual size |
| `Ctrl+2` | Fit width |
| `Ctrl+O` | Open PDF |
| `Ctrl+S` | Update original file |
| `Ctrl+Shift+S` | Save a copy |
| `Ctrl+E` | Export notes |
| `Ctrl+D` | Toggle Details |
| `s` | Toggle thumbnails |
| `h` | Toggle highlight mode |
| `c` | Toggle crop mode |
| `Esc` | Cancel the active tool |

Single-letter shortcuts are ignored while typing in an input control.

## Tests and verification

Run the automated tests with a workspace-local temporary directory:

```powershell
$env:PDF_SUITE_TEST_TMP = (Resolve-Path ".test-temp").Path
uv run python -m unittest discover -s tests -v
```

After building, run the packaged visual smoke check with a sample PDF:

```powershell
.\tests\visual_smoke.ps1 -PdfPath ".\sample.pdf"
```

Screenshots are written to `.test-temp\visual-smoke`. The script checks the normal, Details, Forms, Sign, 800x600, and 1024x768 layouts.

## Limitations

- There is no undo or redo history.
- Placed visual signatures cannot be selected, moved, or resized.
- Certificate-backed PDF signing and validation are not implemented.
- Complex scripted forms and multi-page field groups need broader compatibility testing.
- The project currently produces a portable folder, not an installer or automatic file association.

See [technical documentation](docs/technical_documentation.md) for architecture and maintainer details.
