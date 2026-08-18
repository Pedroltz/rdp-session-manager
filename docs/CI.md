# Continuous integration

The repository has three GitHub Actions workflows.

## Quality Checks

`Quality Checks` runs for every pull request and for pushes to `master`, `main`,
and `develop`. The independent gates are:

- syntax compilation on Python 3.9 and 3.13;
- Python compilation, shell syntax, XML/recipe parsing, the complete unittest
  suite, and installer bootstrap tests;
- real Debian and Arch package builds, followed by archive inspection for the
  privileged audit helpers and logrotate policy.

The generated packages are retained for seven days as workflow artifacts. Add
both jobs as required status checks in the repository branch-protection rule.

## Privileged RDP E2E

`Privileged RDP E2E` runs every Monday at 03:30 UTC and can also be started
manually. It requires a dedicated runner labeled `self-hosted`, `linux`, and
`rdpsm-e2e`, with xrdp, Xvfb, FreeRDP, the supported desktops, and Windows
runtime dependencies already installed.

Suites run serially because they share system users, xrdp, display numbers, and
host capacity:

1. desktop connection smoke test;
2. Linux RemoteApp battery;
3. privileged audit create/lock/unlock/delete round trip;
4. staged 5/10/25-session capacity test;
5. Windows application connection test.

The runner must provide a deterministic Windows GUI executable at
`/opt/rdpsm-fixtures/windows-test.exe`, or a different absolute path through the
manual workflow input. Diagnostics are uploaded even when a suite fails.

## Publish Release

`Publish Release` runs for tags matching `v*.*.*`. Before building or publishing
it verifies the tag against `src/version.py` and repeats compilation, shell,
unit, and bootstrap gates. It then builds the checksummed installer assets and
publishes the release.

The privileged E2E workflow is intentionally separate: GitHub-hosted runners do
not provide a persistent systemd/xrdp host or a Windows fixture. A release should
only be tagged after the latest scheduled or manually triggered E2E run passes.
