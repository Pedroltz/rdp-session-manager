#!/usr/bin/env bash
# Exercise privileged audit events through real user administration helpers.
set -Eeuo pipefail

[[ "$EUID" -eq 0 ]] || { echo "Run as root" >&2; exit 2; }
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARTIFACTS="${RDPSM_E2E_ARTIFACTS_DIR:-$ROOT_DIR/artifacts/audit-e2e}"
USERNAME="audit_$$_${RANDOM}"
PASSWORD="Audit-${RANDOM}-Aa9!"
CREATED=false

mkdir -p "$ARTIFACTS"
cleanup() {
    set +e
    if $CREATED; then
        PYTHONPATH="$ROOT_DIR/src" python3 "$ROOT_DIR/src/cli.py" \
            user delete "$USERNAME" --force >/dev/null 2>&1
    fi
}
trap cleanup EXIT

rdpsm_cmd=(env PYTHONPATH="$ROOT_DIR/src" python3 "$ROOT_DIR/src/cli.py")
"${rdpsm_cmd[@]}" user create "$USERNAME" --password "$PASSWORD" \
    --session-type remoteapp --app-command xfce4-terminal
CREATED=true
"${rdpsm_cmd[@]}" user disable "$USERNAME"
"${rdpsm_cmd[@]}" user enable "$USERNAME"
"${rdpsm_cmd[@]}" user delete "$USERNAME" --force
CREATED=false
"${rdpsm_cmd[@]}" audit export --output "$ARTIFACTS/audit.jsonl" \
    --user "$USERNAME" --limit 1000

python3 - "$ARTIFACTS/audit.jsonl" "$PASSWORD" <<'PY'
import json
import stat
import sys
from pathlib import Path

path = Path(sys.argv[1])
secret = sys.argv[2]
raw = path.read_text(encoding="utf-8")
if secret in raw:
    raise SystemExit("password leaked into audit export")
events = [json.loads(line) for line in raw.splitlines()]
actions = {event["action"] for event in events}
required = {"user.create", "user.lock", "user.unlock", "user.delete"}
if not required.issubset(actions):
    raise SystemExit(f"missing audit actions: {sorted(required - actions)}")
successful = {
    event["action"] for event in events if event.get("result") == "success"
}
if not required.issubset(successful):
    raise SystemExit(f"actions without a success event: {sorted(required - successful)}")
if stat.S_IMODE(path.stat().st_mode) != 0o600:
    raise SystemExit("audit export is not private")
PY

echo "Privileged audit E2E passed"
