#!/usr/bin/env python3
"""Extract a tar archive while keeping every member and link inside its root."""

import sys
import tarfile
from pathlib import Path, PurePosixPath


def extract_safe(archive: Path, destination: Path) -> None:
    destination.mkdir()
    root = destination.resolve()
    with tarfile.open(archive) as handle:
        for member in handle.getmembers():
            member_path = PurePosixPath(member.name)
            target = (destination / member_path).resolve()
            target_is_safe = target == root or root in target.parents
            supported_type = member.isfile() or member.isdir() or member.issym()
            link_is_safe = True
            if member.issym():
                link_path = PurePosixPath(member.linkname)
                resolved_link = (
                    destination / member_path.parent / link_path
                ).resolve()
                link_is_safe = (
                    not link_path.is_absolute()
                    and (resolved_link == root or root in resolved_link.parents)
                )
            if not target_is_safe or not supported_type or not link_is_safe:
                raise ValueError(f"unsafe archive member: {member.name}")
        handle.extractall(destination)


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} ARCHIVE DESTINATION", file=sys.stderr)
        return 2
    try:
        extract_safe(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, tarfile.TarError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
