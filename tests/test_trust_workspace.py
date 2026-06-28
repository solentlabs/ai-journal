"""Tests for ``scripts/dev/trust_workspace.py`` (Claude Code workspace trust).

The script lives outside the package (it's dev tooling that must run with a bare
``python3`` before the venv exists), so it's loaded by path via importlib. Pure
mapping logic is table-driven; the write path uses the ``claude_config`` factory
fixture (see ``conftest.py``) to prove idempotency and that unrelated config is
preserved, never clobbered.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "dev" / "trust_workspace.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("trust_workspace", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tw = _load()

ROOT = "/home/dev/checkout"


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        ({}, False),
        ({"projects": {}}, False),
        ({"projects": {ROOT: {}}}, False),
        ({"projects": {ROOT: {"hasTrustDialogAccepted": False}}}, False),
        ({"projects": {"/other": {"hasTrustDialogAccepted": True}}}, False),
        ({"projects": "not-a-dict"}, False),
        ({"projects": {ROOT: {"hasTrustDialogAccepted": True}}}, True),
    ],
)
def test_is_trusted(config: dict, expected: bool) -> None:
    assert tw.is_trusted(config, ROOT) is expected


def test_set_trusted_adds_projects_map_when_missing() -> None:
    config: dict = {"someOtherSetting": 1}
    changed = tw.set_trusted(config, ROOT)
    assert changed is True
    assert config["projects"][ROOT]["hasTrustDialogAccepted"] is True
    assert config["someOtherSetting"] == 1  # unrelated keys preserved


def test_set_trusted_preserves_sibling_projects_and_entry_keys() -> None:
    config = {"projects": {"/other": {"hasTrustDialogAccepted": True}, ROOT: {"history": ["x"]}}}
    changed = tw.set_trusted(config, ROOT)
    assert changed is True
    assert config["projects"]["/other"]["hasTrustDialogAccepted"] is True
    assert config["projects"][ROOT]["history"] == ["x"]  # existing entry data kept
    assert config["projects"][ROOT]["hasTrustDialogAccepted"] is True


def test_set_trusted_idempotent() -> None:
    config = {"projects": {ROOT: {"hasTrustDialogAccepted": True}}}
    assert tw.set_trusted(config, ROOT) is False


def test_ensure_trusted_creates_file_then_is_idempotent(claude_config) -> None:
    cfg = claude_config(name="nested/.claude.json")  # absent file, missing parent dir
    assert tw.ensure_trusted(cfg, ROOT) is True  # first run writes
    assert tw.is_trusted(json.loads(cfg.read_text()), ROOT) is True
    assert tw.ensure_trusted(cfg, ROOT) is False  # second run is a no-op


def test_ensure_trusted_preserves_existing_content(claude_config) -> None:
    cfg = claude_config({"projects": {"/other": {"hasTrustDialogAccepted": True}}, "numStartups": 7})
    tw.ensure_trusted(cfg, ROOT)
    data = json.loads(cfg.read_text())
    assert data["numStartups"] == 7
    assert data["projects"]["/other"]["hasTrustDialogAccepted"] is True
    assert data["projects"][ROOT]["hasTrustDialogAccepted"] is True


def test_malformed_config_raises_and_does_not_clobber(claude_config) -> None:
    cfg = claude_config("{ not json")
    with pytest.raises(ValueError):
        tw.ensure_trusted(cfg, ROOT)
    assert cfg.read_text() == "{ not json"  # left untouched


def test_check_mode_exit_codes(claude_config) -> None:
    cfg = claude_config()  # absent -> untrusted
    assert tw.main(["--check", "--repo", ROOT, "--config", str(cfg)]) == 1  # untrusted
    tw.ensure_trusted(cfg, ROOT)
    assert tw.main(["--check", "--repo", ROOT, "--config", str(cfg)]) == 0  # trusted


def test_check_mode_silent_on_malformed_config(claude_config) -> None:
    cfg = claude_config("{ not json")
    # Undeterminable status must stay silent (exit 0), not nag or error.
    assert tw.main(["--check", "--repo", ROOT, "--config", str(cfg)]) == 0


def test_main_write_mode_creates_then_idempotent(claude_config, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = claude_config()  # absent
    assert tw.main(["--repo", ROOT, "--config", str(cfg)]) == 0
    assert "Trusted this workspace" in capsys.readouterr().out
    assert tw.is_trusted(json.loads(cfg.read_text()), ROOT) is True
    assert tw.main(["--repo", ROOT, "--config", str(cfg)]) == 0  # second run
    assert "Already trusted" in capsys.readouterr().out


def test_main_write_mode_malformed_config_errors(claude_config, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = claude_config("{ not json")
    assert tw.main(["--repo", ROOT, "--config", str(cfg)]) == 2
    assert "Cannot trust workspace" in capsys.readouterr().err
    assert cfg.read_text() == "{ not json"  # left untouched


def test_repo_root_from_script_points_at_checkout() -> None:
    root = Path(tw.repo_root_from_script())
    assert (root / "scripts" / "dev" / "trust_workspace.py").is_file()
    assert (root / "pyproject.toml").is_file()


def test_default_config_path_honors_env_then_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CONFIG", "/custom/claude.json")
    assert tw.default_config_path() == Path("/custom/claude.json")
    monkeypatch.delenv("CLAUDE_CONFIG", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path("/home/someone")))
    assert tw.default_config_path() == Path("/home/someone/.claude.json")


def test_main_resolves_default_repo_and_config(claude_config, monkeypatch: pytest.MonkeyPatch) -> None:
    # No --repo / --config: must trust *this* checkout in the env-pointed config.
    cfg = claude_config()
    monkeypatch.setenv("CLAUDE_CONFIG", str(cfg))
    assert tw.main([]) == 0
    assert tw.is_trusted(json.loads(cfg.read_text()), tw.repo_root_from_script()) is True


def test_load_config_treats_blank_file_as_empty(claude_config) -> None:
    assert tw.load_config(claude_config("   \n")) == {}


def test_load_config_rejects_non_object_json(claude_config) -> None:
    cfg = claude_config("[1, 2, 3]")  # valid JSON, but not an object
    with pytest.raises(ValueError, match="does not contain a JSON object"):
        tw.ensure_trusted(cfg, ROOT)


def test_write_config_failure_leaves_no_temp_and_does_not_corrupt(
    claude_config, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = claude_config('{"keep": true}')

    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(tw.os, "replace", boom)
    with pytest.raises(OSError, match="disk full"):
        tw.write_config(cfg, {"keep": True, "added": 1})
    assert cfg.read_text() == '{"keep": true}'  # original untouched
    assert not list(cfg.parent.glob(".claude.*.tmp"))  # temp cleaned up
