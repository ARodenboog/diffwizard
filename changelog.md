# Changelog

- _parse_diff() to diff class - separating and cleaning diffs as strings
- _split_long_diff() to diff class - helpers for splitting long diffs
- openai==0.25.0
- python-dotenv==0.21.0
- Replaced hardcoded number 2000 by max_length parameter to allow customizing of diff length 
- Added function _split_long_diff to split a diff into multiple diffs of max_length, first on file, then on lines
- Added library dependency of openai==0.25.0
- Added library dependency of python-dotenv==0.21.0