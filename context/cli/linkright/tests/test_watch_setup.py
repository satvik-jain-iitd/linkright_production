"""Unit tests for `linkright watch setup` — alias generation + idempotency."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parents[1] / "src"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from linkright.watch import setup as setup_mod


def test_build_alias_line_macos_open_na():
    line = setup_mod.build_alias_line(
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        Path("/Users/x/.zshrc"),
    )
    # macOS uses `open -na <path> --args --remote-debugging-port=9222`
    assert "open -na" in line
    assert "remote-debugging-port=9222" in line
    assert "Google Chrome.app" in line


def test_build_alias_line_fish_function():
    line = setup_mod.build_alias_line(
        "/usr/bin/google-chrome",
        Path("/home/x/.config/fish/config.fish"),
    )
    assert line.startswith("function chrome")
    assert "remote-debugging-port=9222" in line
    assert line.endswith("end")


def test_install_alias_first_time(tmp_path):
    cfg = tmp_path / ".zshrc"
    cfg.write_text("# existing line\n")

    alias = "alias chrome='echo test'"
    changed, msg = setup_mod.install_alias(cfg, alias)

    assert changed is True
    contents = cfg.read_text()
    assert setup_mod.ALIAS_MARK_BEGIN in contents
    assert setup_mod.ALIAS_MARK_END in contents
    assert alias in contents
    assert "# existing line" in contents  # didn't clobber existing config


def test_install_alias_idempotent(tmp_path):
    cfg = tmp_path / ".zshrc"
    alias = "alias chrome='echo test'"

    # First install
    changed1, _ = setup_mod.install_alias(cfg, alias)
    contents1 = cfg.read_text()

    # Re-install with SAME alias — should be a no-op
    changed2, msg2 = setup_mod.install_alias(cfg, alias)

    assert changed1 is True
    assert changed2 is False
    assert "up-to-date" in msg2
    assert cfg.read_text() == contents1


def test_install_alias_replaces_existing_block(tmp_path):
    cfg = tmp_path / ".zshrc"
    cfg.write_text("# existing\n")

    setup_mod.install_alias(cfg, "alias chrome='OLD'")
    changed, _ = setup_mod.install_alias(cfg, "alias chrome='NEW'")

    contents = cfg.read_text()
    assert changed is True
    assert "alias chrome='NEW'" in contents
    assert "alias chrome='OLD'" not in contents
    # Block markers still present (only one set, not duplicated)
    assert contents.count(setup_mod.ALIAS_MARK_BEGIN) == 1
    assert contents.count(setup_mod.ALIAS_MARK_END) == 1


def test_install_alias_dry_run_does_not_write(tmp_path):
    cfg = tmp_path / ".zshrc"
    cfg.write_text("# untouched\n")

    changed, msg = setup_mod.install_alias(cfg, "alias chrome='x'", dry_run=True)

    assert changed is True
    assert "WOULD" in msg
    assert cfg.read_text() == "# untouched\n"  # nothing written


def test_remove_alias_strips_block_cleanly(tmp_path):
    cfg = tmp_path / ".zshrc"
    cfg.write_text("# before\n")

    setup_mod.install_alias(cfg, "alias chrome='x'")
    changed, _ = setup_mod.remove_alias(cfg)

    assert changed is True
    contents = cfg.read_text()
    assert setup_mod.ALIAS_MARK_BEGIN not in contents
    assert setup_mod.ALIAS_MARK_END not in contents
    assert "# before" in contents


def test_remove_alias_no_block_present(tmp_path):
    cfg = tmp_path / ".zshrc"
    cfg.write_text("# nothing to remove\n")

    changed, msg = setup_mod.remove_alias(cfg)

    assert changed is False
    assert "no linkright alias block" in msg


def test_install_alias_creates_file_if_missing(tmp_path):
    cfg = tmp_path / "nested" / "dir" / ".zshrc"
    assert not cfg.exists()

    changed, _ = setup_mod.install_alias(cfg, "alias chrome='x'")

    assert changed is True
    assert cfg.exists()
    assert "alias chrome='x'" in cfg.read_text()
