import fnmatch
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Sequence


@dataclass(frozen=True, slots=True)
class BackupManifest:
    paths: list[Path]

    def as_text(self) -> str:
        return "".join(f"{path}\n" for path in self.paths)

    def as_rsync(self) -> str:
        return "".join(f"{path}\0" for path in self.paths)


class BackupManifestGenerator:

    @classmethod
    def generate(
            cls,
            source: Path,
            *,
            includes: Sequence[Path],
            excludes: Sequence[str] = (),
    ) -> BackupManifest:
        source = source.expanduser()

        if not source.is_dir():
            raise ValueError(
                f"Backup source is not a directory: {source}"
            )

        paths: set[Path] = set()

        for include in includes:
            relative = cls._validate_include(include)
            absolute = source / relative

            if not os.path.lexists(absolute):
                continue

            if cls._is_excluded(relative, excludes):
                continue

            if absolute.is_symlink() or not absolute.is_dir():
                cls._add_with_parents(
                    relative=relative,
                    excludes=excludes,
                    paths=paths,
                )
                continue

            cls._walk(
                source=source,
                current=absolute,
                excludes=excludes,
                paths=paths,
            )

        return BackupManifest(
            paths=sorted(
                paths,
                key=lambda path: path.as_posix(),
            )
        )

    @classmethod
    def _walk(
            cls,
            *,
            source: Path,
            current: Path,
            excludes: Sequence[str],
            paths: set[Path],
    ) -> None:
        relative = current.relative_to(source)

        if cls._is_excluded(relative, excludes):
            return

        if relative.parts:
            paths.add(relative)

        if cls._is_git_repository(current):
            cls._walk_git_repository(
                source=source,
                repository=current,
                excludes=excludes,
                paths=paths,
            )
            return

        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    absolute = Path(entry.path)
                    relative = absolute.relative_to(source)

                    if cls._is_excluded(relative, excludes):
                        continue

                    if entry.is_dir(follow_symlinks=False):
                        cls._walk(
                            source=source,
                            current=absolute,
                            excludes=excludes,
                            paths=paths,
                        )
                    else:
                        cls._add_with_parents(
                            relative=relative,
                            excludes=excludes,
                            paths=paths,
                        )

        except PermissionError as error:
            raise PermissionError(
                f"Cannot read backup directory: {current}"
            ) from error

    @classmethod
    def _walk_git_repository(
            cls,
            *,
            source: Path,
            repository: Path,
            excludes: Sequence[str],
            paths: set[Path],
    ) -> None:
        # git ls-files doesn't include .git itself.
        # For a backup, keep the repository metadata as well.
        git_directory = repository / ".git"

        if os.path.lexists(git_directory):
            cls._walk_plain(
                source=source,
                current=git_directory,
                excludes=excludes,
                paths=paths,
            )

        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repository),
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-per-directory=.gitignore",
                    "-z",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        except FileNotFoundError as error:
            raise RuntimeError(
                "Cannot generate backup manifest: git is not installed"
            ) from error

        if result.returncode != 0:
            stderr = os.fsdecode(result.stderr).strip()

            raise RuntimeError(
                f"Cannot enumerate Git repository "
                f"{repository}: {stderr}"
            )

        for raw_path in result.stdout.split(b"\0"):
            if not raw_path:
                continue

            repository_relative = Path(
                os.fsdecode(raw_path)
            )
            absolute = repository / repository_relative

            # A tracked file can still be present in the index after
            # having been deleted from the working tree.
            if not os.path.lexists(absolute):
                continue

            relative = absolute.relative_to(source)

            if cls._is_excluded(relative, excludes):
                continue

            # Mainly relevant for Git submodules.
            if (
                    not absolute.is_symlink()
                    and absolute.is_dir()
                    and cls._is_git_repository(absolute)
            ):
                cls._walk(
                    source=source,
                    current=absolute,
                    excludes=excludes,
                    paths=paths,
                )
                continue

            cls._add_with_parents(
                relative=relative,
                excludes=excludes,
                paths=paths,
            )

    @classmethod
    def _walk_plain(
            cls,
            *,
            source: Path,
            current: Path,
            excludes: Sequence[str],
            paths: set[Path],
    ) -> None:
        """
        Walk without applying Git semantics.

        Used for .git itself.
        """
        relative = current.relative_to(source)

        if cls._is_excluded(relative, excludes):
            return

        cls._add_with_parents(
            relative=relative,
            excludes=excludes,
            paths=paths,
        )

        if current.is_symlink() or not current.is_dir():
            return

        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    child = Path(entry.path)

                    if entry.is_dir(follow_symlinks=False):
                        cls._walk_plain(
                            source=source,
                            current=child,
                            excludes=excludes,
                            paths=paths,
                        )
                    else:
                        relative = child.relative_to(source)

                        cls._add_with_parents(
                            relative=relative,
                            excludes=excludes,
                            paths=paths,
                        )

        except PermissionError as error:
            raise PermissionError(
                f"Cannot read backup directory: {current}"
            ) from error

    @classmethod
    def _add_with_parents(
            cls,
            *,
            relative: Path,
            excludes: Sequence[str],
            paths: set[Path],
    ) -> None:
        candidates = [
            relative,
            *(
                parent
                for parent in relative.parents
                if parent.parts
            ),
        ]

        # If the file itself or any parent directory is excluded,
        # the object must not enter the manifest.
        if any(
                cls._is_excluded(candidate, excludes)
                for candidate in candidates
        ):
            return

        paths.update(candidates)

    @staticmethod
    def _validate_include(include: Path) -> Path:
        if include.is_absolute():
            raise ValueError(
                f"Backup include must be relative: {include}"
            )

        if ".." in include.parts:
            raise ValueError(
                f"Backup include must not contain '..': {include}"
            )

        return include

    @staticmethod
    def _is_git_repository(path: Path) -> bool:
        return os.path.lexists(path / ".git")

    @staticmethod
    def _is_excluded(
            relative: Path,
            excludes: Sequence[str],
    ) -> bool:
        if not relative.parts:
            return False

        for raw_pattern in excludes:
            pattern = raw_pattern.strip()

            if not pattern:
                continue

            pattern = pattern.removeprefix("./")
            pattern = pattern.removeprefix("/")

            if not pattern:
                continue

            if "/" in pattern:
                path = PurePosixPath(relative.as_posix())

                if path.full_match(pattern):
                    return True

                continue

            # A pattern without "/" applies to every individual path
            # component. Thus:
            #
            #   *.iso
            #
            # matches Downloads/foo.iso, and:
            #
            #   node_modules
            #
            # excludes a node_modules subtree wherever it occurs.
            if any(
                    fnmatch.fnmatchcase(part, pattern)
                    for part in relative.parts
            ):
                return True

        return False
