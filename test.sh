#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENVIRONMENT=(uv run python "$ROOT/tests/vm/environment/manage.py")
HOSTCONFIG="$ROOT/tests/vm/hostconfig"
VM_TESTS="$ROOT/tests/vm/tests"

run_default_tests() {
    uv run ruff format --check .
    uv run ruff check .
    uv run pytest
}

run_vm_tests() (
    set -euo pipefail

    cleanup() {
        local status=$?
        "${ENVIRONMENT[@]}" stop-all || true

        echo
        if (( status == 0 )); then
            echo "VM tests passed. State retained for manual inspection."
        else
            echo "VM tests FAILED. State retained for debugging."
        fi
        echo "Use ./test.sh vm-gui or ./test.sh vm-ssh to inspect it."
        exit "$status"
    }

    trap cleanup EXIT

    run_default_tests

    "${ENVIRONMENT[@]}" prepare
    "${ENVIRONMENT[@]}" boot-fixture
    "${ENVIRONMENT[@]}" wait-fixture

    "${ENVIRONMENT[@]}" boot-sut-installer
    "${ENVIRONMENT[@]}" wait-sut-root

    uv run phs \
        --config-dir="$HOSTCONFIG" \
        install \
        --force \
        --userpassword=test \
        phs-test

    "${ENVIRONMENT[@]}" stop-sut
    "${ENVIRONMENT[@]}" boot-sut
    "${ENVIRONMENT[@]}" wait-sut-user
    "${ENVIRONMENT[@]}" configure-sut-testnet

    # Exercise the real production init path, including the GitHub clone.
    uv run phs \
        --config-dir="$HOSTCONFIG" \
        init \
        --host=phs-test \
        --loose-ssh

    # Replace the cloned working tree with exactly what is currently local.
    "${ENVIRONMENT[@]}" stage-source
    "${ENVIRONMENT[@]}" exec-sut -- \
        uv tool install --force /home/ko/projects/phs

    # From here on the guest uses the staged, unpushed source itself.
    "${ENVIRONMENT[@]}" exec-sut -- /home/ko/.local/bin/phs setup
    "${ENVIRONMENT[@]}" exec-sut -- /home/ko/.local/bin/phs setup

    uv run pytest "$VM_TESTS"

    # Persistence check.
    "${ENVIRONMENT[@]}" stop-sut
    "${ENVIRONMENT[@]}" boot-sut
    "${ENVIRONMENT[@]}" wait-sut-user
    uv run pytest "$VM_TESTS"
)

show_help() {
    cat <<'EOF'
Usage: ./test.sh [command]

Commands:
    default                 Ruff + default pytest suite (default)
    vm                      Full VM system test
    vm-gui                  Boot retained SUT with GUI and fixture services
    vm-ssh                  SSH into SUT
    vm-ssh-fixture          SSH into network fixture VM
    vm-clean                Stop VMs and remove current run state
    vm-rebuild-fixture      Rebuild cached NFS + IPP fixture base
    vm-download-archiso     Check/download current Arch ISO
    vm-download-archiso-force
                            Force full Arch ISO redownload
    vm-status               Show VM/cache status
    help                    Show this help
EOF
}

case "${1:-default}" in
    default)
        run_default_tests
        ;;
    vm)
        run_vm_tests
        ;;
    vm-gui)
        "${ENVIRONMENT[@]}" boot-fixture
        "${ENVIRONMENT[@]}" wait-fixture
        "${ENVIRONMENT[@]}" boot-sut-gui
        ;;
    vm-ssh)
        "${ENVIRONMENT[@]}" ssh-sut
        ;;
    vm-ssh-fixture)
        "${ENVIRONMENT[@]}" ssh-fixture
        ;;
    vm-clean)
        "${ENVIRONMENT[@]}" stop-all || true
        "${ENVIRONMENT[@]}" clean-state
        ;;
    vm-rebuild-fixture)
        "${ENVIRONMENT[@]}" rebuild-fixture-base
        ;;
    vm-download-archiso)
        "${ENVIRONMENT[@]}" download-archiso
        ;;
    vm-download-archiso-force)
        "${ENVIRONMENT[@]}" download-archiso --force
        ;;
    vm-status)
        "${ENVIRONMENT[@]}" status
        ;;
    help|-h|--help)
        show_help
        ;;
    *)
        show_help >&2
        echo >&2
        echo "ERROR: unknown command: $1" >&2
        exit 2
        ;;
esac
