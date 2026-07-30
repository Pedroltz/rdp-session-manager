#!/usr/bin/env bash
# Post-installation test: create an XFCE user and open it through RDP.
# Supported on Debian/Ubuntu and Arch families.

set -Eeuo pipefail

TEST_USER="rdpsme2e$$"
TEST_PASSWORD="RdpE2e-${RANDOM}-Aa9!"
TEST_HOME="/opt/rdp-users/${TEST_USER}"
MARKER="${TEST_HOME}/.rdpsm-e2e-ready"
DISPLAY_NUMBER="${RDPSM_E2E_DISPLAY:-:99}"
SCREEN_SIZE="${RDPSM_E2E_SCREEN_SIZE:-1280x720}"
ARTIFACTS_DIR="${RDPSM_E2E_ARTIFACTS_DIR:-artifacts/rdp-e2e}"
FREERDP_PID=""
XVFB_PID=""
USER_CREATED=false

log() {
    printf '[rdp-e2e] %s\n' "$*"
}

fail() {
    log "ERROR: $*"
    return 1
}

collect_diagnostics() {
    mkdir -p "${ARTIFACTS_DIR}"
    journalctl --no-pager -u xrdp -u xrdp-sesman \
        >"${ARTIFACTS_DIR}/xrdp-journal.log" 2>&1 || true

    for server_log in /var/log/xrdp.log /var/log/xrdp-sesman.log; do
        if [ -f "${server_log}" ]; then
            cp "${server_log}" "${ARTIFACTS_DIR}/" || true
        fi
    done

    if [ -d "${TEST_HOME}" ]; then
        find "${TEST_HOME}" -maxdepth 1 -type f \
            \( -name '.xorgxrdp.*.log' -o -name '.xsession-errors*' \) \
            -exec cp {} "${ARTIFACTS_DIR}/" \; 2>/dev/null || true
    fi
}

cleanup() {
    local exit_code=$?
    trap - EXIT INT TERM
    set +e

    if [ -n "${FREERDP_PID}" ]; then
        kill "${FREERDP_PID}" 2>/dev/null || true
        wait "${FREERDP_PID}" 2>/dev/null || true
    fi
    if [ -n "${XVFB_PID}" ]; then
        kill "${XVFB_PID}" 2>/dev/null || true
        wait "${XVFB_PID}" 2>/dev/null || true
    fi

    sleep 1
    collect_diagnostics

    if ${USER_CREATED} && [[ "${TEST_USER}" == rdpsme2e* ]] &&
        getent passwd "${TEST_USER}" >/dev/null; then
        log "Removing temporary user ${TEST_USER}"
        rdpsm user delete "${TEST_USER}" --force >/dev/null 2>&1 || {
            pkill -KILL -u "${TEST_USER}" 2>/dev/null || true
            userdel -r "${TEST_USER}" 2>/dev/null || true
        }
    fi

    chmod -R a+rX "${ARTIFACTS_DIR}" 2>/dev/null || true
    exit "${exit_code}"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

if [ "${EUID}" -ne 0 ]; then
    fail "run this test as root: sudo $0"
fi

if [ ! -r /etc/os-release ]; then
    fail "/etc/os-release is unavailable"
fi
# shellcheck disable=SC1091
. /etc/os-release
distro_candidates=" ${ID:-} ${ID_LIKE:-} "
if [[ "${distro_candidates}" != *" debian "* &&
      "${distro_candidates}" != *" ubuntu "* &&
      "${distro_candidates}" != *" arch "* &&
      "${distro_candidates}" != *" manjaro "* &&
      "${distro_candidates}" != *" endeavouros "* &&
      "${distro_candidates}" != *" cachyos "* ]]; then
    fail "unsupported distribution for the RDP test: ${ID:-unknown}"
fi

required_commands=(
    rdpsm systemctl ss Xvfb xdpyinfo import identify pgrep getent
)
for command_name in "${required_commands[@]}"; do
    command -v "${command_name}" >/dev/null ||
        fail "missing prerequisite '${command_name}'; see tests/README.md"
done

if command -v xfreerdp3 >/dev/null; then
    FREERDP_BIN="$(command -v xfreerdp3)"
elif command -v xfreerdp >/dev/null; then
    FREERDP_BIN="$(command -v xfreerdp)"
else
    fail "missing FreeRDP X11 client (xfreerdp3 or xfreerdp)"
fi

mkdir -p "${ARTIFACTS_DIR}"
ARTIFACTS_DIR="$(readlink -f "${ARTIFACTS_DIR}")"

log "Checking xrdp service and listener"
systemctl is-active --quiet xrdp || fail "xrdp.service is not active"
systemctl is-active --quiet xrdp-sesman || fail "xrdp-sesman.service is not active"
ss -ltn | awk '$4 ~ /:3389$/ { found=1 } END { exit !found }' ||
    fail "nothing is listening on TCP port 3389"

log "Creating temporary XFCE user through the installed application"
USER_CREATED=true
rdpsm --verbose user create "${TEST_USER}" \
    --fullname "RDP E2E Test" \
    --desktop xfce \
    --password "${TEST_PASSWORD}" \
    --session-type desktop \
    >"${ARTIFACTS_DIR}/rdpsm-create.log" 2>&1

getent passwd "${TEST_USER}" >/dev/null || fail "rdpsm did not create the system user"
test -x "${TEST_HOME}/.xsession" || fail "rdpsm did not create an executable .xsession"
grep -q 'startxfce4' "${TEST_HOME}/.xsession" ||
    fail "the generated .xsession does not start XFCE"

log "Installing a deterministic marker in the generated .xsession"
cat >"${TEST_HOME}/.xsession" <<EOF
#!/usr/bin/env bash
export HOME='${TEST_HOME}'
export USER='${TEST_USER}'
export LOGNAME='${TEST_USER}'
touch '${MARKER}'
exec startxfce4
EOF
chmod 0755 "${TEST_HOME}/.xsession"
chown "${TEST_USER}:rdp-users" "${TEST_HOME}/.xsession"

log "Starting a virtual client display on ${DISPLAY_NUMBER}"
Xvfb "${DISPLAY_NUMBER}" -screen 0 "${SCREEN_SIZE}x24" -ac \
    >"${ARTIFACTS_DIR}/xvfb.log" 2>&1 &
XVFB_PID=$!

for _ in $(seq 1 40); do
    if DISPLAY="${DISPLAY_NUMBER}" xdpyinfo >/dev/null 2>&1; then
        break
    fi
    sleep 0.25
done
DISPLAY="${DISPLAY_NUMBER}" xdpyinfo >/dev/null 2>&1 ||
    fail "Xvfb did not become ready"

log "Connecting to localhost with FreeRDP"
DISPLAY="${DISPLAY_NUMBER}" "${FREERDP_BIN}" \
    /v:127.0.0.1:3389 \
    "/u:${TEST_USER}" \
    "/p:${TEST_PASSWORD}" \
    /cert:ignore \
    "/size:${SCREEN_SIZE}" \
    /network:lan \
    -wallpaper \
    >"${ARTIFACTS_DIR}/freerdp.log" 2>&1 &
FREERDP_PID=$!

for _ in $(seq 1 120); do
    if [ -f "${MARKER}" ] &&
        pgrep -u "${TEST_USER}" -f 'xfce4-session' >/dev/null; then
        break
    fi
    if ! kill -0 "${FREERDP_PID}" 2>/dev/null; then
        fail "FreeRDP exited before the XFCE desktop became ready"
    fi
    sleep 0.5
done

test -f "${MARKER}" ||
    fail "the RDP session did not execute the generated .xsession within 60 seconds"
pgrep -u "${TEST_USER}" -f 'xfce4-session' >/dev/null ||
    fail "no xfce4-session process is running for the RDP user"
kill -0 "${FREERDP_PID}" 2>/dev/null ||
    fail "FreeRDP disconnected after desktop startup"

sleep 2
log "Capturing and validating the rendered RDP desktop"
DISPLAY="${DISPLAY_NUMBER}" xwininfo -root -tree \
    >"${ARTIFACTS_DIR}/x-window-tree.log" 2>&1 || true
COLOR_COUNT=0
for _ in $(seq 1 60); do
    # On Xvfb, -screen includes the FreeRDP child window in the root capture.
    DISPLAY="${DISPLAY_NUMBER}" import -window root -screen \
        "${ARTIFACTS_DIR}/rdp-desktop.png"
    COLOR_COUNT="$(identify -format '%k' "${ARTIFACTS_DIR}/rdp-desktop.png")"
    if awk -v colors="${COLOR_COUNT}" 'BEGIN { exit !(colors >= 32) }'; then
        break
    fi
    sleep 0.5
done
if ! awk -v colors="${COLOR_COUNT}" 'BEGIN { exit !(colors >= 32) }'; then
    fail "the captured desktop appears blank (${COLOR_COUNT} colors)"
fi

log "PASS: authenticated RDP session opened XFCE and rendered ${COLOR_COUNT} colors"
