#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly PROJECT_DIR
TEST_DIR="$(mktemp -d "${TMPDIR:-/tmp}/rdpsm-bootstrap-test.XXXXXX")"
readonly TEST_DIR
readonly BUNDLE_NAME="rdp-session-manager-installer.zip"
trap 'rm -rf "$TEST_DIR"' EXIT

mkdir -p \
    "$TEST_DIR/bin" \
    "$TEST_DIR/assets" \
    "$TEST_DIR/bundle-source" \
    "$TEST_DIR/bootstrap-tmp"

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
    */releases/latest|*/releases/tags/*)
        source_file="$RDPSM_BOOTSTRAP_FIXTURES/release.json"
        ;;
    */rdp-session-manager-installer.zip)
        source_file="$RDPSM_BOOTSTRAP_FIXTURES/rdp-session-manager-installer.zip"
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

REAL_PYTHON3="$(command -v python3)"
readonly REAL_PYTHON3
export REAL_PYTHON3

cat > "$TEST_DIR/bin/python3" <<'PYTHON_WRAPPER'
#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${RDPSM_EXPECT_TTY:-}" == "1" && "${1:-}" == */installer.pyz ]]; then
    [ -t 0 ] || {
        printf 'installer stdin is not a terminal\n' >&2
        exit 1
    }
    printf 'RDPSM_TTY_READY\n' >&2
    IFS= read -r answer
    [ "$answer" = "y" ] || {
        printf 'unexpected interactive answer: %s\n' "$answer" >&2
        exit 1
    }
    exit 0
fi

exec "$REAL_PYTHON3" "$@"
PYTHON_WRAPPER
chmod +x "$TEST_DIR/bin/python3"

cat > "$TEST_DIR/bundle-source/installer.pyz" <<'PYTHON'
#!/usr/bin/env python3
import sys
from pathlib import Path

arguments = sys.argv[1:]
if "--bundle-dir" in arguments:
    bundle_index = arguments.index("--bundle-dir")
    bundle_dir = Path(arguments[bundle_index + 1])
    release_index = arguments.index("--resolved-release")
    if arguments[release_index + 1] != "v0.3.5":
        raise SystemExit("unexpected resolved release")
    for name in (
        "installer.pyz",
        "rdp-session-manager.deb",
        "rdp-session-manager.pkg.tar.zst",
        "SHA256SUMS",
    ):
        if not (bundle_dir / name).is_file():
            raise SystemExit(f"missing bundled file: {name}")
    public_arguments = [
        value
        for index, value in enumerate(arguments)
        if index not in {
            bundle_index,
            bundle_index + 1,
            release_index,
            release_index + 1,
        }
    ]
    if public_arguments != ["--dry-run", "--yes"]:
        raise SystemExit(f"unexpected bundle arguments: {public_arguments}")
else:
    if arguments != ["--release", "v0.3.4", "--dry-run", "--yes"]:
        raise SystemExit(f"unexpected legacy arguments: {arguments}")
PYTHON
printf 'fake deb package\n' > "$TEST_DIR/bundle-source/rdp-session-manager.deb"
printf 'fake arch package\n' > "$TEST_DIR/bundle-source/rdp-session-manager.pkg.tar.zst"
(
    cd "$TEST_DIR/bundle-source"
    sha256sum --binary \
        installer.pyz \
        rdp-session-manager.deb \
        rdp-session-manager.pkg.tar.zst \
        > SHA256SUMS
    "$REAL_PYTHON3" -m zipfile -c \
        "$TEST_DIR/assets/$BUNDLE_NAME" \
        installer.pyz \
        rdp-session-manager.deb \
        rdp-session-manager.pkg.tar.zst \
        SHA256SUMS
)
cp "$TEST_DIR/assets/$BUNDLE_NAME" "$TEST_DIR/assets/valid-bundle.zip"
cp "$TEST_DIR/bundle-source/installer.pyz" "$TEST_DIR/assets/installer.pyz"
cp "$TEST_DIR/bundle-source/SHA256SUMS" "$TEST_DIR/assets/SHA256SUMS"

bundle_digest() {
    sha256sum "$TEST_DIR/assets/$BUNDLE_NAME" | awk '{print $1}'
}

write_bundle_release() {
    local digest="${1:-$(bundle_digest)}"
    printf '%s\n' \
        "{\"tag_name\":\"v0.3.5\",\"draft\":false,\"prerelease\":false,\"assets\":[{\"name\":\"$BUNDLE_NAME\",\"browser_download_url\":\"https://example.test/$BUNDLE_NAME\",\"digest\":\"sha256:$digest\"}]}" \
        > "$TEST_DIR/assets/release.json"
}

write_legacy_release() {
    printf '%s\n' \
        '{"tag_name":"v0.3.4","draft":false,"prerelease":false,"assets":[{"name":"installer.pyz","browser_download_url":"https://example.test/installer.pyz"},{"name":"SHA256SUMS","browser_download_url":"https://example.test/SHA256SUMS"}]}' \
        > "$TEST_DIR/assets/release.json"
}

run_bootstrap() {
    PATH="$TEST_DIR/bin:$PATH" \
        TMPDIR="$TEST_DIR/bootstrap-tmp" \
        RDPSM_BOOTSTRAP_FIXTURES="$TEST_DIR/assets" \
        bash "$PROJECT_DIR/installer/install.sh" "$@"
}

expect_failure() {
    local expected_message="$1"
    shift
    local output=""
    if output="$(run_bootstrap "$@" 2>&1)"; then
        printf 'Expected bootstrap failure, but it succeeded.\n' >&2
        exit 1
    fi
    grep -Fq "$expected_message" <<<"$output" || {
        printf 'Expected error not found: %s\n%s\n' "$expected_message" "$output" >&2
        exit 1
    }
}

write_bundle_release
run_bootstrap --dry-run --yes >/dev/null
test -z "$(find "$TEST_DIR/bootstrap-tmp" -mindepth 1 -maxdepth 1 -print -quit)"

cp "$TEST_DIR/assets/valid-bundle.zip" "$TEST_DIR/assets/$BUNDLE_NAME"
"$REAL_PYTHON3" - "$TEST_DIR/assets/$BUNDLE_NAME" <<'PY'
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1], "a") as archive:
    archive.writestr("../unexpected", "unsafe")
PY
write_bundle_release
expect_failure "Unable to extract bundle." --dry-run --yes
cp "$TEST_DIR/assets/valid-bundle.zip" "$TEST_DIR/assets/$BUNDLE_NAME"

write_bundle_release "$(printf '0%.0s' {1..64})"
expect_failure "Invalid digest for $BUNDLE_NAME." --dry-run --yes

printf '%s\n' \
    "{\"tag_name\":\"v0.3.5\",\"draft\":false,\"prerelease\":false,\"assets\":[{\"name\":\"$BUNDLE_NAME\",\"browser_download_url\":\"https://example.test/$BUNDLE_NAME\"}]}" \
    > "$TEST_DIR/assets/release.json"
expect_failure "does not have a valid SHA-256 digest" --dry-run --yes

printf '%s\n' \
    '{"tag_name":"v0.3.5","draft":false,"prerelease":false,"assets":[]}' \
    > "$TEST_DIR/assets/release.json"
expect_failure "does not contain the bundle or required legacy assets" --dry-run --yes

write_legacy_release
run_bootstrap --release v0.3.4 --dry-run --yes >/dev/null

legacy_hash="$(sha256sum "$TEST_DIR/assets/installer.pyz" | awk '{print $1}')"
printf '%s  another-file.pyz\n' "$legacy_hash" > "$TEST_DIR/assets/SHA256SUMS"
expect_failure "SHA256SUMS does not contain the checksum of installer.pyz." \
    --release v0.3.4 --dry-run --yes
printf '%s *installer.pyz\n' "$(printf '0%.0s' {1..64})" > "$TEST_DIR/assets/SHA256SUMS"
expect_failure "Invalid checksum for installer.pyz." \
    --release v0.3.4 --dry-run --yes

write_bundle_release
PATH="$TEST_DIR/bin:$PATH" \
    RDPSM_BOOTSTRAP_FIXTURES="$TEST_DIR/assets" \
    RDPSM_EXPECT_TTY=1 \
    python3 "$PROJECT_DIR/tests/test_installer_tty.py" \
        "$PROJECT_DIR/installer/install.sh"

noninteractive_output=""
if noninteractive_output="$(
    PATH="$TEST_DIR/bin:$PATH" \
        RDPSM_BOOTSTRAP_FIXTURES="$TEST_DIR/assets" \
        bash -c "cat '$PROJECT_DIR/installer/install.sh' | bash" 2>&1
)"; then
    printf 'Expected piped bootstrap without a terminal to fail.\n' >&2
    exit 1
fi
grep -Fq "Interactive installation requires a terminal." \
    <<<"$noninteractive_output"

if [ -n "${RDPSM_RELEASE_ASSETS_DIR:-}" ]; then
    cp "$RDPSM_RELEASE_ASSETS_DIR/$BUNDLE_NAME" "$TEST_DIR/assets/$BUNDLE_NAME"
    write_bundle_release
    run_bootstrap --dry-run --yes >/dev/null
fi

printf 'Bootstrap bundle and compatibility tests passed.\n'
