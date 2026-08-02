# Server mode

RDP Session Manager can run headlessly on Ubuntu 22.04/24.04 and Debian
12/13. The production target is up to 25 concurrent, single-application RDP
sessions on a private network or VPN. Arch remains an experimental target.

## Baseline

- 16 vCPU, 64 GB RAM, and NVMe for a mixed Linux/Windows workload.
- 96 GB RAM when all 25 sessions can be Windows applications.
- cgroup v2, systemd, xrdp/xorgxrdp, Openbox, D-Bus, nftables, and TLS.

The capacity check reserves 20 percent of host memory for the operating system
and refuses an unsafe session mix.

## Provisioning workflow

```bash
# Read-only host validation
rdpsm server preflight

# Review all files and services affected
rdpsm server plan

# Check the expected mix before applying limits
rdpsm server capacity --linux 15 --windows 10

# Preview, then apply. Replace this example with the VPN/private CIDR.
sudo rdpsm server apply --dry-run --allowed-network 10.20.0.0/16
sudo rdpsm server apply --allowed-network 10.20.0.0/16

# Operational checks
rdpsm server status --format json
rdpsm server benchmark --samples 20
```

`server apply` creates timestamped backups under
`/var/backups/rdp-session-manager`, patches xrdp atomically, installs per-user
systemd slice limits, configures an isolated nftables rule for TCP/3389, and
rolls files back if xrdp cannot restart.

Defaults:

| Setting | Value |
|---|---:|
| Maximum sessions | 25 |
| Disconnected-session lifetime | 15 minutes |
| Idle-session lifetime | 60 minutes |
| Color depth | 24 bpp |
| Linux RemoteApp limit | 1.25 GB, 100% CPU, 256 tasks |
| Windows RemoteApp limit | 2.5 GB, 150% CPU, 512 tasks |

The persistent configuration is `/etc/rdp-session-manager/server.ini`.
The default capacity mix is 15 Linux plus 10 Windows slots. Smaller hosts must
set `--linux-session-slots`, `--windows-session-slots`, and `--max-sessions`
together when applying the profile.

## RemoteApp behavior

RemoteApp means a normal xrdp session containing one maximized application.
It does not claim Windows RAIL/seamless-window compatibility. The application
is launched without shell evaluation, supervised as a process group, and its
Openbox and Windows runtime processes are cleaned up when it exits.

Profiles use `.rdp_profiles.json` schema 2. Older list-based documents and
`app_command`/`app_args` fields are read and converted automatically.

## Windows runtime migration

New Windows profiles use `umu-run`. The optional installer downloads a pinned
official package and verifies its SHA-256 checksum. Existing WineGE prefixes
remain intact and usable as a legacy fallback.
The Steam/Proton runtime cache is shared at
`/opt/rdp-session-manager/runtimes/umu`, while each user's Wine prefix and
application data remain private.

```bash
# Inventory only
rdpsm server migrate

# Migrate metadata for one user after installing umu-run
sudo rdpsm server migrate --username USERNAME --apply

# Restore the backup reported by the migration
sudo rdpsm server migrate --username USERNAME \
  --rollback /opt/rdp-users/USERNAME/.rdpsm-backups/TIMESTAMP
```

Migration never deletes the Wine prefix or legacy WineGE runtime.
The migration is marked validated only after the first umu application session
exits successfully; until then the reported backup should be retained.
