import pytest

import ai_journal_mcp.config as config
from ai_journal_mcp.cli import main
from ai_journal_mcp.config import add_journal, load_config
from ai_journal_mcp.store import init_journal, is_managed


def test_init_creates_managed_journal_and_registers(tmp_path):
    cfg = tmp_path / "journals.toml"
    root, registered = init_journal(tmp_path / "journal", config_path=cfg)

    assert registered is True
    assert is_managed(root)
    assert (root / "entries").is_dir()
    sources = load_config(cfg)
    assert len(sources) == 1
    assert sources[0].name == "journal"
    assert sources[0].mode == "managed"
    assert sources[0].path == root


def test_init_appends_to_existing_config(tmp_path):
    cfg = tmp_path / "journals.toml"
    init_journal(tmp_path / "a", name="alpha", config_path=cfg)
    init_journal(tmp_path / "b", name="beta", config_path=cfg)
    assert [s.name for s in load_config(cfg)] == ["alpha", "beta"]


def test_init_skips_duplicate_name(tmp_path):
    cfg = tmp_path / "journals.toml"
    init_journal(tmp_path / "a", name="dup", config_path=cfg)
    _, registered = init_journal(tmp_path / "a2", name="dup", config_path=cfg)
    assert registered is False
    assert len(load_config(cfg)) == 1


def test_init_refuses_existing_managed(tmp_path):
    cfg = tmp_path / "journals.toml"
    root = tmp_path / "journal"
    init_journal(root, config_path=cfg)
    with pytest.raises(FileExistsError, match="already a managed journal"):
        init_journal(root, config_path=cfg)


def test_add_journal_creates_missing_config_dir(tmp_path):
    cfg = tmp_path / "nested" / "journals.toml"
    assert add_journal("x", tmp_path / "x", config_path=cfg) is True
    assert cfg.exists()
    assert load_config(cfg)[0].name == "x"


def test_cli_init(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "DEFAULT_CONFIG", tmp_path / "journals.toml")
    root = tmp_path / "my-journal"
    assert main(["init", str(root)]) == 0
    out = capsys.readouterr().out
    assert "Created managed journal" in out
    assert (root / "entries").is_dir()
    assert load_config(tmp_path / "journals.toml")[0].name == "my-journal"
