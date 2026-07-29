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
readonly API_BASE="https://api.github.com/repos/${REPOSITORY}"
readonly BUNDLE_NAME="rdp-session-manager-installer.zip"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/rdpsm-installer.XXXXXX")"
readonly TMP_DIR
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

release_file="$TMP_DIR/release.json"
if [ -z "$release_tag" ]; then
    log "Consultando a release estável mais recente..."
    download "${API_BASE}/releases/latest" "$release_file"
    require_stable="true"
else
    [[ "$release_tag" == v* ]] || release_tag="v${release_tag}"
    log "Consultando a release ${release_tag}..."
    download "${API_BASE}/releases/tags/${release_tag}" "$release_file"
    require_stable="false"
fi

mapfile -t release_fields < <(python3 - "$release_file" "$BUNDLE_NAME" "$require_stable" <<'PY'
import json
import re
import sys

try:
    release = json.load(open(sys.argv[1], encoding="utf-8"))
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"Não foi possível interpretar a resposta da release: {exc}")

if (
    not isinstance(release, dict)
    or release.get("draft")
    or not release.get("tag_name")
):
    raise SystemExit("A release selecionada é inválida ou ainda não foi publicada.")
if sys.argv[3] == "true" and release.get("prerelease"):
    raise SystemExit("Nenhuma release estável foi encontrada no GitHub.")

assets = release.get("assets")
if not isinstance(assets, list):
    raise SystemExit("A release não contém uma lista válida de assets.")

print(release["tag_name"])
bundle = next(
    (asset for asset in assets if isinstance(asset, dict) and asset.get("name") == sys.argv[2]),
    None,
)
if bundle is not None:
    url = bundle.get("browser_download_url")
    digest = bundle.get("digest")
    if not isinstance(url, str) or not url:
        raise SystemExit("O bundle da release não possui uma URL válida.")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        raise SystemExit("O bundle da release não possui um digest SHA-256 válido.")
    print("bundle")
    print(url)
    print(digest.removeprefix("sha256:").lower())
else:
    by_name = {
        asset.get("name"): asset
        for asset in assets
        if isinstance(asset, dict) and isinstance(asset.get("name"), str)
    }
    missing = [name for name in ("installer.pyz", "SHA256SUMS") if name not in by_name]
    if missing:
        raise SystemExit(
            "A release não contém o bundle nem os assets legados necessários: "
            + ", ".join(missing)
        )
    urls = [by_name[name].get("browser_download_url") for name in ("installer.pyz", "SHA256SUMS")]
    if not all(isinstance(url, str) and url for url in urls):
        raise SystemExit("Os assets legados da release não possuem URLs válidas.")
    print("legacy")
    print(*urls, sep="\n")
PY
)
[ "${#release_fields[@]}" -ge 4 ] || fail "Não foi possível resolver os assets da release."

release_tag="${release_fields[0]}"
release_mode="${release_fields[1]}"
installer_args=("$@")

if [ "$release_mode" = "bundle" ]; then
    bundle_path="$TMP_DIR/$BUNDLE_NAME"
    bundle_dir="$TMP_DIR/bundle"
    log "Baixando bundle da release ${release_tag}..."
    download "${release_fields[2]}" "$bundle_path"
    actual="$(sha256sum "$bundle_path" | awk '{print $1}')"
    [ "$actual" = "${release_fields[3]}" ] || fail "Digest inválido para $BUNDLE_NAME."

    mkdir -p "$bundle_dir"
    python3 - "$bundle_path" "$bundle_dir" <<'PY' || fail "Não foi possível extrair o bundle."
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath

archive_path, destination = Path(sys.argv[1]), Path(sys.argv[2])
expected = {
    "installer.pyz",
    "rdp-session-manager.deb",
    "rdp-session-manager.pkg.tar.zst",
    "SHA256SUMS",
}
with zipfile.ZipFile(archive_path) as archive:
    members = archive.infolist()
    names = {member.filename for member in members}
    if names != expected:
        missing = sorted(expected - names)
        extra = sorted(names - expected)
        raise SystemExit(f"Conteúdo inesperado no bundle; ausentes={missing}, extras={extra}")
    for member in members:
        path = PurePosixPath(member.filename)
        mode = member.external_attr >> 16
        if path.is_absolute() or ".." in path.parts or stat.S_ISLNK(mode):
            raise SystemExit(f"Entrada insegura no bundle: {member.filename}")
    archive.extractall(destination)
PY
    (cd "$bundle_dir" && sha256sum --check --strict SHA256SUMS >/dev/null) \
        || fail "Checksum interno inválido no bundle."
    installer_path="$bundle_dir/installer.pyz"
    installer_args=(
        --bundle-dir "$bundle_dir"
        --resolved-release "$release_tag"
        "$@"
    )
else
    log "Baixando instalador visual legado da release ${release_tag}..."
    download "${release_fields[2]}" "$TMP_DIR/installer.pyz"
    download "${release_fields[3]}" "$TMP_DIR/SHA256SUMS"
    expected="$(awk '$2 == "installer.pyz" || $2 == "*installer.pyz" {print $1; exit}' "$TMP_DIR/SHA256SUMS")"
    [ -n "$expected" ] || fail "SHA256SUMS não contém o checksum de installer.pyz."
    actual="$(sha256sum "$TMP_DIR/installer.pyz" | awk '{print $1}')"
    [ "$expected" = "$actual" ] || fail "Checksum inválido para installer.pyz."
    installer_path="$TMP_DIR/installer.pyz"
fi

if [ -t 0 ]; then
    python3 "$installer_path" "${installer_args[@]}"
    exit $?
fi

# `curl ... | bash` uses stdin to deliver this script. Read interactive answers
# from the controlling terminal instead of the already-consumed pipe.
if (: </dev/tty) 2>/dev/null; then
    python3 "$installer_path" "${installer_args[@]}" </dev/tty
    exit $?
fi

for arg in "$@"; do
    if [[ "$arg" == "--yes" ]]; then
        python3 "$installer_path" "${installer_args[@]}"
        exit $?
    fi
done

fail "A instalação interativa precisa de um terminal. Execute em um terminal ou use --yes."
