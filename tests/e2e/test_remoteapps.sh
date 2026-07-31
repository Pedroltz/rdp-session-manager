#!/usr/bin/env bash
# End-to-end RemoteApp battery test for RDPSM.
# Tests APT binaries, Snap packages, and Flatpak packages in RemoteApp mode.

set -Eeuo pipefail

DISPLAY_NUMBER="${RDPSM_E2E_DISPLAY:-:99}"
SCREEN_SIZE="${RDPSM_E2E_SCREEN_SIZE:-1280x720}"
ARTIFACTS_DIR="${RDPSM_E2E_ARTIFACTS_DIR:-artifacts/rdp-remoteapp-e2e}"

log() {
    printf '[remoteapp-e2e] %s\n' "$*"
}

fail() {
    log "ERROR: $*"
    return 1
}

if [ "${EUID}" -ne 0 ]; then
    fail "Run this test as root: sudo $0"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RDPSM_BIN="/tmp/rdpsm"
cat > /tmp/rdpsm <<WRAPPEREOF
#!/bin/bash
export PYTHONPATH="${SCRIPT_DIR}/src:\${PYTHONPATH}"
exec python3 "${SCRIPT_DIR}/src/cli.py" "\$@"
WRAPPEREOF
chmod +x /tmp/rdpsm
export PATH="/tmp:${PATH}"

required_commands=(
    rdpsm systemctl ss Xvfb xdpyinfo import identify pgrep getent openbox
)
for command_name in "${required_commands[@]}"; do
    command -v "${command_name}" >/dev/null ||
        fail "Missing prerequisite '${command_name}'"
done

if command -v xfreerdp3 >/dev/null; then
    FREERDP_BIN="$(command -v xfreerdp3)"
elif command -v xfreerdp >/dev/null; then
    FREERDP_BIN="$(command -v xfreerdp)"
else
    fail "Missing FreeRDP X11 client (xfreerdp3 or xfreerdp)"
fi

mkdir -p "${ARTIFACTS_DIR}"
ARTIFACTS_DIR="$(readlink -f "${ARTIFACTS_DIR}")"

log "Checking xrdp service and listener..."
systemctl is-active --quiet xrdp || fail "xrdp.service is not active"
systemctl is-active --quiet xrdp-sesman || fail "xrdp-sesman.service is not active"
ss -ltn | awk '$4 ~ /:3389$/ { found=1 } END { exit !found }' ||
    fail "Nothing is listening on TCP port 3389"

test_remoteapp() {
    local app_type="$1"       # 'apt', 'snap', or 'flatpak'
    local app_cmd="$2"        # e.g., 'xfce4-terminal', '/snap/bin/firefox', 'flatpak'
    local app_args="${3:-}"   # e.g., '--help', 'run ...'

    local test_user="e2e_app_${app_type}_$$"
    local test_password="RdpE2e-${RANDOM}-Aa9!"
    local test_home="/opt/rdp-users/${test_user}"
    local marker="${test_home}/.rdpsm-e2e-ready"
    local freerdp_pid=""
    local xvfb_pid=""
    local user_created=false

    log "--------------------------------------------------------"
    log "Starting RemoteApp E2E test for [${app_type^^}]: ${app_cmd} ${app_args}"
    log "--------------------------------------------------------"

    cleanup_single() {
        set +e
        if [ -n "${freerdp_pid}" ]; then
            kill "${freerdp_pid}" 2>/dev/null || true
            wait "${freerdp_pid}" 2>/dev/null || true
        fi
        if [ -n "${xvfb_pid}" ]; then
            kill "${xvfb_pid}" 2>/dev/null || true
            wait "${xvfb_pid}" 2>/dev/null || true
        fi

        if ${user_created} && getent passwd "${test_user}" >/dev/null; then
            log "Cleaning up test user: ${test_user}"
            "${RDPSM_BIN}" user delete "${test_user}" --force >/dev/null 2>&1 || {
                pkill -KILL -u "${test_user}" 2>/dev/null || true
                userdel -r "${test_user}" 2>/dev/null || true
            }
        fi
    }
    trap cleanup_single RETURN

    # 1. Create RemoteApp user
    log "Creating RemoteApp user ${test_user}..."
    local cmd_args=(
        user create "${test_user}"
        --fullname "E2E RemoteApp ${app_type^^}"
        --password "${test_password}"
        --session-type remoteapp
        --app-command "${app_cmd}"
    )
    if [ -n "${app_args}" ]; then
        cmd_args+=("--app-args=${app_args}")
    fi
    user_created=true
    "${RDPSM_BIN}" "${cmd_args[@]}" >"${ARTIFACTS_DIR}/rdpsm-create-${app_type}.log" 2>&1

    getent passwd "${test_user}" >/dev/null || fail "Failed to create user ${test_user}"
    test -x "${test_home}/.xsession" || fail "Missing executable .xsession for ${test_user}"

    # Verify PATH injection in .xsession for Snap/Flatpak
    grep -q "/snap/bin" "${test_home}/.xsession" ||
        fail ".xsession does not include /snap/bin in PATH"
    grep -q "/var/lib/flatpak/exports/bin" "${test_home}/.xsession" ||
        fail ".xsession does not include flatpak in PATH"

    # Inject marker creation before openbox launch
    log "Injecting ready marker in ${test_user} .xsession..."
    sed -i "/exec /i touch '${marker}'" "${test_home}/.xsession"

    # 2. Launch virtual display (Xvfb)
    log "Starting virtual display on ${DISPLAY_NUMBER}..."
    Xvfb "${DISPLAY_NUMBER}" -screen 0 "${SCREEN_SIZE}x24" -ac \
        >"${ARTIFACTS_DIR}/xvfb-${app_type}.log" 2>&1 &
    xvfb_pid=$!

    for _ in $(seq 1 40); do
        if DISPLAY="${DISPLAY_NUMBER}" xdpyinfo >/dev/null 2>&1; then
            break
        fi
        sleep 0.25
    done
    DISPLAY="${DISPLAY_NUMBER}" xdpyinfo >/dev/null 2>&1 ||
        fail "Xvfb display did not initialize"

    # 3. Connect with FreeRDP
    log "Connecting to RDP RemoteApp session for ${test_user}..."
    DISPLAY="${DISPLAY_NUMBER}" "${FREERDP_BIN}" \
        /v:127.0.0.1:3389 \
        "/u:${test_user}" \
        "/p:${test_password}" \
        /cert:ignore \
        "/size:${SCREEN_SIZE}" \
        /network:lan \
        -wallpaper \
        >"${ARTIFACTS_DIR}/freerdp-${app_type}.log" 2>&1 &
    freerdp_pid=$!

    # 4. Wait for RemoteApp session initialization
    log "Waiting for RemoteApp ${app_type^^} session to initialize..."
    for _ in $(seq 1 120); do
        if [ -f "${marker}" ]; then
            break
        fi
        if ! kill -0 "${freerdp_pid}" 2>/dev/null; then
            fail "FreeRDP client exited prematurely for RemoteApp ${app_type}"
        fi
        sleep 0.5
    done

    test -f "${marker}" || fail "RemoteApp session for ${app_type} failed to execute .xsession"
    log "Marker created successfully for RemoteApp ${app_type}"

    # 5. Capture screenshot and verify GUI colors
    local screenshot="${ARTIFACTS_DIR}/rdp-remoteapp-${app_type}.png"
    local color_count=0
    for _ in $(seq 1 60); do
        DISPLAY="${DISPLAY_NUMBER}" import -window root -screen "${screenshot}" 2>/dev/null || true
        if [ -f "${screenshot}" ]; then
            color_count="$(identify -format '%k' "${screenshot}" 2>/dev/null || echo 0)"
            if [ "${color_count}" -ge 16 ]; then
                break
            fi
        fi
        sleep 0.5
    done

    if [ "${color_count}" -lt 16 ]; then
        fail "RemoteApp ${app_type} render failed (blank/black screen with ${color_count} colors)"
    fi

    log "SUCCESS: RemoteApp [${app_type^^}] loaded graphical interface correctly (${color_count} colors rendered)"
}

PASSED_APPS=()
FAILED_APPS=()

# Test APT RemoteApp
if test_remoteapp "apt" "xfce4-terminal" ""; then
    PASSED_APPS+=("apt (xfce4-terminal)")
else
    FAILED_APPS+=("apt (xfce4-terminal)")
fi

# Test Snap RemoteApp
if [ -x /snap/bin/firefox ]; then
    if test_remoteapp "snap" "snap" "run firefox"; then
        PASSED_APPS+=("snap (firefox)")
    else
        FAILED_APPS+=("snap (firefox)")
    fi
elif [ -x /snap/bin/thunderbird ]; then
    if test_remoteapp "snap" "/snap/bin/thunderbird" ""; then
        PASSED_APPS+=("snap (thunderbird)")
    else
        FAILED_APPS+=("snap (thunderbird)")
    fi
else
    log "Skipping Snap test: no installed snap app found"
fi

# Test Flatpak RemoteApp
if command -v flatpak >/dev/null; then
    if test_remoteapp "flatpak" "flatpak" "run org.gnome.Calculator"; then
        PASSED_APPS+=("flatpak (org.gnome.Calculator)")
    else
        FAILED_APPS+=("flatpak (org.gnome.Calculator)")
    fi
else
    log "Skipping Flatpak test: flatpak binary not found"
fi

log "========================================================"
log "E2E REMOTEAPP TEST SUMMARY"
log "========================================================"
log "Passed: ${#PASSED_APPS[@]} [${PASSED_APPS[*]:-none}]"
log "Failed: ${#FAILED_APPS[@]} [${FAILED_APPS[*]:-none}]"

if [ "${#FAILED_APPS[@]}" -ne 0 ]; then
    exit 1
fi
exit 0
