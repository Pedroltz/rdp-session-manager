#!/usr/bin/env bash
# End-to-end multi-desktop environment test for RDPSM.
# Tests installation, user creation, FreeRDP connection, and GUI rendering for XFCE, GNOME, and KDE.

set -Eeuo pipefail

DESKTOPS_TO_TEST=("${1:-xfce}" "${2:-gnome}" "${3:-kde}")
# Filter empty parameters if fewer than 3 were supplied
DESKTOPS=()
for de in "${DESKTOPS_TO_TEST[@]}"; do
    if [ -n "${de}" ]; then
        DESKTOPS+=("${de}")
    fi
done

DISPLAY_NUMBER="${RDPSM_E2E_DISPLAY:-:99}"
SCREEN_SIZE="${RDPSM_E2E_SCREEN_SIZE:-1280x720}"
ARTIFACTS_DIR="${RDPSM_E2E_ARTIFACTS_DIR:-artifacts/rdp-multi-e2e}"

log() {
    printf '[rdp-multi-e2e] %s\n' "$*"
}

fail() {
    log "ERROR: $*"
    return 1
}

if [ "${EUID}" -ne 0 ]; then
    fail "Run this test as root: sudo $0 [xfce] [gnome] [kde]"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
if ! command -v rdpsm >/dev/null 2>&1; then
    cat > /tmp/rdpsm <<WRAPPEREOF
#!/bin/bash
export PYTHONPATH="${SCRIPT_DIR}/src:\${PYTHONPATH}"
exec python3 "${SCRIPT_DIR}/src/cli.py" "\$@"
WRAPPEREOF
    chmod +x /tmp/rdpsm
    export PATH="/tmp:${PATH}"
fi

required_commands=(
    rdpsm systemctl ss Xvfb xdpyinfo import identify pgrep getent
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

test_single_desktop() {
    local de="$1"
    local test_user="e2e_${de}_$$"
    local test_password="RdpE2e-${RANDOM}-Aa9!"
    local test_home="/opt/rdp-users/${test_user}"
    local marker="${test_home}/.rdpsm-e2e-ready"
    local freerdp_pid=""
    local xvfb_pid=""
    local user_created=false

    log "--------------------------------------------------------"
    log "Starting E2E test for desktop environment: [${de^^}]"
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
            rdpsm user delete "${test_user}" --force >/dev/null 2>&1 || {
                pkill -KILL -u "${test_user}" 2>/dev/null || true
                userdel -r "${test_user}" 2>/dev/null || true
            }
        fi
    }
    trap cleanup_single RETURN

    # 1. Check/Install Desktop Environment if needed
    log "Checking desktop installation status for ${de}..."
    if ! rdpsm de list | grep -i "${de}" | grep -q "Installed: Yes\|sim\|True"; then
        log "Installing desktop environment ${de}..."
        rdpsm de install "${de}" || fail "Failed to install desktop environment ${de}"
    else
        log "Desktop environment ${de} is already installed."
    fi

    # 2. Create test user
    log "Creating test user ${test_user} with desktop ${de}..."
    user_created=true
    rdpsm --verbose user create "${test_user}" \
        --fullname "E2E Test ${de^^}" \
        --desktop "${de}" \
        --password "${test_password}" \
        --session-type desktop \
        >"${ARTIFACTS_DIR}/rdpsm-create-${de}.log" 2>&1

    getent passwd "${test_user}" >/dev/null || fail "Failed to create user ${test_user}"
    test -x "${test_home}/.xsession" || fail "Missing executable .xsession for ${test_user}"

    # Verify XDG environment variable injection in .xsession
    grep -q "XDG_SESSION_TYPE=x11" "${test_home}/.xsession" ||
        fail ".xsession does not set XDG_SESSION_TYPE=x11"

    # Add marker creation before session binary run
    log "Injecting ready marker in ${test_user} .xsession..."
    sed -i "/exec /i touch '${marker}'" "${test_home}/.xsession"

    # 3. Launch virtual display (Xvfb)
    log "Starting virtual display on ${DISPLAY_NUMBER}..."
    Xvfb "${DISPLAY_NUMBER}" -screen 0 "${SCREEN_SIZE}x24" -ac \
        >"${ARTIFACTS_DIR}/xvfb-${de}.log" 2>&1 &
    xvfb_pid=$!

    for _ in $(seq 1 40); do
        if DISPLAY="${DISPLAY_NUMBER}" xdpyinfo >/dev/null 2>&1; then
            break
        fi
        sleep 0.25
    done
    DISPLAY="${DISPLAY_NUMBER}" xdpyinfo >/dev/null 2>&1 ||
        fail "Xvfb display did not initialize"

    # 4. Connect with FreeRDP
    log "Connecting to RDP session for ${test_user}..."
    DISPLAY="${DISPLAY_NUMBER}" "${FREERDP_BIN}" \
        /v:127.0.0.1:3389 \
        "/u:${test_user}" \
        "/p:${test_password}" \
        /cert:ignore \
        "/size:${SCREEN_SIZE}" \
        /network:lan \
        -wallpaper \
        >"${ARTIFACTS_DIR}/freerdp-${de}.log" 2>&1 &
    freerdp_pid=$!

    # 5. Wait for session process and marker creation
    log "Waiting for ${de} desktop session to initialize..."
    local ready=false
    for _ in $(seq 1 120); do
        if [ -f "${marker}" ]; then
            ready=true
            break
        fi
        if ! kill -0 "${freerdp_pid}" 2>/dev/null; then
            fail "FreeRDP client exited prematurely for desktop ${de}"
        fi
        sleep 0.5
    done

    test -f "${marker}" || fail "RDP session for ${de} failed to execute .xsession"
    log "Marker created successfully for ${de}"

    # 6. Capture screenshot and verify GUI colors
    local screenshot="${ARTIFACTS_DIR}/rdp-desktop-${de}.png"
    local color_count=0
    for _ in $(seq 1 60); do
        DISPLAY="${DISPLAY_NUMBER}" import -window root -screen "${screenshot}" 2>/dev/null || true
        if [ -f "${screenshot}" ]; then
            color_count="$(identify -format '%k' "${screenshot}" 2>/dev/null || echo 0)"
            if [ "${color_count}" -ge 32 ]; then
                break
            fi
        fi
        sleep 0.5
    done

    if [ "${color_count}" -lt 32 ]; then
        fail "Desktop ${de} render failed (blank/black screen with ${color_count} colors)"
    fi

    log "SUCCESS: Desktop ${de^^} loaded graphical interface correctly (${color_count} colors rendered)"
}

PASSED_DESKTOPS=()
FAILED_DESKTOPS=()

for desktop_env in "${DESKTOPS[@]}"; do
    if test_single_desktop "${desktop_env}"; then
        PASSED_DESKTOPS+=("${desktop_env}")
    else
        FAILED_DESKTOPS+=("${desktop_env}")
    fi
done

log "========================================================"
log "E2E MULTI-DESKTOP TEST SUMMARY"
log "========================================================"
log "Passed: ${#PASSED_DESKTOPS[@]} [${PASSED_DESKTOPS[*]:-none}]"
log "Failed: ${#FAILED_DESKTOPS[@]} [${FAILED_DESKTOPS[*]:-none}]"

if [ "${#FAILED_DESKTOPS[@]}" -ne 0 ]; then
    exit 1
fi
exit 0
