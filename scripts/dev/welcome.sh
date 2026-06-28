#!/usr/bin/env bash
# Printed on VS Code folder-open (see .vscode/tasks.json "Welcome", runOn:
# folderOpen) so a first-time contributor gets an unmissable starting point —
# even if they never open a terminal. Picks the message by venv state and
# reuses the same text the terminal greeting shows.
set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"

if [ -x "$ROOT/.venv/bin/python" ]; then
    cat "$DIR/next_steps.txt"
else
    cat "$DIR/welcome_message.txt"
fi

# Claude Code trust nudge: shown whenever this checkout isn't a trusted
# workspace yet (so its committed permission allowlist is being ignored).
# Stdlib-only check, runs with system python3 even before the venv exists;
# silent if python3 is missing or the trust status can't be read safely.
if command -v python3 >/dev/null 2>&1; then
    if ! python3 "$DIR/trust_workspace.py" --check >/dev/null 2>&1; then
        cat "$DIR/trust_nudge.txt"
    fi
fi
