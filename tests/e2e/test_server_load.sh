#!/usr/bin/env bash
# Staged xrdp capacity test. Creates disposable Linux RemoteApp users and
# validates 5, 10, then 25 concurrent authenticated sessions.
set -Eeuo pipefail

[[ "$EUID" -eq 0 ]] || {
    echo "Run as root: sudo $0" >&2
    exit 2
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ARTIFACTS="${RDPSM_LOAD_ARTIFACTS:-$ROOT_DIR/artifacts/server-load}"
SCREEN="${RDPSM_LOAD_SCREEN:-1024x768}"
STAGES="${RDPSM_LOAD_STAGES:-5 10 25}"
APP="${RDPSM_LOAD_APP:-xfce4-terminal}"
PASSWORD="RdpLoad-${RANDOM}-Aa9!"
RUN_ID="load_$$_${RANDOM}"
WORK_DIR="$(mktemp -d -t rdpsm-load-XXXXXX)"
XVFB_PID=""
declare -a USERS=()
declare -a CLIENT_PIDS=()

mkdir -p "$ARTIFACTS"

cleanup() {
    set +e
    for pid in "${CLIENT_PIDS[@]:-}"; do
        kill "$pid" 2>/dev/null
    done
    [[ -n "$XVFB_PID" ]] && kill "$XVFB_PID" 2>/dev/null
    for username in "${USERS[@]:-}"; do
        PYTHONPATH="$ROOT_DIR/src" python3 "$ROOT_DIR/src/cli.py" \
            user delete "$username" --force >/dev/null 2>&1 || true
    done
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

command -v "$APP" >/dev/null
command -v Xvfb >/dev/null
FREERDP="$(command -v xfreerdp3 || command -v xfreerdp)"

Xvfb :98 -screen 0 "${SCREEN}x24" -ac >"$ARTIFACTS/xvfb.log" 2>&1 &
XVFB_PID=$!
export DISPLAY=:98
for _ in $(seq 1 40); do
    xdpyinfo >/dev/null 2>&1 && break
    sleep 0.25
done
xdpyinfo >/dev/null

create_until() {
    local target="$1"
    while ((${#USERS[@]} < target)); do
        local index="${#USERS[@]}"
        local username="${RUN_ID}_${index}"
        PYTHONPATH="$ROOT_DIR/src" python3 "$ROOT_DIR/src/cli.py" user create \
            "$username" --password "$PASSWORD" --session-type remoteapp \
            --app-command "$APP" >"$ARTIFACTS/create-$username.log" 2>&1
        USERS+=("$username")
        local marker="/opt/rdp-users/$username/.rdpsm-load-ready"
        sed -i "/exec \\/usr\\/bin\\/python3/i touch '$marker'" \
            "/opt/rdp-users/$username/.xsession"
        "$FREERDP" /v:127.0.0.1:3389 "/u:$username" "/p:$PASSWORD" \
            /cert:ignore "/size:$SCREEN" /network:lan -wallpaper \
            >"$ARTIFACTS/client-$username.log" 2>&1 &
        CLIENT_PIDS+=("$!")
    done
}

for target in $STAGES; do
    create_until "$target"
    deadline=$((SECONDS + 90))
    while ((SECONDS < deadline)); do
        ready=0
        for username in "${USERS[@]}"; do
            [[ -f "/opt/rdp-users/$username/.rdpsm-load-ready" ]] && ((ready += 1))
        done
        ((ready == target)) && break
        sleep 1
    done
    ((ready == target)) || {
        echo "Only $ready/$target sessions became ready" >&2
        exit 1
    }
    memory_percent="$(free | awk '/Mem:/ {printf "%.0f", $3/$2*100}')"
    ((memory_percent < 85)) || {
        echo "Host memory reached ${memory_percent}% at $target sessions" >&2
        exit 1
    }
    PYTHONPATH="$ROOT_DIR/src" python3 "$ROOT_DIR/src/cli.py" \
        server status --format json >"$ARTIFACTS/status-$target.json"
    printf 'stage=%s ready=%s memory_percent=%s\n' \
        "$target" "$ready" "$memory_percent"
done

echo "Server load test passed for stages: $STAGES"
