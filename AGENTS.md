# Agent instructions for this repo

This repo tracks a home fermentation hobby: recipes transcribed from cookbook
photos, and each brewing run ("batch") tracked as a GitHub issue. It's meant
to work with any coding agent (Claude Code, Codex, Copilot, Cursor, Pi, or by
hand).

See `README.md` for the full recipe/batch file formats and human quickstart.

## Transcribing a recipe from a photo

- Read the cookbook photo(s) and write `recipes/<slug>/recipe.md` per the
  format in README.md.
- Keep the original language and quantities exactly as printed: do not
  translate or convert units.
- Mark anything illegible in the photo with `[illegible]` instead of guessing.
- Save the photo(s) alongside as `source-1.jpg`, `source-2.jpg`, etc.

## Starting and archiving a batch

- Start one with `tools/ferment start <slug> [--date YYYY-MM-DD]`; it opens
  the `batch` issue with a dated checklist.
- Log progress as issue comments; close the issue when the batch is done.
- Archive a closed batch with `tools/ferment archive <issue>`, which writes
  `batches/<start-date>-<slug>/log.md`.
