#!/usr/bin/env python3
"""Fast, offline tests for the release installer."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from installer import core as installer


class InstallerHelpersTest(unittest.TestCase):
    @patch.dict("installer.core.os.environ", {}, clear=True)
    def test_headless_installer_uses_terminal_sudo(self):
        instance = object.__new__(installer.Installer)

        self.assertIsNone(instance._configure_graphical_auth())
        instance.askpass = None
        with patch("installer.core.os.geteuid", return_value=1000):
            self.assertEqual(instance.privilege(), ["sudo"])

    @patch("installer.core.shutil.which", return_value="/usr/bin/ksshaskpass")
    @patch.dict(
        "installer.core.os.environ",
        {"DISPLAY": "localhost:10.0"},
        clear=True,
    )
    def test_forwarded_display_without_session_bus_uses_terminal_sudo(self, _which):
        instance = object.__new__(installer.Installer)

        self.assertIsNone(instance._configure_graphical_auth())

    @patch("installer.core.shutil.which", return_value="/usr/bin/ksshaskpass")
    @patch("sys.stdin.isatty", return_value=False)
    @patch.dict(
        "installer.core.os.environ",
        {
            "DISPLAY": ":0",
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
        },
        clear=True,
    )
    def test_desktop_installer_configures_graphical_askpass(self, _isatty, _which):
        instance = object.__new__(installer.Installer)

        self.assertEqual(
            instance._configure_graphical_auth(),
            "/usr/bin/ksshaskpass",
        )
        self.assertEqual(
            installer.os.environ["SUDO_ASKPASS"],
            "/usr/bin/ksshaskpass",
        )

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
            "ubuntu": ("debian", "ID=ubuntu\nVERSION_ID=24.04\n"),
            "debian": ("debian", "ID=debian\nVERSION_ID=13\n"),
            "linuxmint": ("debian", 'ID=linuxmint\nID_LIKE="ubuntu debian"\nVERSION_ID=22\n'),
            "pop": ("debian", 'ID=pop\nID_LIKE="ubuntu debian"\nVERSION_ID=22.04\n'),
            "arch": ("arch", "ID=arch\n"),
            "manjaro": ("arch", "ID=manjaro\nID_LIKE=arch\n"),
            "endeavouros": ("arch", "ID=endeavouros\nID_LIKE=arch\n"),
            "cachyos": ("arch", "ID=cachyos\nID_LIKE=arch\n"),
        }
        for identifier, (expected_family, content) in samples.items():
            with self.subTest(identifier=identifier), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "os-release"
                path.write_text(content, encoding="utf-8")
                distro = installer.detect_distro(path)
                self.assertEqual(distro.family, expected_family)

                instance = object.__new__(installer.Installer)
                instance.distro = distro
                instance.args = SimpleNamespace(without_xrdp=False, with_wine=False)
                packages = instance.package_names()
                expected_package = "xrdp" if expected_family == "debian" else "xorg-server"
                self.assertIn(expected_package, packages)

    def test_rejects_unknown_distribution(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "os-release"
            path.write_text('ID=fedora\nPRETTY_NAME=Fedora\n', encoding="utf-8")
            with self.assertRaises(installer.InstallerError):
                installer.detect_distro(path)

    def test_accepts_latest_stable_release(self):
        release = {"tag_name": "v0.3.2", "draft": False, "prerelease": False}
        self.assertEqual(installer.validate_stable_release(release)["tag_name"], "v0.3.2")

    def test_rejects_prerelease_as_latest_stable(self):
        release = {"tag_name": "v0.3.2-Beta", "draft": False, "prerelease": True}
        with self.assertRaises(installer.InstallerError):
            installer.validate_stable_release(release)

    def test_rejects_invalid_latest_release_response(self):
        with self.assertRaises(installer.InstallerError):
            installer.validate_stable_release([])

    def test_parses_sha256sum_formats(self):
        checksums = installer.parse_checksums(
            "a" * 64 + "  installer.py\n" + "b" * 64 + " *rdp-session-manager.deb\n"
        )
        self.assertEqual(checksums["installer.py"], "a" * 64)
        self.assertEqual(checksums["rdp-session-manager.deb"], "b" * 64)

    def test_bundle_uses_resolved_release_and_validates_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle_dir = Path(directory)
            packages = {
                installer.APP_DEB: b"deb package fixture",
                installer.APP_ARCH: b"arch package fixture",
            }
            checksums = []
            for name, content in packages.items():
                package = bundle_dir / name
                package.write_bytes(content)
                checksums.append(f"{installer.sha256(package)} *{name}")
            (bundle_dir / "SHA256SUMS").write_text(
                "\n".join(checksums) + "\n",
                encoding="utf-8",
            )
            args = installer.parser().parse_args(
                [
                    "--bundle-dir",
                    directory,
                    "--resolved-release",
                    "v0.3.5",
                    "--dry-run",
                    "--yes",
                    "--os-release",
                    "/etc/os-release",
                ]
            )
            instance = installer.Installer(args)
            try:
                self.assertEqual(instance.release_info()["tag_name"], "v0.3.5")
                for name in packages:
                    self.assertEqual(
                        instance.bundled_asset(name),
                        bundle_dir / name,
                    )
            finally:
                instance.close()

    def test_bundle_rejects_invalid_asset_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle_dir = Path(directory)
            package = bundle_dir / installer.APP_ARCH
            package.write_bytes(b"arch package fixture")
            (bundle_dir / "SHA256SUMS").write_text(
                f"{'0' * 64} *{installer.APP_ARCH}\n",
                encoding="utf-8",
            )
            args = installer.parser().parse_args(
                [
                    "--bundle-dir",
                    directory,
                    "--resolved-release",
                    "v0.3.5",
                    "--dry-run",
                    "--yes",
                    "--os-release",
                    "/etc/os-release",
                ]
            )
            instance = installer.Installer(args)
            try:
                with self.assertRaises(installer.InstallerError):
                    instance.bundled_asset(installer.APP_ARCH)
            finally:
                instance.close()

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

    def test_terminal_auth_does_not_force_graphical_askpass(self):
        instance = object.__new__(installer.Installer)
        with (
            patch.object(installer.sys.stdin, "isatty", return_value=True),
            patch.dict("os.environ", {"DISPLAY": ":99"}, clear=True),
            patch("shutil.which", return_value="/usr/bin/ssh-askpass"),
        ):
            self.assertIsNone(instance._configure_graphical_auth())

    def test_authenticates_sudo_before_live_progress(self):
        instance = object.__new__(installer.Installer)
        instance.args = SimpleNamespace(dry_run=False)
        instance.ui = Mock()
        instance.askpass = None
        with (
            patch("os.geteuid", return_value=1000),
            patch("subprocess.run", return_value=Mock(returncode=0)) as run,
        ):
            instance.authenticate_privileges()
        run.assert_called_once_with(["sudo", "-v"], timeout=300, check=False)

    def test_reports_failed_sudo_authentication(self):
        instance = object.__new__(installer.Installer)
        instance.args = SimpleNamespace(dry_run=False)
        instance.ui = Mock()
        instance.askpass = None
        with (
            patch("os.geteuid", return_value=1000),
            patch("subprocess.run", return_value=Mock(returncode=1)),
            self.assertRaisesRegex(installer.InstallerError, "authentication failed"),
        ):
            instance.authenticate_privileges()

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

    def test_debian_wine_enables_i386_before_apt_update(self):
        args = installer.parser().parse_args(
            ["--dry-run", "--yes", "--with-wine", "--os-release", "/etc/os-release"]
        )
        instance = installer.Installer(args)
        instance.distro = installer.Distro(
            family="debian",
            identifier="ubuntu",
            version="24.04",
            name="Ubuntu 24.04",
            id_like=("debian",),
        )
        instance.args.without_xrdp = True
        app_path = Path("/tmp/rdp-session-manager.deb")
        try:
            with (
                patch("platform.machine", return_value="x86_64"),
                patch.object(instance.runner, "run") as run,
            ):
                run.side_effect = [
                    Mock(stdout="", returncode=0),
                    Mock(stdout="", returncode=0),
                    Mock(stdout="", returncode=0),
                    Mock(stdout="", returncode=0),
                    Mock(stdout="", returncode=0),
                ]
                instance.install_debian(app_path)
            commands = [call.args[0] for call in run.call_args_list]
            self.assertEqual(commands[0], ["dpkg", "--print-foreign-architectures"])
            self.assertEqual(commands[1][-3:], ["dpkg", "--add-architecture", "i386"])
            self.assertEqual(commands[2][-2:], ["apt-get", "update"])
            self.assertTrue(commands[4][-1].endswith("install-umu-launcher.sh"))
        finally:
            instance.close()


if __name__ == "__main__":
    unittest.main()
