# Security policy

## Supported versions

Security fixes are provided for the latest published release and the current `main` branch.

| Version | Supported |
| --- | --- |
| 1.1.x | Yes |
| Earlier versions | No |

## Reporting a vulnerability

Please use [GitHub private vulnerability reporting](https://github.com/snguish/pdf-suite/security/advisories/new). Do not disclose vulnerabilities in public issues, discussions, or pull requests.

Include the affected version, reproduction steps, impact, and any suggested mitigation. Avoid attaching confidential PDFs or real signature images. You should receive an acknowledgement within seven days.

## Security boundaries

PDF Suite processes files locally, but PDFs are complex, potentially hostile inputs. Visual signatures are ordinary page images: they do not verify identity, provide certificate-backed signing, or prevent later document changes.
