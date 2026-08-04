#!/usr/bin/env python3
"""Tests for the archive validation used by the UMU installer."""

import importlib.util
import io
import tarfile
import tempfile
import unittest
from pathlib import Path


HELPER = Path(__file__).parent.parent / "helpers" / "extract-safe-tar.py"
SPEC = importlib.util.spec_from_file_location("extract_safe_tar", HELPER)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SafeTarTest(unittest.TestCase):
    @staticmethod
    def _archive(path: Path, members) -> None:
        with tarfile.open(path, "w") as handle:
            for member, content in members:
                handle.addfile(member, io.BytesIO(content) if content is not None else None)

    def test_accepts_official_umu_relative_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "umu.tar"
            folder = tarfile.TarInfo("umu")
            folder.type = tarfile.DIRTYPE
            executable = tarfile.TarInfo("umu/umu-run")
            payload = b"#!/usr/bin/env python3\n"
            executable.size = len(payload)
            link = tarfile.TarInfo("umu/umu_run.py")
            link.type = tarfile.SYMTYPE
            link.linkname = "umu-run"
            self._archive(
                archive,
                [(folder, None), (executable, payload), (link, None)],
            )

            destination = root / "output"
            MODULE.extract_safe(archive, destination)

            self.assertEqual((destination / "umu/umu_run.py").read_bytes(), payload)

    def test_rejects_symlink_outside_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "bad.tar"
            link = tarfile.TarInfo("umu/escape")
            link.type = tarfile.SYMTYPE
            link.linkname = "../../outside"
            self._archive(archive, [(link, None)])

            with self.assertRaisesRegex(ValueError, "unsafe archive member"):
                MODULE.extract_safe(archive, root / "output")

    def test_rejects_parent_path_member(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "bad.tar"
            member = tarfile.TarInfo("../outside")
            payload = b"bad"
            member.size = len(payload)
            self._archive(archive, [(member, payload)])

            with self.assertRaisesRegex(ValueError, "unsafe archive member"):
                MODULE.extract_safe(archive, root / "output")


if __name__ == "__main__":
    unittest.main()
