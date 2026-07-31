#!/usr/bin/env bash
set -Eeuo pipefail

IMAGE="${1:?usage: run_container_installation.sh IMAGE FAMILY SOURCE TAG VERSION WITH_WINE [BUNDLE]}"
FAMILY="${2:?usage: run_container_installation.sh IMAGE FAMILY SOURCE TAG VERSION WITH_WINE [BUNDLE]}"
SOURCE="${3:?usage: run_container_installation.sh IMAGE FAMILY SOURCE TAG VERSION WITH_WINE [BUNDLE]}"
TAG="${4:?usage: run_container_installation.sh IMAGE FAMILY SOURCE TAG VERSION WITH_WINE [BUNDLE]}"
VERSION="${5:?usage: run_container_installation.sh IMAGE FAMILY SOURCE TAG VERSION WITH_WINE [BUNDLE]}"
WITH_WINE="${6:?usage: run_container_installation.sh IMAGE FAMILY SOURCE TAG VERSION WITH_WINE [BUNDLE]}"
BUNDLE="${7:-}"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_SLUG="$(printf '%s' "$IMAGE" | tr '/:' '--')"
LOG_DIR="$PROJECT_DIR/ci-logs/$LOG_SLUG"
mkdir -p "$LOG_DIR"

docker_args=(
    run
    --rm
    --volume "$PROJECT_DIR:/workspace:ro"
    --volume "$LOG_DIR:/ci-home"
    --env "RDPSM_FAMILY=$FAMILY"
    --env "RDPSM_SOURCE=$SOURCE"
    --env "RDPSM_TAG=$TAG"
    --env "RDPSM_VERSION=$VERSION"
    --env "RDPSM_WITH_WINE=$WITH_WINE"
    --env "RDPSM_REPOSITORY=${RDPSM_REPOSITORY:-Pedroltz/rdp-session-manager}"
)

if [[ -n "$BUNDLE" ]]; then
    BUNDLE_DIR="$(cd "$(dirname "$BUNDLE")" && pwd)"
    BUNDLE_NAME="$(basename "$BUNDLE")"
    docker_args+=(
        --volume "$BUNDLE_DIR:/release-assets:ro"
        --env "RDPSM_BUNDLE=/release-assets/$BUNDLE_NAME"
    )
fi

docker "${docker_args[@]}" \
    "$IMAGE" \
    bash /workspace/tests/ci/container_entrypoint.sh
