# Security policy

## Supported version

Security fixes are applied to the current `main` branch. This project does not
currently maintain older release branches.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use GitHub's
private vulnerability reporting feature on this repository instead. Include the
affected version or commit, reproduction steps, impact, and any suggested fix.

Do not include real private documents, credentials, or personal information in a
report. Use synthetic samples when demonstrating document-processing issues.

You should receive an acknowledgement within seven days. A fix and disclosure
timeline will depend on severity and reproducibility.

## Data handling

GoTranslate processes uploaded documents in server memory. Full-document
translation and translated vocabulary definitions are sent to Google's web
translation service. Deployers are responsible for reviewing that service's
terms and privacy requirements before processing sensitive documents.
