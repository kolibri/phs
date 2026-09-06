import hashlib
import json
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen

from cyclopts import Parameter

from phs.context import AppContext
from phs.output import Output


class InstallerFlashError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class BlockDevice:
    path: Path
    size: int
    model: str
    transport: str
    mountpoints: tuple[str, ...]


def _request(url: str) -> Request:
    return Request(url, headers={"User-Agent": "phs installerflash"})


def _iso_filename(iso_url: str) -> str:
    filename = Path(unquote(urlparse(iso_url).path)).name
    if not filename:
        raise InstallerFlashError(f"ISO URL has no filename: {iso_url}")

    return filename


def _expected_checksum(iso_url: str) -> str:
    filename = _iso_filename(iso_url)
    checksum_url = urljoin(iso_url, "sha256sums.txt")

    try:
        with urlopen(_request(checksum_url), timeout=30) as response:
            content = response.read(1024 * 1024 + 1)
    except (HTTPError, URLError, OSError) as error:
        raise InstallerFlashError(
            f"Could not download checksum manifest {checksum_url}: {error}"
        ) from error

    if len(content) > 1024 * 1024:
        raise InstallerFlashError(
            f"Checksum manifest is unexpectedly large: {checksum_url}"
        )

    try:
        lines = content.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise InstallerFlashError(
            f"Checksum manifest is not UTF-8 text: {checksum_url}"
        ) from error

    for line in lines:
        fields = line.split(maxsplit=1)
        if len(fields) != 2:
            continue

        checksum, manifest_filename = fields
        manifest_filename = manifest_filename.lstrip("*")
        if manifest_filename == filename:
            if len(checksum) != 64:
                break

            try:
                int(checksum, 16)
            except ValueError:
                break

            return checksum.lower()

    raise InstallerFlashError(
        f"No valid SHA-256 checksum for {filename} in {checksum_url}"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    try:
        with path.open("rb") as file:
            while chunk := file.read(1024 * 1024):
                digest.update(chunk)
    except OSError as error:
        raise InstallerFlashError(f"Could not read ISO {path}: {error}") from error

    return digest.hexdigest()


def _verify_iso(path: Path, expected_checksum: str) -> None:
    actual_checksum = _sha256(path)
    if actual_checksum != expected_checksum:
        raise InstallerFlashError(
            f"SHA-256 checksum mismatch for {path}: "
            f"expected {expected_checksum}, got {actual_checksum}"
        )


def _download_iso(
        iso_url: str,
        destination: Path,
        expected_checksum: str,
        output: Output,
) -> Path:
    partial_path = destination.with_name(f"{destination.name}.part")

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial_path.unlink(missing_ok=True)
    except OSError as error:
        raise InstallerFlashError(
            f"Could not prepare download path {destination}: {error}"
        ) from error

    output.info(f"Downloading {iso_url} to {destination}")

    try:
        with (
            urlopen(_request(iso_url), timeout=60) as response,
            partial_path.open("wb") as file,
        ):
            while chunk := response.read(1024 * 1024):
                file.write(chunk)
    except (HTTPError, URLError, OSError) as error:
        partial_path.unlink(missing_ok=True)
        raise InstallerFlashError(f"Could not download ISO {iso_url}: {error}") from error

    try:
        _verify_iso(partial_path, expected_checksum)
    except InstallerFlashError:
        partial_path.unlink(missing_ok=True)
        raise

    try:
        partial_path.replace(destination)
    except OSError as error:
        raise InstallerFlashError(
            f"Could not move verified ISO to {destination}: {error}"
        ) from error

    output.success(f"Verified SHA-256 checksum for {destination}")
    return destination


def _mountpoints(device: dict[str, object]) -> tuple[str, ...]:
    result: list[str] = []

    raw_mountpoints = device.get("mountpoints")
    if isinstance(raw_mountpoints, list):
        result.extend(
            mountpoint
            for mountpoint in raw_mountpoints
            if isinstance(mountpoint, str) and mountpoint
        )

    raw_children = device.get("children")
    if isinstance(raw_children, list):
        for child in raw_children:
            if isinstance(child, dict):
                result.extend(_mountpoints(child))

    return tuple(result)


def _available_devices() -> list[BlockDevice]:
    try:
        completed = subprocess.run(
            [
                "lsblk",
                "--json",
                "--tree",
                "--bytes",
                "--output",
                "PATH,SIZE,MODEL,TRAN,TYPE,RM,MOUNTPOINTS",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as error:
        raise InstallerFlashError(f"Could not list block devices: {error}") from error

    if completed.returncode != 0:
        message = completed.stderr.strip() or f"exit code {completed.returncode}"
        raise InstallerFlashError(f"Could not list block devices: {message}")

    try:
        raw_devices = json.loads(completed.stdout).get("blockdevices", [])
    except (AttributeError, json.JSONDecodeError) as error:
        raise InstallerFlashError("Could not parse lsblk output") from error

    devices: list[BlockDevice] = []
    for device in raw_devices:
        if not isinstance(device, dict) or device.get("type") != "disk":
            continue

        removable = device.get("rm") in (True, 1, "1")
        transport = str(device.get("tran") or "")
        if not removable and transport != "usb":
            continue

        path = device.get("path")
        if not isinstance(path, str):
            continue

        size = int(device.get("size") or 0)
        if size <= 0:
            continue

        devices.append(
            BlockDevice(
                path=Path(path),
                size=size,
                model=str(device.get("model") or "").strip(),
                transport=transport,
                mountpoints=_mountpoints(device),
            )
        )

    return devices


def _format_size(size: int) -> str:
    value = float(size)
    units = ("B", "KiB", "MiB", "GiB", "TiB")

    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024

    raise AssertionError("unreachable")


def _select_device(devices: list[BlockDevice], output: Output) -> BlockDevice:
    if not devices:
        raise InstallerFlashError(
            "No suitable unmounted removable or USB block devices found"
        )

    output.info("Available target devices:")
    for index, device in enumerate(devices, start=1):
        details = " ".join(
            value
            for value in (
                _format_size(device.size),
                device.model,
                device.transport,
            )
            if value
        )
        output.text(f"  {index}. {device.path} ({details})")

    selected_device: BlockDevice | None = None
    while selected_device is None:
        answer = output.prompt(f"Select target device [1-{len(devices)}]: ").strip()
        try:
            selection = int(answer)
        except ValueError:
            output.error("Invalid device selection.")
            continue

        if 1 <= selection <= len(devices):
            selected_device = devices[selection - 1]
            continue

        output.error("Invalid device selection.")

    return selected_device


def _target_device(
        target_dev: Path | None,
        devices: list[BlockDevice],
        output: Output,
        minimum_size: int,
) -> BlockDevice:
    if target_dev is None:
        return _select_device(
            [
                device
                for device in devices
                if not device.mountpoints and device.size >= minimum_size
            ],
            output,
        )

    requested = target_dev.expanduser().resolve()
    for device in devices:
        if device.path.resolve() == requested:
            if device.size < minimum_size:
                raise InstallerFlashError(
                    f"Target device {device.path} is smaller than the ISO"
                )
            return device

    raise InstallerFlashError(
        f"Target is not a removable or USB block device: {target_dev}"
    )


def _dd_command(iso_path: Path, target_device: Path) -> list[str]:
    return [
        "sudo",
        "dd",
        "bs=4M",
        f"if={iso_path}",
        f"of={target_device}",
        "conv=sync",
        "oflag=direct",
        "status=progress",
    ]


def installerflash(
        *,
        iso_path: Path | None = None,
        target_dev: Path | None = None,
        context: Annotated[AppContext, Parameter(parse=False)],
) -> None:
    iso_url = context.settings.installer_iso_url
    expected_checksum = _expected_checksum(iso_url)

    if iso_path is None:
        image_path = _download_iso(
            iso_url,
            Path.home() / "Downloads" / _iso_filename(iso_url),
            expected_checksum,
            context.output,
        )
    else:
        try:
            image_path = iso_path.expanduser().resolve(strict=True)
        except OSError as error:
            raise InstallerFlashError(f"Could not find ISO {iso_path}: {error}") from error

        context.output.info(f"Verifying SHA-256 checksum for {image_path}")
        _verify_iso(image_path, expected_checksum)
        context.output.success(f"Verified SHA-256 checksum for {image_path}")

    try:
        image_size = image_path.stat().st_size
    except OSError as error:
        raise InstallerFlashError(f"Could not inspect ISO {image_path}: {error}") from error

    device = _target_device(
        target_dev,
        _available_devices(),
        context.output,
        image_size,
    )
    if device.mountpoints:
        raise InstallerFlashError(
            f"Target device {device.path} is mounted at "
            f"{', '.join(device.mountpoints)}; unmount it before flashing"
        )

    command = _dd_command(image_path, device.path)
    context.output.warning(
        f"This will ERASE all data on {device.path} and write {image_path}."
    )
    context.output.result(shlex.join(command))

    answer = context.output.prompt("Type 'yes' to continue: ").strip().lower()
    if answer != "yes":
        context.output.info("Installer flash aborted.")
        return

    try:
        subprocess.run(command, check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise InstallerFlashError(f"Could not flash {device.path}: {error}") from error

    context.output.success(f"Flashed {image_path} to {device.path}.")
