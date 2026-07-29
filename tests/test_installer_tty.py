#!/usr/bin/env python3
"""Exercise the piped bootstrap while answering through its controlling TTY."""

from __future__ import annotations

import errno
import os
import pty
import select
import shlex
import sys
import time


READY_MARKER = b"RDPSM_TTY_READY"
TIMEOUT_SECONDS = 15


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} INSTALLER", file=sys.stderr)
        return 2

    installer = shlex.quote(os.path.abspath(sys.argv[1]))
    child_pid, terminal_fd = pty.fork()
    if child_pid == 0:
        os.execvp("bash", ["bash", "-c", f"cat {installer} | bash"])

    output = bytearray()
    answered = False
    deadline = time.monotonic() + TIMEOUT_SECONDS
    child_status: int | None = None

    while time.monotonic() < deadline:
        readable, _, _ = select.select([terminal_fd], [], [], 0.1)
        if readable:
            try:
                chunk = os.read(terminal_fd, 4096)
            except OSError as exc:
                if exc.errno != errno.EIO:
                    raise
                chunk = b""
            if chunk:
                output.extend(chunk)
                if not answered and READY_MARKER in output:
                    os.write(terminal_fd, b"y\n")
                    answered = True

        finished_pid, status = os.waitpid(child_pid, os.WNOHANG)
        if finished_pid:
            child_status = status
            break

    if child_status is None:
        os.kill(child_pid, 15)
        _, child_status = os.waitpid(child_pid, 0)

    rendered_output = output.decode("utf-8", errors="replace")
    if not answered:
        print("Bootstrap never requested input through the terminal.", file=sys.stderr)
        print(rendered_output, file=sys.stderr)
        return 1
    if os.waitstatus_to_exitcode(child_status) != 0:
        print("Piped bootstrap failed after receiving terminal input.", file=sys.stderr)
        print(rendered_output, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
