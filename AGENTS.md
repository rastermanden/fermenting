# Project agent memory

This file is the project's committed home for project-intrinsic agent knowledge: build, test, release, architecture, and sharp-edge notes that should travel with the code.

- Correct entries that work proves wrong; add new ones only by deliberate maintainer choice, never as routine task output.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.

## Transcribing a recipe

- Read the cookbook photo(s) and write `recipes/<slug>/recipe.md`, keeping the original
  language and quantities exactly as printed; do not translate or convert units.
- Mark anything illegible in the photo with `[illegible]` (or similar) instead of guessing.
- Save the photo(s) alongside as `source-1.jpg`, `source-2.jpg`, etc.
- See README.md for the full frontmatter/schedule format.

## Batches

- Start one with `tools/ferment start <slug> [--date YYYY-MM-DD]`; it opens the `batch` issue.
- Log progress as issue comments; close the issue when the batch is done.
- Archive a closed batch with `tools/ferment archive <issue>`, which writes
  `batches/<start-date>-<slug>/log.md`.
