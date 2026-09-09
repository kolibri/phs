#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

# Allow direct execution as `python tests/vm/environment/manage.py ...`.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.vm.environment.lib.environment import create_environment


def strip_separator(command: Sequence[str]) -> list[str]:
    result = list(command)
    if result and result[0] == "--":
        result.pop(0)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PHS QEMU VM test environment")
    sub = parser.add_subparsers(dest="action", required=True)

    sub.add_parser("prepare")
    download = sub.add_parser("download-archiso")
    download.add_argument("--force", action="store_true")

    sub.add_parser("build-fixture-base")
    sub.add_parser("rebuild-fixture-base")
    sub.add_parser("boot-fixture")
    sub.add_parser("boot-sut-installer")
    sub.add_parser("boot-sut")
    sub.add_parser("boot-sut-gui")
    sub.add_parser("wait-fixture")
    sub.add_parser("wait-sut-root")
    sub.add_parser("wait-sut-user")
    sub.add_parser("configure-sut-testnet")
    sub.add_parser("stage-source")

    exec_sut_parser = sub.add_parser("exec-sut")
    exec_sut_parser.add_argument("command", nargs=argparse.REMAINDER)
    exec_fixture_parser = sub.add_parser("exec-fixture")
    exec_fixture_parser.add_argument("command", nargs=argparse.REMAINDER)

    sub.add_parser("ssh-sut")
    sub.add_parser("ssh-fixture")
    sub.add_parser("stop-sut")
    sub.add_parser("stop-fixture")
    sub.add_parser("stop-all")
    sub.add_parser("clean-state")
    sub.add_parser("clean-all")
    sub.add_parser("status")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    environment = create_environment()

    match args.action:
        case "prepare":
            environment.prepare()
        case "download-archiso":
            environment.arch_iso.ensure_current(force=args.force)
        case "build-fixture-base":
            environment.build_fixture_base()
        case "rebuild-fixture-base":
            environment.rebuild_fixture_base()
        case "boot-fixture":
            environment.boot_fixture()
        case "boot-sut-installer":
            environment.boot_sut_installer()
        case "boot-sut":
            environment.boot_sut()
        case "boot-sut-gui":
            environment.boot_sut_gui()
        case "wait-fixture":
            environment.wait_fixture()
        case "wait-sut-root":
            environment.wait_sut_root()
        case "wait-sut-user":
            environment.wait_sut_user()
        case "configure-sut-testnet":
            environment.configure_sut_testnet()
        case "stage-source":
            environment.stage_source()
        case "exec-sut":
            environment.exec_sut(strip_separator(args.command))
        case "exec-fixture":
            environment.exec_fixture(strip_separator(args.command))
        case "ssh-sut":
            environment.sut.interactive_ssh()
        case "ssh-fixture":
            environment.fixture.interactive_ssh()
        case "stop-sut":
            environment.stop_sut()
        case "stop-fixture":
            environment.stop_fixture()
        case "stop-all":
            environment.stop_all()
        case "clean-state":
            environment.clean_state()
        case "clean-all":
            environment.clean_all()
        case "status":
            environment.status()
        case _:
            raise AssertionError(args.action)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        raise SystemExit(130) from None
