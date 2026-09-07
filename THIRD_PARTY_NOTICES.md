# Third-party notices

GoTranslate includes data and relies on open-source packages whose licenses are
separate from the MIT License covering GoTranslate's original source code.

## JLPT vocabulary data

`libraries/data/jlpt/all.csv` is derived from the `elzup/jlpt-word-list`
repository:

- Source: https://github.com/elzup/jlpt-word-list
- Repository license: MIT
- Original vocabulary data: Jonathan Waller's JLPT resources at tanos.co.uk,
  distributed under Creative Commons Attribution terms

Copyright and attribution remain with their respective authors. The included
data is used to attach approximate JLPT levels to extracted vocabulary. These
levels are community-maintained and are not an official JLPT vocabulary list.

## Runtime packages and model data

Python and JavaScript dependencies are installed from their upstream packages
and retain their respective licenses. OCR model files and the Jamdict database
are downloaded during setup or container builds and are not committed to this
repository. Consult each upstream project before redistributing a built image or
downloaded model bundle.
