# Contributing to PDF Suite

Thank you for contributing. Keep changes focused, testable, and safe for local PDF workflows.

## Development setup

Requirements are Windows 10 or later, Python 3.11 or later, and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync
uv run python app.pyw
```

## Before opening a pull request

```powershell
$env:PDF_SUITE_TEST_TMP = Join-Path (Get-Location) ".test-temp"
New-Item -ItemType Directory -Force $env:PDF_SUITE_TEST_TMP | Out-Null
uv run python -m compileall -q app.pyw core ui scripts tests
uv run python -m unittest discover -s tests -v
```

For UI changes, build the portable application and run the visual smoke check described in the README.

## Guidelines

- Never commit confidential PDFs, personal signature images, credentials, or generated build directories.
- Preserve local-only document processing unless a change explicitly documents and obtains consent for network behavior.
- Keep visual-signature language distinct from certificate-backed digital signing.
- Add regression tests for engine behavior and update documentation for visible workflow changes.
- Use clear commit messages and explain user impact in pull requests.

By contributing, you agree that your contribution is licensed under the GNU AGPL v3 or later.
