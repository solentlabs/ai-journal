#!/usr/bin/env python3
"""Mark this checkout as a trusted Claude Code workspace.

Claude Code ignores a project's committed ``.claude/settings.json`` permission
allowlist until the workspace has been trusted. Trust is recorded *per machine*
in ``~/.claude.json`` under ``projects["<absolute checkout path>"]`` — it cannot
live in the repo (the path differs per developer, and the file is global). This
script writes that flag idempotently so a new contributor clears the
"Ignoring N permissions.allow entries … this workspace has not been trusted"
warning with one command:

    make trust            # or the "Trust workspace for Claude Code" VS Code task

Stdlib only, so it runs with any ``python3`` — before the venv exists.

Exit codes (``--check`` mode, used by the folder-open Welcome message):
    0  already trusted, or status could not be determined safely (stay silent)
    1  confidently untrusted (show the nudge)
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import tempfile
from pathlib import Path

TRUST_KEY = "hasTrustDialogAccepted"


def default_config_path() -> Path:
    """Location of the per-user Claude Code config (``CLAUDE_CONFIG`` overrides)."""
    override = os.environ.get("CLAUDE_CONFIG")
    return Path(override) if override else Path.home() / ".claude.json"


def repo_root_from_script() -> str:
    """Absolute path of this checkout (this file is ``scripts/dev/`` under root)."""
    return str(Path(__file__).resolve().parents[2])


def load_config(path: Path) -> dict:
    """Read the config, or ``{}`` if absent. Raises ``ValueError`` if malformed.

    Refusing to parse a malformed file is deliberate: we never want to clobber a
    developer's global Claude config by overwriting content we could not read.
    """
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:  # pragma: no cover - exercised via ValueError
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return data


def is_trusted(config: dict, repo_root: str) -> bool:
    """True iff ``config`` records ``repo_root`` as a trusted workspace."""
    projects = config.get("projects")
    if not isinstance(projects, dict):
        return False
    entry = projects.get(repo_root)
    return isinstance(entry, dict) and entry.get(TRUST_KEY) is True


def set_trusted(config: dict, repo_root: str) -> bool:
    """Set the trust flag for ``repo_root``, preserving every other key.

    Returns ``True`` if ``config`` was changed, ``False`` if already trusted.
    """
    projects = config.get("projects")
    if not isinstance(projects, dict):
        projects = {}
        config["projects"] = projects
    entry = projects.get(repo_root)
    if not isinstance(entry, dict):
        entry = {}
        projects[repo_root] = entry
    if entry.get(TRUST_KEY) is True:
        return False
    entry[TRUST_KEY] = True
    return True


def write_config(path: Path, config: dict) -> None:
    """Atomically write ``config`` to ``path`` (temp file + replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".claude.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(config, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def ensure_trusted(config_path: Path, repo_root: str) -> bool:
    """Trust ``repo_root`` in ``config_path``. Returns ``True`` if a write occurred."""
    config = load_config(config_path)
    if not set_trusted(config, repo_root):
        return False
    write_config(config_path, config)
    return True


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Trust this checkout as a Claude Code workspace.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="report trust status without modifying anything (exit 1 if untrusted)",
    )
    parser.add_argument("--repo", default=None, help="checkout path to trust (default: this checkout)")
    parser.add_argument("--config", default=None, help="path to the Claude config (default: ~/.claude.json)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo_root = str(Path(args.repo).resolve()) if args.repo else repo_root_from_script()
    config_path = Path(args.config) if args.config else default_config_path()

    if args.check:
        try:
            trusted = is_trusted(load_config(config_path), repo_root)
        except ValueError:
            # Can't read the config safely — stay silent rather than nag/clobber.
            return 0
        return 0 if trusted else 1

    try:
        changed = ensure_trusted(config_path, repo_root)
    except ValueError as exc:
        print(f"✗ Cannot trust workspace: {exc}", file=sys.stderr)
        print("  Fix or remove the file, then re-run. Nothing was written.", file=sys.stderr)
        return 2

    if changed:
        print(f"✓ Trusted this workspace for Claude Code:\n    {repo_root}\n  (recorded in {config_path})")
    else:
        print(f"✓ Already trusted for Claude Code:\n    {repo_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
