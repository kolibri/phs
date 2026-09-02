from difflib import unified_diff
from pathlib import Path
from typing import ClassVar, final

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from phs.output import Output
from phs.target.filesystem import Filesystem
from phs.target.runner import Runner


class WatchedFile(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    content: str
    root: bool = False


class WatchCacheData(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")
    files: dict[str, WatchedFile] = Field(default_factory=dict)


@final
class WatchCache:
    def __init__(
            self,
            path: Path,
            filesystem: Filesystem,
            runner: Runner,
            output: Output,
    ) -> None:
        self.path = path
        self.filesystem = filesystem
        self.runner = runner
        self.output = output
        self._data: WatchCacheData | None = None
        self._seen: set[str] = set()
        self._refresh = False
        self._dirty = False
        self._force = False

    def _load(self) -> WatchCacheData:
        if self._data is not None:
            return self._data

        if not self.filesystem.exists(self.path):
            self._data = WatchCacheData()
            return self._data

        content = self.filesystem.read_text(self.path)

        try:
            self._data = WatchCacheData.model_validate_json(content)
        except ValidationError as error:
            raise RuntimeError(f"Invalid watch cache: {self.path}") from error

        return self._data

    @property
    def force(self) -> bool:
        return self._force

    def set_force(self, force: bool) -> None:
        self._force = force

    def begin_refresh(self) -> None:
        self._load()
        self._seen.clear()
        self._refresh = True

    def get(self, path: Path) -> WatchedFile | None:
        return self._load().files.get(str(path))

    def preserve(self, path: Path) -> None:
        self._load()
        self._seen.add(str(path))

    def record(
            self,
            path: Path,
            content: str,
            *,
            root: bool,
    ) -> None:
        data = self._load()
        key = str(path)
        watched_file = WatchedFile(
            content=content,
            root=root,
        )

        self._seen.add(key)

        if data.files.get(key) == watched_file:
            return

        data.files[key] = watched_file
        self._dirty = True

    def show_diff(
            self,
            path: Path,
            before: str,
            after: str,
            *,
            before_name: str,
            after_name: str,
    ) -> None:
        diff = "".join(unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"{before_name}:{path}",
            tofile=f"{after_name}:{path}",
        ))

        if diff:
            self.output.text(diff.rstrip())

    def show_changes(self) -> bool:
        data = self._load()
        changed = False

        for path_text, watched_file in sorted(data.files.items()):
            path = Path(path_text)
            actual = (
                self.filesystem.read_text(path, root=watched_file.root)
                if self.filesystem.exists(path, root=watched_file.root)
                else ""
            )

            if actual == watched_file.content:
                continue

            changed = True
            self.output.warning(f"Watched file changed: {path}")
            self.show_diff(
                path,
                watched_file.content,
                actual,
                before_name="cached",
                after_name="actual",
            )

        return changed

    def save(self, *, success: bool) -> None:
        data = self._load()

        if success and self._refresh:
            refreshed_files = {
                key: data.files[key]
                for key in sorted(self._seen)
                if key in data.files
            }

            if refreshed_files != data.files:
                data.files = refreshed_files
                self._dirty = True

        if not self._dirty:
            self._refresh = False
            self._seen.clear()
            return

        content = data.model_dump_json(indent=2) + "\n"
        temporary_path = self.path.with_name(f"{self.path.name}.tmp")

        self.filesystem.write_text(temporary_path, content)
        self.runner.run([
            "mv",
            "--",
            str(temporary_path),
            str(self.path),
        ])
        self.runner.run([
            "chmod",
            "600",
            str(self.path),
        ])

        self._dirty = False
        self._refresh = False
        self._seen.clear()
