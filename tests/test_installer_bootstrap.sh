#!/usr/bin/env bash
set -Eeuo pipefail

readonly PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly TEST_DIR="$(mktemp -d "${TMPDIR:-/tmp}/rdpsm-bootstrap-test.XXXXXX")"
trap 'rm -rf "$TEST_DIR"' EXIT

mkdir -p "$TEST_DIR/bin" "$TEST_DIR/assets"

cat > "$TEST_DIR/bin/curl" <<'CURL'
#!/usr/bin/env bash
set -Eeuo pipefail

url=""
destination=""
while (($#)); do
    case "$1" in
        --output)
            destination="$2"
            shift 2
            ;;
        http://*|https://*)
            url="$1"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

case "$url" in
    */releases/latest)
        source_file="$RDPSM_BOOTSTRAP_FIXTURES/release.json"
        ;;
    */installer.pyz)
        source_file="$RDPSM_BOOTSTRAP_FIXTURES/installer.pyz"
        ;;
    */SHA256SUMS)
        source_file="$RDPSM_BOOTSTRAP_FIXTURES/SHA256SUMS"
        ;;
    *)
        printf 'Unexpected bootstrap URL: %s\n' "$url" >&2
        exit 1
        ;;
esac

cp "$source_file" "$destination"
CURL
chmod +x "$TEST_DIR/bin/curl"

cat > "$TEST_DIR/assets/release.json" <<'JSON'
{"tag_name":"v0.3.3","draft":false,"prerelease":false}
JSON

cat > "$TEST_DIR/assets/installer.pyz" <<'PYTHON'
#!/usr/bin/env python3
import sys

if sys.argv[1:] != ["--dry-run", "--yes"]:
    raise SystemExit(f"unexpected installer arguments: {sys.argv[1:]}")
PYTHON

readonly INSTALLER_HASH="$(sha256sum "$TEST_DIR/assets/installer.pyz" | awk '{print $1}')"

run_success_case() {
    local filename="$1"
    printf '%s  %s\n' "$INSTALLER_HASH" "$filename" > "$TEST_DIR/assets/SHA256SUMS"
    PATH="$TEST_DIR/bin:$PATH" \
        RDPSM_BOOTSTRAP_FIXTURES="$TEST_DIR/assets" \
        bash "$PROJECT_DIR/installer/install.sh" --dry-run --yes >/dev/null
}

run_failure_case() {
    local checksum_line="$1"
    local expected_message="$2"
    local output=""
    printf '%s\n' "$checksum_line" > "$TEST_DIR/assets/SHA256SUMS"
    if output="$(
        PATH="$TEST_DIR/bin:$PATH" \
            RDPSM_BOOTSTRAP_FIXTURES="$TEST_DIR/assets" \
            bash "$PROJECT_DIR/installer/install.sh" --dry-run --yes 2>&1
    )"; then
        printf 'Expected bootstrap failure, but it succeeded.\n' >&2
        exit 1
    fi
    grep -Fq "$expected_message" <<<"$output"
}

run_success_case "installer.pyz"
run_success_case "*installer.pyz"
run_failure_case "$INSTALLER_HASH  another-file.pyz" \
    "SHA256SUMS não contém o checksum de installer.pyz."
run_failure_case "$(printf '0%.0s' {1..64}) *installer.pyz" \
    "Checksum inválido para installer.pyz."

if [ -n "${RDPSM_RELEASE_ASSETS_DIR:-}" ]; then
    cp "$RDPSM_RELEASE_ASSETS_DIR/installer.pyz" "$TEST_DIR/assets/installer.pyz"
    cp "$RDPSM_RELEASE_ASSETS_DIR/SHA256SUMS" "$TEST_DIR/assets/SHA256SUMS"
    PATH="$TEST_DIR/bin:$PATH" \
        RDPSM_BOOTSTRAP_FIXTURES="$TEST_DIR/assets" \
        bash "$PROJECT_DIR/installer/install.sh" --dry-run --yes >/dev/null
fi

printf 'Bootstrap checksum tests passed.\n'
