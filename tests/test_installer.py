#!/usr/bin/env python3
"""Fast, offline tests for the release installer."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from installer import core as installer


class InstallerHelpersTest(unittest.TestCase):
    def test_detects_debian_derivative_from_id_like(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "os-release"
            path.write_text('ID=linuxmint\nID_LIKE="ubuntu debian"\nVERSION_ID="22.04"\nPRETTY_NAME="Linux Mint"\n', encoding="utf-8")
            distro = installer.detect_distro(path)
        self.assertEqual(distro.family, "debian")
        self.assertEqual(distro.identifier, "linuxmint")

    def test_detects_arch_derivative(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "os-release"
            path.write_text('ID=cachyos\nID_LIKE=arch\nVERSION_ID=2026\n', encoding="utf-8")
            distro = installer.detect_distro(path)
        self.assertEqual(distro.family, "arch")

    def test_supported_distribution_families(self):
        samples = {
            "ubuntu": "ID=ubuntu\nVERSION_ID=24.04\n",
            "debian": "ID=debian\nVERSION_ID=12\n",
            "pop": "ID=pop\nID_LIKE=ubuntu\nVERSION_ID=22.04\n",
            "manjaro": "ID=manjaro\nID_LIKE=arch\n",
            "endeavouros": "ID=endeavouros\nID_LIKE=arch\n",
        }
        for identifier, content in samples.items():
            with self.subTest(identifier=identifier), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "os-release"
                path.write_text(content, encoding="utf-8")
                distro = installer.detect_distro(path)
                self.assertIn(distro.family, {"debian", "arch"})

    def test_rejects_unknown_distribution(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "os-release"
            path.write_text('ID=fedora\nPRETTY_NAME=Fedora\n', encoding="utf-8")
            with self.assertRaises(installer.InstallerError):
                installer.detect_distro(path)

    def test_selects_the_first_published_release(self):
        releases = [
            {"tag_name": "v0.4.0-Beta", "draft": False, "prerelease": True},
            {"tag_name": "v0.3.2", "draft": False, "prerelease": False},
        ]
        self.assertEqual(installer.latest_published_release(releases)["tag_name"], "v0.4.0-Beta")

    def test_skips_draft_releases_when_selecting_latest(self):
        releases = [
            {"tag_name": "v0.5.0", "draft": True},
            {"tag_name": "v0.4.0", "draft": False},
        ]
        self.assertEqual(installer.latest_published_release(releases)["tag_name"], "v0.4.0")

    def test_rejects_an_empty_release_list(self):
        with self.assertRaises(installer.InstallerError):
            installer.latest_published_release([])

    def test_parses_sha256sum_formats(self):
        checksums = installer.parse_checksums(
            "a" * 64 + "  installer.py\n" + "b" * 64 + " *rdp-session-manager.deb\n"
        )
        self.assertEqual(checksums["installer.py"], "a" * 64)
        self.assertEqual(checksums["rdp-session-manager.deb"], "b" * 64)

    def test_parses_native_fraction_progress(self):
        self.assertEqual(
            installer.parse_progress_fraction("( 3/12) instalando pacote"),
            (3, 12),
        )

    def test_parses_native_percentage_progress(self):
        self.assertEqual(
            installer.parse_progress_fraction("Progress: [ 47% ] configurando"),
            (47, 100),
        )
        self.assertEqual(
            installer.parse_progress_fraction("pacote 8 MiB 83% concluído"),
            (83, 100),
        )

    def test_ignores_regular_command_output_as_progress(self):
        self.assertIsNone(installer.parse_progress_fraction("baixando pacote normalmente"))

    def test_enables_commented_arch_multilib_block(self):
        original = (
            "[core]\n"
            "Include = /etc/pacman.d/mirrorlist\n\n"
            "#[multilib]\n"
            "#Include = /etc/pacman.d/mirrorlist\n"
        )
        updated = installer.enable_multilib_config(original)
        self.assertIn("\n[multilib]\nInclude = /etc/pacman.d/mirrorlist\n", updated)
        self.assertNotIn("#[multilib]", updated)

    def test_multilib_configuration_is_idempotent(self):
        original = "[multilib]\nInclude = /etc/pacman.d/mirrorlist\n"
        self.assertEqual(installer.enable_multilib_config(original), original)

    def test_appends_multilib_when_configuration_has_no_block(self):
        updated = installer.enable_multilib_config("[core]\nInclude = /etc/pacman.d/mirrorlist\n")
        self.assertTrue(updated.endswith("[multilib]\nInclude = /etc/pacman.d/mirrorlist\n"))

    def test_extracts_and_deduplicates_pkgbuild_pgp_fingerprints(self):
        fingerprint = "61ECEABBF2BB40E3A35DF30A9F72CDBC01BF10EB"
        text = f"validpgpkeys=(\n  '{fingerprint}'\n  \"{fingerprint.lower()}\"\n)\n"
        self.assertEqual(installer.pkgbuild_pgp_keys(text), [fingerprint])

    def test_runner_dry_run_does_not_execute_command(self):
        ui = installer.UI(dry_run=True)
        with tempfile.TemporaryDirectory() as directory:
            log = installer.InstallLog()
            try:
                runner = installer.Runner(ui, log, dry_run=True)
                with patch("subprocess.Popen") as popen:
                    result = runner.run(["command-that-must-not-run"])
                popen.assert_not_called()
                self.assertEqual(result.returncode, 0)
            finally:
                log.close()

    def test_dry_run_installer_does_not_query_network(self):
        args = installer.parser().parse_args(["--dry-run", "--yes", "--os-release", "/etc/os-release"])
        with patch("installer.core.http_json", side_effect=AssertionError("network access in dry-run")):
            instance = installer.Installer(args)
            try:
                self.assertEqual(instance.run(), 0)
            finally:
                # run() already closes resources; this is safe for a test that
                # fails before entering the normal cleanup path.
                if not instance.log.handle.closed:
                    instance.close()

    def test_yay_install_is_non_interactive_after_confirmation(self):
        args = installer.parser().parse_args(
            ["--dry-run", "--yes", "--os-release", "/etc/os-release"]
        )
        instance = installer.Installer(args)
        instance.args.without_xrdp = False
        try:
            with (
                patch.object(instance, "aur_helper", return_value="yay"),
                patch.object(instance.runner, "run") as run,
            ):
                instance.install_arch_xrdp()
            command = run.call_args.args[0]
            self.assertIn("--noconfirm", command)
            self.assertIn("--answerclean", command)
            self.assertIn("--answerdiff", command)
            self.assertIn("--noremovemake", command)
            self.assertIn("--pgpfetch", command)
        finally:
            instance.close()

    def test_arch_wine_dependencies_use_current_multilib_packages(self):
        args = installer.parser().parse_args(
            ["--dry-run", "--yes", "--with-wine", "--os-release", "/etc/os-release"]
        )
        instance = installer.Installer(args)
        instance.distro = installer.Distro(
            family="arch",
            identifier="arch",
            version="rolling",
            name="Arch Linux",
            id_like=("arch",),
        )
        try:
            packages = instance.package_names()
            self.assertIn("7zip", packages)
            self.assertIn("lib32-vulkan-icd-loader", packages)
            self.assertNotIn("p7zip", packages)
        finally:
            instance.close()


if __name__ == "__main__":
    unittest.main()
