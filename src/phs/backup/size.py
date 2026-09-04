import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path

from phs.backup.base import BackupRsync
from phs.target.context import TargetContext


@dataclass(slots=True)
class BackupSizeNode:
    path: Path
    total: int = 0
    increment: int = 0
    children: dict[str, "BackupSizeNode"] = field(
        default_factory=dict
    )


@dataclass(frozen=True, slots=True)
class BackupSize:
    root: BackupSizeNode

    @property
    def total(self) -> int:
        return self.root.total

    @property
    def increment(self) -> int:
        return self.root.increment


class BackupSizeAccumulator:
    def __init__(self) -> None:
        self.root = BackupSizeNode(path=Path("."))

    def add_directory(self, path: Path) -> None:
        self._directory(path)

    def add_total(self, path: Path, size: int) -> None:
        self._add(path.parent, total=size)

    def add_increment(self, path: Path, size: int) -> None:
        self._add(path.parent, increment=size)

    def _add(
            self,
            directory: Path,
            *,
            total: int = 0,
            increment: int = 0,
    ) -> None:
        node = self.root
        node.total += total
        node.increment += increment

        for part in directory.parts:
            if part == ".":
                continue

            node = node.children.setdefault(
                part,
                BackupSizeNode(path=node.path / part),
            )
            node.total += total
            node.increment += increment

    def _directory(self, directory: Path) -> BackupSizeNode:
        node = self.root

        for part in directory.parts:
            if part == ".":
                continue

            node = node.children.setdefault(
                part,
                BackupSizeNode(path=node.path / part),
            )

        return node


class RsyncItemizedChangesParser:
    @staticmethod
    def parse(output: str) -> list[Path]:
        paths: list[Path] = []

        # Rsync's itemized output is line-oriented. A literal newline in its
        # output would split a filename across records; with LC_ALL=C rsync
        # normally avoids that by escaping filename bytes as \#ooo. This
        # limitation stays confined to reporting: the manifest and the actual
        # backup remain NUL-safe.
        for raw_line in output.split("\n"):
            line = raw_line.removesuffix("\r")

            if len(line) < 12 or line[11] != " ":
                continue

            itemization = line[:11]

            # With this local source-to-destination invocation, >f denotes a
            # regular file whose contents rsync will send. Metadata-only
            # changes and hard-link creations do not contribute to rsync's
            # Total transferred file size.
            if itemization[0] != ">" or itemization[1] != "f":
                continue

            paths.append(
                RsyncItemizedChangesParser._relative_path(
                    line[12:]
                )
            )

        return paths

    @staticmethod
    def _relative_path(value: str) -> Path:
        raw_path = bytearray()
        index = 0

        while index < len(value):
            escaped = value[index:index + 5]

            if (
                    len(escaped) == 5
                    and escaped.startswith("\\#")
                    and all(character in "01234567" for character in escaped[2:])
            ):
                raw_path.append(int(escaped[2:], 8))
                index += 5
                continue

            raw_path.extend(os.fsencode(value[index]))
            index += 1

        path = Path(os.fsdecode(bytes(raw_path)))

        if path.is_absolute() or ".." in path.parts:
            raise RuntimeError(
                f"rsync reported a path outside the backup source: {value}"
            )

        return path


class BackupSizeRenderer:
    @classmethod
    def render(
            cls,
            size: BackupSize,
            *,
            depth: int,
    ) -> str:
        if depth < 0:
            raise ValueError("depth must be greater than or equal to 0")

        rows = cls._rows(size.root, depth=depth)
        path_width = max(
            len("Path"),
            *(len(label) for label, _ in rows),
        )
        total_width = max(
            len("Total"),
            *(len(_format_size(node.total)) for _, node in rows),
        )
        increment_width = max(
            len("Increment"),
            *(
                len(_format_size(node.increment))
                for _, node in rows
            ),
        )

        lines = [
            f"{'Path':<{path_width}}  "
            f"{'Total':>{total_width}}  "
            f"{'Increment':>{increment_width}}"
        ]

        for label, node in rows:
            lines.append(
                f"{label:<{path_width}}  "
                f"{_format_size(node.total):>{total_width}}  "
                f"{_format_size(node.increment):>{increment_width}}"
            )

        return "\n".join(lines)

    @classmethod
    def _rows(
            cls,
            root: BackupSizeNode,
            *,
            depth: int,
    ) -> list[tuple[str, BackupSizeNode]]:
        rows = [(".", root)]

        if depth == 0:
            return rows

        cls._append_children(
            rows,
            root,
            prefix="",
            current_depth=1,
            maximum_depth=depth,
        )

        return rows

    @classmethod
    def _append_children(
            cls,
            rows: list[tuple[str, BackupSizeNode]],
            node: BackupSizeNode,
            *,
            prefix: str,
            current_depth: int,
            maximum_depth: int,
    ) -> None:
        children = sorted(
            node.children.values(),
            key=lambda item: (
                -item.total,
                item.path.as_posix(),
            ),
        )

        for index, child in enumerate(children):
            last = index == len(children) - 1
            branch = "└── " if last else "├── "
            rows.append((f"{prefix}{branch}{child.path.name}", child))

            if current_depth >= maximum_depth:
                continue

            cls._append_children(
                rows,
                child,
                prefix=f"{prefix}{'    ' if last else '│   '}",
                current_depth=current_depth + 1,
                maximum_depth=maximum_depth,
            )


def _format_size(value: int) -> str:
    amount = float(value)

    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            if unit == "B":
                return f"{int(amount)} {unit}"

            return f"{amount:.1f} {unit}"

        amount /= 1024

    raise AssertionError("unreachable")


class BackupSizeCalculator:
    @staticmethod
    def calculate(
            target: TargetContext,
            rsync: BackupRsync
    ) -> BackupSize:
        result = target.runner.run(
            rsync.command(
                dry_run=True,
                itemize_changes=True,
            ),
            root=True,
            capture_output=True,
        )

        if result.stdout is None:
            raise RuntimeError("rsync did not return size statistics")

        accumulator = BackupSizeAccumulator()

        BackupSizeCalculator._accumulate_manifest(
            accumulator,
            manifest=rsync.manifest,
            source=rsync.source,
        )
        BackupSizeCalculator._accumulate_increment(
            accumulator,
            source=rsync.source,
            output=result.stdout,
        )

        rsync_increment = BackupSizeCalculator._parse_stat(
            result.stdout,
            "Total transferred file size",
        )

        if accumulator.root.increment != rsync_increment:
            raise RuntimeError(
                "Increment breakdown does not match rsync's "
                "Total transferred file size"
            )

        return BackupSize(root=accumulator.root)

    @staticmethod
    def _accumulate_manifest(
            accumulator: BackupSizeAccumulator,
            *,
            manifest: Path,
            source: Path,
    ) -> None:
        for path in BackupSizeCalculator._manifest_paths(manifest):
            status = (source / path).stat(follow_symlinks=False)

            if stat.S_ISDIR(status.st_mode):
                accumulator.add_directory(path)
            elif stat.S_ISREG(status.st_mode):
                accumulator.add_total(path, status.st_size)

    @staticmethod
    def _accumulate_increment(
            accumulator: BackupSizeAccumulator,
            *,
            source: Path,
            output: str,
    ) -> None:
        for path in RsyncItemizedChangesParser.parse(output):
            status = (source / path).stat(follow_symlinks=False)

            if stat.S_ISREG(status.st_mode):
                accumulator.add_increment(path, status.st_size)

    @staticmethod
    def _manifest_paths(manifest: Path) -> list[Path]:
        paths: list[Path] = []

        for raw_path in manifest.read_bytes().split(b"\0"):
            if not raw_path:
                continue

            path = Path(os.fsdecode(raw_path))

            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError(
                    f"Backup manifest contains an unsafe path: {path}"
                )

            paths.append(path)

        return paths

    @staticmethod
    def _parse_stat(
            output: str,
            name: str,
    ) -> int:
        match = re.search(
            rf"^{re.escape(name)}:\s+([\d,]+)\s+bytes$",
            output,
            re.MULTILINE,
        )

        if match is None:
            raise RuntimeError(
                f"Could not find rsync statistic: {name}"
            )

        return int(match.group(1).replace(",", ""))
