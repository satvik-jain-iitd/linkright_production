"""Tests for profile create guard — partial-state regression (issue: any(iterdir()) false-positive)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

from click.testing import CliRunner

from linkright.profile.cli import create_cmd


def _fake_resume(tmp_path: Path) -> Path:
    p = tmp_path / "resume.pdf"
    p.touch()
    return p


class TestProfileCreateGuard:
    """Profile dir guard must check metadata.yaml, not just dir emptiness."""

    def test_scaffold_dirs_without_metadata_allows_create(self, tmp_path):
        """Partial profile (scaffold dirs, no metadata.yaml) must NOT block create.

        Regression: old guard used any(iterdir()) — empty artifact dirs from a
        prior failed run triggered "Profile already exists" while profile show
        and status both said "no profile found". User had no path forward.
        """
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        (profile_dir / "artifacts").mkdir()
        (profile_dir / "inputs").mkdir()
        (profile_dir / "logs").mkdir()
        # No metadata.yaml — incomplete profile from prior failed run

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli.parse_and_extract") as mock_extract, \
             patch("linkright.profile.cli.persist"), \
             patch("linkright.profile.cli.load_metadata", return_value={}), \
             patch("linkright.profile.cli.contact_verify_loop"), \
             patch("linkright.profile.cli.truth_engine_loop"):

            mock_extract.return_value = MagicMock()
            result = runner.invoke(create_cmd, ["-r", str(_fake_resume(tmp_path)), "--yes"])

        assert result.exit_code == 0, (
            f"create should proceed on partial profile dir (no metadata.yaml).\n"
            f"Output: {result.output}\nException: {result.exception}"
        )
        assert "already exists" not in result.output
        mock_extract.assert_called_once()  # guard must not short-circuit before extract

    def test_complete_profile_blocks_create_without_force(self, tmp_path):
        """Complete profile (metadata.yaml present) must block create without --force."""
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        (profile_dir / "metadata.yaml").write_text("n_nuggets: 10\n")

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir):
            result = runner.invoke(
                create_cmd,
                ["-r", str(_fake_resume(tmp_path))],
                catch_exceptions=False,
            )

        assert result.exit_code == 1
        assert "already exists" in result.output
        assert isinstance(result.exception, SystemExit)  # clean sys.exit(1), not an unrelated crash

    def test_empty_profile_dir_allows_create(self, tmp_path):
        """Completely empty profile dir must allow create (baseline case)."""
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli.parse_and_extract") as mock_extract, \
             patch("linkright.profile.cli.persist"), \
             patch("linkright.profile.cli.load_metadata", return_value={}), \
             patch("linkright.profile.cli.contact_verify_loop"), \
             patch("linkright.profile.cli.truth_engine_loop"):

            mock_extract.return_value = MagicMock()
            result = runner.invoke(create_cmd, ["-r", str(_fake_resume(tmp_path)), "--yes"])

        assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
        mock_extract.assert_called_once()

    def test_nonexistent_profile_dir_allows_create(self, tmp_path):
        """Non-existent profile dir must allow create (first-time user path)."""
        profile_dir = tmp_path / "profile"
        # profile_dir intentionally not created

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli.parse_and_extract") as mock_extract, \
             patch("linkright.profile.cli.persist"), \
             patch("linkright.profile.cli.load_metadata", return_value={}), \
             patch("linkright.profile.cli.contact_verify_loop"), \
             patch("linkright.profile.cli.truth_engine_loop"):

            mock_extract.return_value = MagicMock()
            result = runner.invoke(create_cmd, ["-r", str(_fake_resume(tmp_path)), "--yes"])

        assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
        mock_extract.assert_called_once()

    def test_force_flag_overwrites_complete_profile(self, tmp_path):
        """--force on complete profile must wipe then proceed (not block)."""
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        (profile_dir / "metadata.yaml").write_text("n_nuggets: 10\n")

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli._wipe") as mock_wipe, \
             patch("linkright.profile.cli.parse_and_extract") as mock_extract, \
             patch("linkright.profile.cli.persist"), \
             patch("linkright.profile.cli.load_metadata", return_value={}), \
             patch("linkright.profile.cli.contact_verify_loop"), \
             patch("linkright.profile.cli.truth_engine_loop"):

            mock_extract.return_value = MagicMock()
            result = runner.invoke(
                create_cmd,
                ["-r", str(_fake_resume(tmp_path)), "--force", "--yes"],
            )

        assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
        assert "already exists" not in result.output
        mock_wipe.assert_called_once()    # backup+wipe must fire on --force
        mock_extract.assert_called_once() # create must proceed after wipe
