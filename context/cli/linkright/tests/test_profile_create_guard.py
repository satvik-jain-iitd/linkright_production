"""Tests for profile create guard — partial-state regression (issue: any(iterdir()) false-positive).

Also covers UAT bug #9: the interactive overwrite picker (Keep / Overwrite /
View) replaces the older flag-suggestion error when stdin is a TTY. Non-TTY
preserves the original `--force`-suggesting error so CI scripts stay
deterministic.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

from click.testing import CliRunner

from linkright.profile.cli import create_cmd


# Minimal valid PDF (a single empty page) — enough to pass pypdf's readability
# guard so the create-guard tests don't trip the "✗ Cannot read PDF" branch.
# Generated once via pypdf and embedded as bytes; deterministic and tiny.
_MIN_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj <</Type/Catalog/Pages 2 0 R>> endobj\n"
    b"2 0 obj <</Type/Pages/Kids[3 0 R]/Count 1>> endobj\n"
    b"3 0 obj <</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>> endobj\n"
    b"xref\n0 4\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000056 00000 n \n"
    b"0000000111 00000 n \n"
    b"trailer <</Size 4/Root 1 0 R>>\n"
    b"startxref\n182\n%%EOF\n"
)


def _fake_resume(tmp_path: Path) -> Path:
    p = tmp_path / "resume.pdf"
    p.write_bytes(_MIN_PDF_BYTES)
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

    def test_complete_profile_blocks_create_without_force_in_non_tty(self, tmp_path):
        """Complete profile + non-TTY stdin must block with the legacy --force hint.

        Non-TTY (CI / piped) sticks with the original error: the interactive
        picker is unreachable, so the safe behaviour is the same error message
        the CLI shipped before UAT bug #9. Power-user --force remains the
        explicit opt-in for unattended overwrite.
        """
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        (profile_dir / "metadata.yaml").write_text("n_nuggets: 10\n")

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli._is_interactive", return_value=False):
            result = runner.invoke(
                create_cmd,
                ["-r", str(_fake_resume(tmp_path))],
                catch_exceptions=False,
            )

        assert result.exit_code == 1
        assert "already exists" in result.output
        assert "--force" in result.output  # legacy hint preserved for non-TTY
        assert isinstance(result.exception, SystemExit)

    def test_complete_profile_interactive_overwrite_keep_cancels(self, tmp_path):
        """UAT bug #9: TTY + 'keep' choice from picker must cancel cleanly, no wipe."""
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        (profile_dir / "metadata.yaml").write_text("n_nuggets: 10\n")

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli._is_interactive", return_value=True), \
             patch("linkright.profile.cli._prompt_overwrite_existing", return_value="keep"), \
             patch("linkright.profile.cli._wipe") as mock_wipe, \
             patch("linkright.profile.cli.parse_and_extract") as mock_extract:
            result = runner.invoke(create_cmd, ["-r", str(_fake_resume(tmp_path))])

        assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
        assert "Kept existing profile" in result.output
        mock_wipe.assert_not_called()
        mock_extract.assert_not_called()

    def test_complete_profile_interactive_overwrite_overwrite_wipes(self, tmp_path):
        """UAT bug #9: TTY + 'overwrite' choice must wipe + re-ingest (no --force needed)."""
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        (profile_dir / "metadata.yaml").write_text("n_nuggets: 10\n")

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli._is_interactive", return_value=True), \
             patch("linkright.profile.cli._prompt_overwrite_existing", return_value="overwrite"), \
             patch("linkright.profile.cli._wipe") as mock_wipe, \
             patch("linkright.profile.cli.parse_and_extract") as mock_extract, \
             patch("linkright.profile.cli.persist"), \
             patch("linkright.profile.cli.load_metadata", return_value={}), \
             patch("linkright.profile.cli.contact_verify_loop"), \
             patch("linkright.profile.cli.truth_engine_loop"):
            mock_extract.return_value = MagicMock()
            result = runner.invoke(
                create_cmd, ["-r", str(_fake_resume(tmp_path)), "--yes"]
            )

        assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
        mock_wipe.assert_called_once()
        mock_extract.assert_called_once()

    def test_complete_profile_interactive_overwrite_view_shows_and_exits(self, tmp_path):
        """UAT bug #9: TTY + 'view' must render existing profile then exit cleanly."""
        profile_dir = tmp_path / "profile"
        profile_dir.mkdir()
        (profile_dir / "metadata.yaml").write_text("n_nuggets: 10\n")

        runner = CliRunner()
        with patch("linkright.profile.cli._profile_dir", return_value=profile_dir), \
             patch("linkright.profile.cli._is_interactive", return_value=True), \
             patch("linkright.profile.cli._prompt_overwrite_existing", return_value="view"), \
             patch("linkright.profile.cli._wipe") as mock_wipe, \
             patch("linkright.profile.cli.parse_and_extract") as mock_extract, \
             patch("linkright.profile.render.show_profile") as mock_show:
            result = runner.invoke(create_cmd, ["-r", str(_fake_resume(tmp_path))])

        assert result.exit_code == 0, f"Output: {result.output}\nException: {result.exception}"
        mock_show.assert_called_once()
        mock_wipe.assert_not_called()
        mock_extract.assert_not_called()

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
