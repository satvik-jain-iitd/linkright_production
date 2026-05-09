"""Tests for profile create guard — partial-state regression (issue: any(iterdir()) false-positive)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from linkright.profile.cli import create_cmd


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
             patch("linkright.profile.cli.persist") as mock_persist, \
             patch("linkright.profile.cli.load_metadata", return_value={}), \
             patch("linkright.profile.cli.contact_verify_loop"), \
             patch("linkright.profile.cli.truth_engine_loop"):

            mock_extract.return_value = MagicMock()

            fake_resume = tmp_path / "resume.pdf"
            fake_resume.touch()

            result = runner.invoke(create_cmd, ["-r", str(fake_resume), "--yes"])

        assert result.exit_code == 0, (
            f"create should proceed on partial profile dir (no metadata.yaml).\n"
            f"Output: {result.output}"
        )
        assert "already exists" not in result.output

    def test_complete_profile_blocks_create_without_force(self, tmp_path):
        """Complete profile (metadata.yaml present) must block create without --force."""
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        (profile_dir / "metadata.yaml").write_text("n_nuggets: 10\n")

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir):
            fake_resume = tmp_path / "resume.pdf"
            fake_resume.touch()
            result = runner.invoke(create_cmd, ["-r", str(fake_resume)])

        assert result.exit_code == 1
        assert "already exists" in result.output

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

            fake_resume = tmp_path / "resume.pdf"
            fake_resume.touch()
            result = runner.invoke(create_cmd, ["-r", str(fake_resume), "--yes"])

        assert result.exit_code == 0, f"Output: {result.output}"

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

            fake_resume = tmp_path / "resume.pdf"
            fake_resume.touch()
            result = runner.invoke(create_cmd, ["-r", str(fake_resume), "--yes"])

        assert result.exit_code == 0, f"Output: {result.output}"
