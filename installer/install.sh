#!/usr/bin/env bash
# RDP Session Manager release bootstrap
#
# Public installer:
#   curl -fsSL https://github.com/Pedroltz/rdp-session-manager/releases/latest/download/install.sh | bash
#
# This file deliberately stays small. It resolves the latest stable GitHub
# release, then delegates platform detection, checksums, and package-manager
# operations to the versioned Python installer.
set -Eeuo pipefail

readonly REPOSITORY="Pedroltz/rdp-session-manager"
readonly RELEASE_BASE="https://github.com/${REPOSITORY}/releases"
readonly API_BASE="https://api.github.com/repos/${REPOSITORY}"
readonly TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/rdpsm-installer.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

log() { printf '[rdp-session-manager] %s\n' "$*"; }
fail() { printf '[rdp-session-manager] ERROR: %s\n' "$*" >&2; exit 1; }

download() {
    local url="$1" destination="$2"
    if command -v curl >/dev/null 2>&1; then
        curl --fail --location --silent --show-error --retry 3 --retry-delay 2 \
            --connect-timeout 15 --max-time 300 "$url" --output "$destination"
    elif command -v wget >/dev/null 2>&1; then
        wget --tries=3 --timeout=15 --output-document="$destination" "$url"
    else
        fail "curl ou wget é necessário para baixar o instalador."
    fi
}

ensure_python() {
    command -v python3 >/dev/null 2>&1 && return 0
    for arg in "$@"; do
        if [[ "$arg" == "--dry-run" ]]; then
            fail "--dry-run precisa de Python 3 já instalado; nenhum pacote foi alterado."
        fi
    done
    log "Python 3 não encontrado; instalando somente o runtime do instalador."
    [ -r /etc/os-release ] || fail "Não foi possível detectar a distribuição para instalar Python."
    # shellcheck disable=SC1091
    . /etc/os-release
    local id_like="${ID_LIKE:-} ${ID:-}"
    if [[ "$id_like" == *debian* || "$id_like" == *ubuntu* ]]; then
        sudo apt-get update
        sudo apt-get install -y python3
    elif [[ "$id_like" == *arch* ]]; then
        sudo pacman -Syu --needed --noconfirm python
    else
        fail "Distribuição não suportada e Python 3 não está instalado."
    fi
    command -v python3 >/dev/null 2>&1 || fail "Não foi possível instalar Python 3."
}

ensure_python "$@"

release_tag=""
bootstrap_args=("$@")
for ((index = 0; index < ${#bootstrap_args[@]}; index++)); do
    arg="${bootstrap_args[index]}"
    if [[ "$arg" == --release=* ]]; then
        release_tag="${arg#--release=}"
    elif [[ "$arg" == --release && $((index + 1)) -lt ${#bootstrap_args[@]} ]]; then
        release_tag="${bootstrap_args[index + 1]}"
    fi
done

if [ -z "$release_tag" ]; then
    release_file="$TMP_DIR/release.json"
    log "Consultando a release estável mais recente..."
    download "${API_BASE}/releases/latest" "$release_file"
    release_tag="$(python3 - "$release_file" <<'PY'
import json
import sys

try:
    release = json.load(open(sys.argv[1], encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"Não foi possível interpretar a resposta da release: {exc}")

if (
    not isinstance(release, dict)
    or release.get("draft")
    or release.get("prerelease")
    or not release.get("tag_name")
):
    raise SystemExit("Nenhuma release estável foi encontrada no GitHub.")

print(release["tag_name"])
PY
)" || fail "Não foi possível determinar a release mais recente."
fi

release_url="${RELEASE_BASE}/download/${release_tag}"

log "Baixando instalador visual da release ${release_tag}..."
download "${release_url}/installer.pyz" "$TMP_DIR/installer.pyz"
download "${release_url}/SHA256SUMS" "$TMP_DIR/SHA256SUMS"

expected="$(awk '$2 == "installer.pyz" || $2 == "*installer.pyz" {print $1; exit}' "$TMP_DIR/SHA256SUMS")"
[ -n "$expected" ] || fail "SHA256SUMS não contém o checksum de installer.pyz."
actual="$(sha256sum "$TMP_DIR/installer.pyz" | awk '{print $1}')"
[ "$expected" = "$actual" ] || fail "Checksum inválido para installer.pyz."

exec python3 "$TMP_DIR/installer.pyz" "$@"
