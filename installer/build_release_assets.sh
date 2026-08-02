#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${1:?usage: build_release_assets.sh OUTPUT_DIR WORK_DIR}"
WORK_DIR="${2:?usage: build_release_assets.sh OUTPUT_DIR WORK_DIR}"

mkdir -p "$OUTPUT_DIR" "$WORK_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"
WORK_DIR="$(cd "$WORK_DIR" && pwd)"

if [[ "$OUTPUT_DIR" == "/" || "$WORK_DIR" == "/" || "$OUTPUT_DIR" == "$PROJECT_DIR" || "$WORK_DIR" == "$PROJECT_DIR" ]]; then
    printf 'Refusing to use an unsafe release directory.\n' >&2
    exit 1
fi

rm -rf -- "$OUTPUT_DIR" "$WORK_DIR"
mkdir -p "$OUTPUT_DIR" "$WORK_DIR/zipapp" "$WORK_DIR/bundle" "$WORK_DIR/validation"

cd "$PROJECT_DIR"
./installer/build_packages.sh

cp installer/install.sh "$OUTPUT_DIR/install.sh"
if python3 -m pip --version >/dev/null 2>&1; then
    python3 -m pip install \
        --disable-pip-version-check \
        --no-compile \
        -r installer/requirements.txt \
        --target "$WORK_DIR/zipapp"
else
    mkdir -p "$WORK_DIR/zipapp"
    python3 -c "import rich, os, shutil; site = os.path.dirname(rich.__file__); shutil.copytree(site, os.path.join('$WORK_DIR/zipapp', 'rich'), dirs_exist_ok=True)"
fi
cp installer/core.py "$WORK_DIR/zipapp/__main__.py"
python3 -m zipapp "$WORK_DIR/zipapp" \
    --output "$WORK_DIR/bundle/installer.pyz" \
    --python '/usr/bin/env python3'

cp release/rdp-session-manager.deb "$WORK_DIR/bundle/"
cp release/rdp-session-manager.pkg.tar.zst "$WORK_DIR/bundle/"

(
    cd "$WORK_DIR/bundle"
    sha256sum --binary \
        installer.pyz \
        rdp-session-manager.deb \
        rdp-session-manager.pkg.tar.zst \
        > SHA256SUMS
    python3 -m zipfile -c \
        "$OUTPUT_DIR/rdp-session-manager-installer.zip" \
        installer.pyz \
        rdp-session-manager.deb \
        rdp-session-manager.pkg.tar.zst \
        SHA256SUMS
)

mapfile -t published_assets < <(
    find "$OUTPUT_DIR" -maxdepth 1 -type f -printf '%f\n' | sort
)
mapfile -t expected_assets < <(
    printf '%s\n' install.sh rdp-session-manager-installer.zip | sort
)
if [[ "${published_assets[*]}" != "${expected_assets[*]}" ]]; then
    printf 'Unexpected release assets: %s\n' "${published_assets[*]}" >&2
    exit 1
fi

for asset in "${expected_assets[@]}"; do
    if [[ ! -s "$OUTPUT_DIR/$asset" ]]; then
        printf 'Missing or empty release asset: %s\n' "$asset" >&2
        exit 1
    fi
done

python3 -m zipfile -e \
    "$OUTPUT_DIR/rdp-session-manager-installer.zip" \
    "$WORK_DIR/validation"
if [[ "$(find "$WORK_DIR/validation" -maxdepth 1 -type f | wc -l)" -ne 4 ]]; then
    printf 'The installer bundle must contain exactly four files.\n' >&2
    exit 1
fi
(cd "$WORK_DIR/validation" && sha256sum --check --strict SHA256SUMS)

RDPSM_RELEASE_ASSETS_DIR="$OUTPUT_DIR" \
    bash tests/test_installer_bootstrap.sh </dev/null

printf 'Release assets created and validated in %s\n' "$OUTPUT_DIR"
