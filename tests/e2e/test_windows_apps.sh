#!/usr/bin/env bash
# Manual Windows RemoteApp acceptance test for Ubuntu/Debian and Arch.

set -Eeuo pipefail

FIXTURE="${RDPSM_WINDOWS_FIXTURE:-}"
RUNNER="${RDPSM_WINDOWS_RUNNER:-winege-legacy}"
DISPLAY_NUMBER="${RDPSM_E2E_DISPLAY:-:98}"
ARTIFACTS="${RDPSM_E2E_ARTIFACTS_DIR:-artifacts/windows-app-e2e}"

fail() { printf '[windows-app-e2e] ERROR: %s\n' "$*" >&2; exit 1; }
log() { printf '[windows-app-e2e] %s\n' "$*"; }

[ "${EUID}" -eq 0 ] || fail "Run as root"
[ -f "${FIXTURE}" ] || fail "Set RDPSM_WINDOWS_FIXTURE to a deterministic GUI .exe"
command -v rdpsm >/dev/null || fail "rdpsm was not found"
command -v Xvfb >/dev/null || fail "Xvfb was not found"

if command -v xfreerdp3 >/dev/null; then
    FREERDP="$(command -v xfreerdp3)"
elif command -v xfreerdp >/dev/null; then
    FREERDP="$(command -v xfreerdp)"
else
    fail "FreeRDP X11 client was not found"
fi

mkdir -p "${ARTIFACTS}"
USERNAME="e2e_win_$$"
PASSWORD="RdpWin-${RANDOM}-Aa9!"
XVFB_PID=""
RDP_PID=""

cleanup() {
    set +e
    [ -z "${RDP_PID}" ] || kill "${RDP_PID}" 2>/dev/null
    [ -z "${XVFB_PID}" ] || kill "${XVFB_PID}" 2>/dev/null
    rdpsm user delete "${USERNAME}" --force >/dev/null 2>&1
}
trap cleanup EXIT

log "Creating disposable RDP user"
rdpsm user create "${USERNAME}" --password "${PASSWORD}" \
    --session-type remoteapp --app-command xfce4-terminal

PROFILE_ID="$(
    rdpsm profile add "${USERNAME}" --name "Windows fixture" \
        --session-type remoteapp --app-command xfce4-terminal |
    sed -n 's/.*ID: \([^)]*\).*/\1/p'
)"
[ -n "${PROFILE_ID}" ] || fail "Could not determine profile ID"

log "Installing portable Windows fixture with ${RUNNER}"
rdpsm windows-app install "${USERNAME}" --profile-id "${PROFILE_ID}" \
    --source "${FIXTURE}" --name "Windows fixture" --mode portable \
    --runner "${RUNNER}" --executable-pattern "*/$(basename "${FIXTURE}")"

APP_ID="$(rdpsm windows-app status "${USERNAME}" --format json |
    python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["manifest"]["app_id"])')"
rdpsm windows-app validate "${USERNAME}" "${APP_ID}"

Xvfb "${DISPLAY_NUMBER}" -screen 0 1280x720x24 -ac \
    >"${ARTIFACTS}/xvfb.log" 2>&1 &
XVFB_PID=$!
sleep 1

log "Connecting through XRDP"
DISPLAY="${DISPLAY_NUMBER}" "${FREERDP}" /v:127.0.0.1:3389 \
    "/u:${USERNAME}" "/p:${PASSWORD}" /cert:ignore /size:1280x720 \
    >"${ARTIFACTS}/freerdp.log" 2>&1 &
RDP_PID=$!

for _ in $(seq 1 120); do
    STATE="$(rdpsm windows-app status "${USERNAME}" "${APP_ID}" --format json |
        python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["status"]["state"])')"
    [ "${STATE}" != "ready" ] || break
    kill -0 "${RDP_PID}" 2>/dev/null || fail "FreeRDP exited before validation"
    sleep 0.5
done

[ "${STATE}" = "ready" ] || fail "Application never reached ready state"
log "SUCCESS: ${APP_ID} opened through RDP"
