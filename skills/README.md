# ai-journal skills

Claude Code skills bundled with ai-journal. They're **model-invoked** — Claude
loads one when its `description` matches what you're doing (e.g. "journal
this"); no slash command required.

| Skill | What it does |
| ----- | ------------ |
| [`capture`](capture/SKILL.md) | Capture a session insight/lesson into a managed journal via `add_entry`. |
| [`maintain`](maintain/SKILL.md) | Rebuild the index, regenerate views, and check journal health. |

## Distribution

These reach users via the Claude Code plugin (a `solentlabs` / Anthropic
marketplace entry), whose MCP config launches the published package. They are
not part of the pip wheel — Claude Code skills aren't a Python artifact. To use
one now, copy its directory into `~/.claude/skills/` (or a project's
`.claude/skills/`).
