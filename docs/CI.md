# Continuous integration

The repository has two GitHub Actions workflows.

## Quality Checks

`Quality Checks` runs for pull requests and pushes to `main`, `master`, and
`develop`. It performs syntax checks, unit tests, bootstrap tests, a dry-run,
and builds the complete release bundle.

The built bundle is then installed, without simulation, on:

- Ubuntu 22.04
- Ubuntu 24.04
- Debian 12
- Debian 13
- Arch Linux

Ubuntu jobs run directly on GitHub-hosted virtual machines. Debian and Arch
run in clean containers on a GitHub-hosted Ubuntu runner. The default
application and xrdp installation is tested everywhere. Wine dependencies are
also installed on Ubuntu 24.04 and Arch Linux.

The verification checks package registration, installed commands, metadata,
PolicyKit and schema files, helper permissions, xrdp, and a headless GTK
startup through Xvfb. Native Ubuntu jobs additionally require the xrdp service
to be enabled, active, and listening on TCP port 3389.

## Publish Release

`Publish Release` runs for tags matching `v*.*.*`. It:

1. validates the tag against `src/version.py`;
2. runs the regular checks and builds the two release assets;
3. installs the generated bundle across the full operating-system matrix;
4. publishes the assets as a prerelease candidate;
5. repeats the full matrix through the public release `install.sh`;
6. promotes stable tags to `latest` only after every installation succeeds.

If a public installation fails, the candidate remains a prerelease and the
previous stable release remains `latest`. Reruns reuse an existing candidate
only when its asset names and contents exactly match the newly built files.

Prerelease tags, such as beta or release-candidate tags, are tested in the same
way but are not promoted to stable.

## Branch protection

To prevent merges after a failed installation, configure the jobs shown under
`Quality Checks` as required status checks for the protected branch. This
repository currently has no branch protection rule, so workflow failures are
visible but do not by themselves prevent an authorized manual merge.
