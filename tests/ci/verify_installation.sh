#!/usr/bin/env bash
set -Eeuo pipefail

EXPECTED_VERSION="${1:?usage: verify_installation.sh VERSION FAMILY WITH_WINE REQUIRE_SERVICE}"
DISTRO_FAMILY="${2:?usage: verify_installation.sh VERSION FAMILY WITH_WINE REQUIRE_SERVICE}"
WITH_WINE="${3:?usage: verify_installation.sh VERSION FAMILY WITH_WINE REQUIRE_SERVICE}"
REQUIRE_SERVICE="${4:?usage: verify_installation.sh VERSION FAMILY WITH_WINE REQUIRE_SERVICE}"

fail() {
    printf 'Installation verification failed: %s\n' "$*" >&2
    exit 1
}

assert_file() {
    [[ -f "$1" ]] || fail "missing file: $1"
}

assert_command() {
    command -v "$1" >/dev/null 2>&1 || fail "missing command: $1"
}

assert_command rdp-session-manager
assert_command rdpsm
assert_command xrdp

case "$DISTRO_FAMILY" in
    debian)
        package_version="$(dpkg-query -W -f='${Version}' rdp-session-manager)"
        dpkg-query -W xrdp xorgxrdp >/dev/null
        ;;
    arch)
        package_version="$(pacman -Q rdp-session-manager | awk '{print $2}')"
        pacman -Q xrdp xorgxrdp >/dev/null
        ;;
    *)
        fail "unsupported verification family: $DISTRO_FAMILY"
        ;;
esac

if [[ "$package_version" != *"$EXPECTED_VERSION"* ]]; then
    fail "installed version $package_version does not contain $EXPECTED_VERSION"
fi

rdpsm --version | grep -F "$EXPECTED_VERSION" >/dev/null
desktop_json="$(rdpsm de list --format json)"
python3 -c '
import json
import sys

items = json.loads(sys.stdin.read())
actual = {item["id"] for item in items}
expected = {"xfce", "gnome", "kde"}
if actual != expected:
    raise SystemExit(f"unexpected desktop IDs: {sorted(actual)}")
' <<<"$desktop_json"

for removed_desktop in mate cinnamon lxde lxqt plasma xfce4; do
    if rdpsm de install "$removed_desktop" >/dev/null 2>&1; then
        fail "removed desktop was accepted: $removed_desktop"
    fi
done

if [[ "$EUID" -eq 0 ]]; then
    python3 -m compileall -q /usr/share/rdp-session-manager/src
else
    sudo python3 -m compileall -q /usr/share/rdp-session-manager/src
fi

assert_file /usr/share/applications/com.rdp.SessionManager.desktop
assert_file /usr/share/metainfo/com.rdp.SessionManager.appdata.xml
assert_file /usr/share/polkit-1/actions/com.rdp.SessionManager.policy
assert_file /usr/share/glib-2.0/schemas/com.rdp.SessionManager.gschema.xml
assert_file /usr/share/glib-2.0/schemas/gschemas.compiled
assert_file /usr/share/rdp-session-manager/helpers/create-rdp-user.sh
[[ -x /usr/share/rdp-session-manager/helpers/create-rdp-user.sh ]] \
    || fail "create-rdp-user.sh is not executable"

python3 - <<'PY'
import xml.etree.ElementTree as ET

ET.parse("/usr/share/metainfo/com.rdp.SessionManager.appdata.xml")
ET.parse("/usr/share/polkit-1/actions/com.rdp.SessionManager.policy")
ET.parse("/usr/share/glib-2.0/schemas/com.rdp.SessionManager.gschema.xml")
PY

if ! find /usr/lib/systemd/system /lib/systemd/system \
    -maxdepth 1 -name 'xrdp.service' -print -quit 2>/dev/null | grep -q .; then
    fail "xrdp.service unit file was not installed"
fi
xrdp --version >/dev/null 2>&1

if [[ "$WITH_WINE" == "true" ]]; then
    assert_command wine
    assert_command winetricks
    wine --version
    winetricks --version
    if [[ "$DISTRO_FAMILY" == "debian" ]]; then
        dpkg-query -W wine wine64 winetricks >/dev/null
        dpkg-query -W 'wine32:*' >/dev/null
    else
        pacman -Q wine winetricks lib32-gnutls >/dev/null
    fi
fi

GUI_LOG="${HOME}/rdp-session-manager-gui.log"
set +e
timeout 15s dbus-run-session -- \
    xvfb-run -a -s '-screen 0 1280x720x24' \
    rdp-session-manager >"$GUI_LOG" 2>&1
gui_status=$?
set -e
if [[ "$gui_status" -ne 0 && "$gui_status" -ne 124 ]]; then
    sed -n '1,240p' "$GUI_LOG" >&2
    fail "graphical application exited with status $gui_status"
fi
if grep -Eiq 'Traceback|ModuleNotFoundError|ImportError|segmentation fault' "$GUI_LOG"; then
    sed -n '1,240p' "$GUI_LOG" >&2
    fail "graphical application reported a startup error"
fi

if [[ "$REQUIRE_SERVICE" == "true" ]]; then
    sudo systemctl is-enabled --quiet xrdp
    sudo systemctl is-active --quiet xrdp
    if ! ss -ltn | awk '{print $4}' | grep -Eq '(^|:|\])3389$'; then
        sudo systemctl status xrdp --no-pager >&2 || true
        fail "xrdp is not listening on TCP port 3389"
    fi
fi

printf 'Installation verification passed for %s %s\n' "$DISTRO_FAMILY" "$EXPECTED_VERSION"
