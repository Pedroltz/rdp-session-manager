#!/bin/bash
# Shared EXIT trap for privileged shell helpers. Never records argv or stdin.

rdpsm_audit_finish() {
    local status="${1:-1}"
    local result="success"
    local error_code=""
    trap - EXIT
    if [ "$status" -ne 0 ]; then
        result="failure"
        error_code="exit-$status"
    fi
    if ! /usr/bin/python3 "$RDPSM_AUDIT_HELPER" write \
        --action "$RDPSM_AUDIT_ACTION" \
        --target "$RDPSM_AUDIT_TARGET" \
        --result "$result" \
        --error-code "$error_code" \
        --plan-id "${RDPSM_AUDIT_PLAN_ID:-}"; then
        echo "Warning: could not write the privileged audit event." >&2
    fi
    exit "$status"
}

rdpsm_audit_on_exit() {
    RDPSM_AUDIT_ACTION="$1"
    RDPSM_AUDIT_TARGET="${2:-system}"
    RDPSM_AUDIT_PLAN_ID="${3:-}"
    local library_dir
    library_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    RDPSM_AUDIT_HELPER="$library_dir/audit-event.py"
    export RDPSM_AUDIT_ACTION RDPSM_AUDIT_TARGET RDPSM_AUDIT_PLAN_ID RDPSM_AUDIT_HELPER
    if [ "$(id -u)" -eq 0 ]; then
        trap 'rdpsm_audit_finish $?' EXIT
    fi
}
