from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BackupManifest:
    paths: list[Path]

    def as_text(self) -> str:
        return "\n".join(self.paths)

    def as_rsync(self) -> str:
        return "".join(
            f"{path}\0"
            for path in self.paths
        )

class BackupManifestGenerator:
    @staticmethod
    def generate(
        source: Path,
    ) -> BackupManifest:
        return BackupManifest(
            paths=[
                Path("Documents/example.txt"),
                Path(".config/example/config.toml"),
                Path("projects/phs/README.md"),
            ]
        )