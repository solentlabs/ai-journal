---
name: maintain
description: Keep an ai-journal-mcp journal healthy — rebuild the search index, regenerate JOURNAL.md and theme views after hand edits, and check for orphans, duplicates, or unthemed entries. Use after bulk-editing entry files, after moving entries outside add_entry, when search looks stale, or for a periodic health check.
---

# ai-journal-mcp — Maintain

Markdown is the source of truth; the search index and the generated views are
disposable and rebuilt from it. This skill keeps them in sync and surfaces
drift.

## When to use

- You hand-edited or bulk-moved entry files (outside `add_entry`).
- Search results look stale or incomplete.
- A periodic health check on a journal.

## What to do

- **Rebuild the index.** The `reindex` MCP tool rebuilds search from the
  markdown sources. (CLI: `ai-journal-mcp reindex <paths...> --db <path>`.) The
  index is disposable — rebuild anytime, it changes no source data.
- **Regenerate views.** For a managed journal, `ai-journal-mcp refresh <root>`
  regenerates `JOURNAL.md` and `themes/`. It also rescues any dated entry a
  stale session appended directly to `JOURNAL.md` — saving it as a real entry
  before regenerating, so no text is lost.
- **Check health.** `list_themes` and `entries_over_time` (MCP) show the shape
  and spot gaps such as `(unthemed)` entries. `ai-journal-mcp scan <root>` (CLI)
  reports orphan files with no dated entries and duplicate groups.

## Principles

- Index and views are derived; markdown wins. Rebuild freely.
- Generated views (`JOURNAL.md`, `themes/*.md`) are never hand-edited — edits
  go in the entry files, then regenerate.
- `indexed`-mode journals are read-only; maintenance never rewrites them.
