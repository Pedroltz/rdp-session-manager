#!/bin/bash
# Diagnose and repair one managed RDP account in a single privileged process.
# Password is read from stdin so it never appears in argv or process listings.
set -euo pipefail

USERNAME="${1:-}"
SESSION_TYPE="${2:-}"
SESSION_COMMAND="${3:-}"
PROFILES_JSON_SRC="${4:-}"
PLAN_ID="${5:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

[ "$(id -u)" -eq 0 ] || {
    echo "Error: this helper must run as root." >&2
    exit 1
}
[[ "$USERNAME" =~ ^[a-z][a-z0-9_-]{2,31}$ ]] || {
    echo "Error: invalid username." >&2
    exit 2
}
case "$SESSION_TYPE" in
    desktop|remoteapp|winege-remoteapp) ;;
    *) echo "Error: invalid session type." >&2; exit 2 ;;
esac
[ -f "$PROFILES_JSON_SRC" ] || {
    echo "Error: profile data is missing." >&2
    exit 2
}
[[ "$PLAN_ID" =~ ^[A-Za-z0-9-]{0,64}$ ]] || {
    echo "Error: invalid repair plan ID." >&2
    exit 2
}

PASSWD_ENTRY="$(getent passwd "$USERNAME" || true)"
[ -n "$PASSWD_ENTRY" ] || {
    echo "Error: user $USERNAME does not exist." >&2
    exit 3
}
HOME_DIR="$(printf '%s\n' "$PASSWD_ENTRY" | cut -d: -f6)"
[ "$HOME_DIR" = "/opt/rdp-users/$USERNAME" ] || {
    echo "Error: refusing to repair an account outside /opt/rdp-users." >&2
    exit 3
}
id -Gn "$USERNAME" | tr ' ' '\n' | grep -Fxq rdp-users || {
    echo "Error: $USERNAME is not a managed rdp-users account." >&2
    exit 3
}
if pgrep -u "$USERNAME" >/dev/null 2>&1; then
    echo "Error: $USERNAME has active processes; disconnect it before repair." >&2
    exit 4
fi

if [ "$SESSION_TYPE" = "winege-remoteapp" ]; then
    [ -f "$SESSION_COMMAND" ] || {
        echo "Error: Windows executable not found: $SESSION_COMMAND" >&2
        exit 5
    }
    if ! command -v umu-run >/dev/null 2>&1; then
        [ -x "$SCRIPT_DIR/install-umu-launcher.sh" ] || {
            echo "Error: umu installer is missing." >&2
            exit 5
        }
        echo "→ Installing the required umu-launcher runtime..."
        "$SCRIPT_DIR/install-umu-launcher.sh"
    fi
fi

IFS= read -r RDP_PASSWORD || {
    echo "Error: RDP password was not provided through stdin." >&2
    exit 2
}
[ -n "$RDP_PASSWORD" ] || {
    echo "Error: RDP password cannot be empty." >&2
    exit 2
}

BACKUP_DIR=""
audit_repair() {
    local result="$1"
    local error_code="${2:-}"
    if ! /usr/bin/python3 "$SCRIPT_DIR/audit-event.py" write \
        --action user.repair --target "$USERNAME" --result "$result" \
        --error-code "$error_code" --plan-id "$PLAN_ID"; then
        echo "Warning: could not write the privileged audit event." >&2
    fi
}
rollback_on_exit() {
    local status=$?
    trap - EXIT
    unset RDP_PASSWORD
    if [ "$status" -ne 0 ]; then
        if [ -n "$BACKUP_DIR" ]; then
            if /usr/bin/python3 "$SCRIPT_DIR/repair-transaction.py" restore \
                "$BACKUP_DIR" "$HOME_DIR" "$USERNAME"; then
                echo "Rollback: managed files restored from $BACKUP_DIR" >&2
            else
                echo "Error: automatic rollback failed; preserve $BACKUP_DIR for recovery." >&2
            fi
        fi
        audit_repair failure "exit-$status"
    fi
    exit "$status"
}
trap rollback_on_exit EXIT

BACKUP_DIR="$(/usr/bin/python3 "$SCRIPT_DIR/repair-transaction.py" backup \
    "$HOME_DIR" "$USERNAME")"
echo "→ Backup created: $BACKUP_DIR"

echo "→ Repairing managed files for $USERNAME..."
/usr/bin/chmod 751 "$HOME_DIR"
if [ "$SESSION_TYPE" = "winege-remoteapp" ]; then
    "$SCRIPT_DIR/setup-winege-app.sh" "$USERNAME" "$HOME_DIR" "$SESSION_COMMAND"
fi
"$SCRIPT_DIR/update-rdp-user-profiles.sh" \
    "$USERNAME" "$PROFILES_JSON_SRC"

printf '%s:%s\n' "$USERNAME" "$RDP_PASSWORD" | /usr/sbin/chpasswd
unset RDP_PASSWORD

PASSWORD_STATE="$(/usr/bin/passwd -S "$USERNAME" 2>/dev/null || true)"
case "$PASSWORD_STATE" in
    "$USERNAME P "*|"$USERNAME PS "*) ;;
    *)
        echo "Error: password state is not usable after repair: $PASSWORD_STATE" >&2
        exit 6
        ;;
esac

audit_repair success
trap - EXIT

echo "OK User $USERNAME repaired successfully"
echo "  - rollback snapshot: $BACKUP_DIR"
echo "  - password: configured"
echo "  - profile: validated"
echo "  - session wrapper: validated"
if [ "$SESSION_TYPE" = "winege-remoteapp" ]; then
    RUNTIME_KIND="$(/usr/bin/python3 -c \
        'import json,sys; print(json.load(open(sys.argv[1])).get("runtime", "unknown"))' \
        "$HOME_DIR/.windows_runtime.json")"
    echo "  - Windows runtime: $RUNTIME_KIND"
fi
