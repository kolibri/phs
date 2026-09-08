import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import final
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from phs.target.base import TargetCommandError
from phs.target.context import TargetContext


def installed_version(target: TargetContext, package: str) -> str | None:
    result = target.runner.run(
        ["pacman", "-Q", package], capture_output=True, check=False
    )
    if result.returncode != 0:
        return None
    fields = (result.stdout or "").split()
    if len(fields) != 2 or fields[0] != package:
        raise AurError(f"Invalid pacman -Q output for package: {package}")
    return fields[1]


def compare_versions(target: TargetContext, candidate: str, installed: str) -> int:
    result = target.runner.run(["vercmp", candidate, installed], capture_output=True)
    comparison = (result.stdout or "").strip()
    if re.fullmatch(r"[+-]?[0-9]+", comparison) is None:
        raise AurError(
            f"Invalid vercmp output comparing {candidate!r} with {installed!r}"
        )
    return int(comparison)


def target_cache_root(target: TargetContext) -> Path:
    result = target.runner.run(["env", "-0"], capture_output=True)
    environment = {}
    for entry in (result.stdout or "").split("\0"):
        name, separator, value = entry.partition("=")
        if separator:
            environment[name] = value
    cache = environment.get("XDG_CACHE_HOME")
    if not cache:
        home = environment.get("HOME")
        if not home:
            raise AurError(
                "Cannot determine AUR cache directory: target HOME is missing"
            )
        cache = str(Path(home) / ".cache")
    return Path(cache) / "phs" / "aur"


@dataclass(frozen=True, slots=True)
class AurPackage:
    package_base: str
    version: str


def install_normal(target: TargetContext, metadata: AurPackage) -> None:
    result = target.runner.run(
        ["mktemp", "-d", "-t", "phs-aur.XXXXXX"], capture_output=True
    )
    temporary = Path((result.stdout or "").rstrip("\n"))
    if not temporary.is_absolute() or not temporary.name.startswith("phs-aur."):
        raise AurError(f"Invalid temporary build directory for {metadata.package_base}")
    try:
        build_dir = temporary / metadata.package_base
        target.runner.run(
            [
                "git",
                "clone",
                f"https://aur.archlinux.org/{metadata.package_base}.git",
                str(build_dir),
            ]
        )
        target.runner.run(
            ["makepkg", "--syncdeps", "--install", "--needed", "--noconfirm"],
            cwd=build_dir,
        )
    finally:
        target.runner.run(["rm", "-rf", "--", str(temporary)])


def install_vcs(
    target: TargetContext, package: str, metadata: AurPackage, installed: str | None
) -> None:
    cache_root = target_cache_root(target)
    build_dir = cache_root / metadata.package_base
    target.runner.run(["mkdir", "-p", "--", str(cache_root)])
    checkout = target.runner.run(
        ["test", "-d", str(build_dir / ".git")], capture_output=True, check=False
    )
    if checkout.returncode not in (0, 1):
        raise TargetCommandError(checkout)
    if checkout.returncode == 0:
        target.runner.run(["git", "-C", str(build_dir), "fetch", "--prune", "origin"])
        target.runner.run(
            ["git", "-C", str(build_dir), "reset", "--hard", "@{upstream}"]
        )
    else:
        target.runner.run(["rm", "-rf", "--", str(build_dir)])
        target.runner.run(
            [
                "git",
                "clone",
                f"https://aur.archlinux.org/{metadata.package_base}.git",
                str(build_dir),
            ]
        )
    target.runner.run(
        ["makepkg", "--cleanbuild", "--nobuild", "--syncdeps", "--noconfirm"],
        cwd=build_dir,
    )
    result = target.runner.run(
        ["makepkg", "--printsrcinfo"], cwd=build_dir, capture_output=True
    )
    candidate = parse_srcinfo_version(result.stdout or "", package=package)
    if installed is not None and compare_versions(target, candidate, installed) <= 0:
        target.output.info(f"{package} is up to date ({installed})")
        return
    target.runner.run(
        [
            "makepkg",
            "--noextract",
            "--syncdeps",
            "--install",
            "--needed",
            "--noconfirm",
        ],
        cwd=build_dir,
    )


def parse_rpc_response(package: str, response: object) -> AurPackage:
    invalid = f"Invalid AUR response for package: {package}"
    if not isinstance(response, dict):
        raise AurError(invalid)
    count = response.get("resultcount")
    results = response.get("results")
    if type(count) is not int or not isinstance(results, list) or count != len(results):
        raise AurError(f"{invalid} (invalid result count)")
    if count == 0:
        raise AurError(f"AUR package not found: {package}")
    if count != 1 or not isinstance(results[0], dict):
        raise AurError(f"{invalid} (expected exactly one result)")
    base = results[0].get("PackageBase")
    version = results[0].get("Version")
    # The package base becomes a checkout path and URL component; do not let a
    # malformed RPC response escape the build/cache directory.
    if (
        not isinstance(base, str)
        or re.fullmatch(r"[a-zA-Z0-9@_+][a-zA-Z0-9@._+\-]*", base) is None
    ):
        raise AurError(f"{invalid} (invalid PackageBase)")
    if not isinstance(version, str) or not version or any(c.isspace() for c in version):
        raise AurError(f"{invalid} (invalid Version)")
    return AurPackage(base, version)


def query_aur(package: str) -> AurPackage:
    url = "https://aur.archlinux.org/rpc/v5/info?" + urlencode({"arg[]": package})
    try:
        with urlopen(url, timeout=30) as response:
            data = json.load(response)
    except (URLError, OSError, ValueError) as error:
        raise AurError(f"AUR metadata lookup failed for {package}: {error}") from error
    return parse_rpc_response(package, data)


def is_vcs_package(package: str) -> bool:
    return package.endswith(
        ("-bzr", "-cvs", "-darcs", "-fossil", "-git", "-hg", "-svn")
    )


def parse_srcinfo_version(srcinfo: str, *, package: str) -> str:
    values: dict[str, str] = {}
    for line in srcinfo.splitlines():
        key, separator, value = line.strip().partition("=")
        key = key.strip()
        if separator and key in {"pkgver", "pkgrel", "epoch"}:
            values.setdefault(key, value.strip())
    for key in ("pkgver", "pkgrel"):
        if not values.get(key):
            raise AurError(
                f"Could not determine package version for {package}: missing {key}"
            )
    version = f"{values['pkgver']}-{values['pkgrel']}"
    if values.get("epoch"):
        version = f"{values['epoch']}:{version}"
    return version


class AurError(RuntimeError):
    pass


@final
@dataclass(frozen=True, slots=True)
class AurInstall:
    packages: tuple[str, ...]

    def execute(self, target: TargetContext) -> None:
        for package in self.packages:
            if target.runner.dry_run:
                target.output.info(f"Would ensure AUR package {package}")
                continue
            target.output.info(f"Ensuring aur package {package}")
            metadata = query_aur(package)
            installed = installed_version(target, package)
            if is_vcs_package(package) or is_vcs_package(metadata.package_base):
                install_vcs(target, package, metadata, installed)
            elif (
                installed is None
                or compare_versions(target, metadata.version, installed) > 0
            ):
                install_normal(target, metadata)
            else:
                target.output.info(f"{package} is up to date ({installed})")
