# fermenting

Recipes and batch tracking for a home fermentation hobby. Works with any
coding agent (Claude Code, Codex, Copilot, Cursor, Pi, ...) or entirely by
hand - see AGENTS.md for the agent-facing summary and the sections below for
the full formats.

## Getting started (no agent required)

**Requirements:** Python 3 and the [`gh` CLI](https://cli.github.com/), logged
in (`gh auth login`).

1. Fork this repository (or copy it to your own new repo).
2. In your fork's Settings > Actions > General, enable Actions if they're
   disabled by default for forks.
3. Create the `batch` label once: `gh label create batch --color 6f4e37
   --description "A fermentation batch in progress"` (the daily-reminder
   workflow also creates it automatically on its first run if it's missing).
4. Add a recipe: transcribe a cookbook photo into `recipes/<slug>/recipe.md`
   (by hand, or ask any coding agent to do it - see AGENTS.md) and put the
   photo alongside it as `source-1.jpg`.
5. Start a batch either from your phone - open an issue with the "Start a
   batch" form under Issues > New issue - or from a checkout with
   `tools/ferment start <slug>`.
6. Log progress as comments on the batch issue (photos can be attached from
   the phone); close the issue when the batch is done.
7. Optionally archive the finished batch's log into the repo with
   `tools/ferment archive <issue>`.

The daily reminder job's timing is configurable, not tied to one person or
timezone - see [Timezone](#timezone) below.

## Recipe format

Each recipe lives at `recipes/<slug>/recipe.md`. The cookbook page photo(s) it was
transcribed from live alongside it as `source-1.jpg`, `source-2.jpg`, etc.

`recipe.md` starts with YAML frontmatter:

```yaml
---
title: Recipe title
source:
  book: Name of the cookbook
  page: 42
yield: "1 liter"
schedule:
  - day: 0
    task: Mix and seal the jar
  - days: 1-6
    task: Burp the jar and taste
  - day: 7
    task: Strain and bottle
---
```

- `day: N` is a single step on day N (day 0 is the start date of a batch).
- `days: A-B` repeats the same task every day from day A through day B, inclusive.
- `task` is a short description of what to do that day.

The body below the frontmatter is free-form Markdown: ingredients and method,
in whatever language and units the source used.

A fictional example recipe fixture lives at `fixtures/recipes/example-ferment/`
for tests and documentation; do not treat it as a real recipe.

## Batches

A batch (one run of a recipe) is tracked as a GitHub issue labeled `batch`:

- Started from the "Start a batch" issue form under `.github/ISSUE_TEMPLATE/`,
  which asks for the recipe slug and a start date (defaults to today).
- The issue body holds a machine-readable block with the recipe slug and start
  date, followed by the dated checklist of steps computed from the recipe's
  `schedule`.
- Comments on the issue are the log: notes and phone photos as things happen.
- Closing the issue marks the batch as done.

A small daily job (`.github/workflows/daily-reminder.yml`) comments each
morning on every open `batch` issue that has a step due that day, mentioning
the issue's author so it becomes a GitHub notification on the phone. It never
posts more than once per calendar day for the same issue, and posts nothing on
days with no due step. See [Timezone](#timezone) for how "morning" and
"today" are determined.

When a batch is finished (issue closed) and archived with
`tools/ferment archive <issue>`, the issue body and all comments are saved to
`batches/<start-date>-<slug>/log.md`, so the whole history ends up next to the
recipe it belongs to.

## `tools/ferment`

A small Python script (standard library only, plus the `gh` CLI for GitHub
calls):

- `tools/ferment today` — list everything due today across open batches.
- `tools/ferment start <slug> [--date YYYY-MM-DD]` — open a batch issue with
  the computed, dated checklist for that recipe.
- `tools/ferment fill-batch <issue> [--slug SLUG] [--date YYYY-MM-DD]` — fill
  in the dated checklist on a batch issue created from the issue form; run
  automatically by the daily-reminder workflow when a new `batch` issue opens.
- `tools/ferment remind` — comment on open batches with a step due today; run
  automatically by the daily-reminder workflow.
- `tools/ferment archive <issue>` — write a closed issue's body and comments to
  `batches/<start-date>-<slug>/log.md`.

Run its tests with:

```sh
python3 -m unittest discover -s tests
```

## Timezone

Nothing here is locked to one owner, language, or timezone. `tools/ferment`
computes "today" from the `FERMENT_TZ` environment variable - any IANA zone
name, e.g. `America/New_York` - defaulting to `Europe/Copenhagen` if unset.

To change it for the daily-reminder workflow, set a repository variable named
`FERMENT_TZ` (Settings > Secrets and variables > Actions > Variables). The
workflow itself runs on a fixed UTC cron - see the comment above the cron
line in `.github/workflows/daily-reminder.yml` for what that currently
resolves to in the default Europe/Copenhagen zone; if you use a different
`FERMENT_TZ`, edit that cron line to match your preferred local run time -
the environment variable only changes what counts as "today" for schedule
and reminder purposes, not when the workflow itself runs.
