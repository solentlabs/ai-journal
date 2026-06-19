"""Load journal sources from journals.toml."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG = Path("~/.config/ai-journal/journals.toml").expanduser()
DEFAULT_DB = Path("~/.local/share/ai-journal/index.db").expanduser()


@dataclass
class JournalSource:
    name: str
    path: Path
    mode: str  # "managed" | "indexed"


def load_config(config_path: Path | None = None) -> list[JournalSource]:
    path = config_path or DEFAULT_CONFIG
    if not path.exists():
        raise FileNotFoundError(
            f"No config at {path}. Create it with [[journal]] entries (name, path, mode = 'managed' or 'indexed')."
        )
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    sources = []
    for raw in data.get("journal", []):
        sources.append(
            JournalSource(
                name=raw["name"],
                path=Path(raw["path"]).expanduser(),
                mode=raw.get("mode", "indexed"),
            )
        )
    return sources


def add_journal(
    name: str,
    path: Path,
    mode: str = "managed",
    config_path: Path | None = None,
) -> bool:
    """Append a ``[[journal]]`` stanza to journals.toml, creating it if absent.

    Returns False (changing nothing) if a journal with this name is already
    configured. The path is written verbatim; ``load_config`` expands it.
    """
    cfg = config_path or DEFAULT_CONFIG
    if cfg.exists():
        if any(src.name == name for src in load_config(cfg)):
            return False
        existing = cfg.read_text(encoding="utf-8").rstrip("\n")
        prefix = f"{existing}\n\n" if existing else ""
    else:
        cfg.parent.mkdir(parents=True, exist_ok=True)
        prefix = ""
    stanza = f'[[journal]]\nname = "{name}"\npath = "{path}"\nmode = "{mode}"\n'
    cfg.write_text(prefix + stanza, encoding="utf-8")
    return True
