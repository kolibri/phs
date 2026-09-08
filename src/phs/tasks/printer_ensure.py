from dataclasses import dataclass
from typing import final

from phs.target.context import TargetContext


@final
@dataclass(frozen=True, slots=True)
class PrinterEnsure:
    name: str
    uri: str
    default: bool = False

    def execute(self, target: TargetContext) -> None:
        current = target.runner.run(
            ["lpstat", "-v", self.name],
            root=True,
            capture_output=True,
            check=False,
        )

        expected = f"device for {self.name}: {self.uri}"

        if current.returncode != 0 or expected not in (current.stdout or ""):
            target.output.info(f"Configuring printer {self.name}.")

            target.runner.run(
                [
                    "lpadmin",
                    "-p",
                    self.name,
                    "-E",
                    "-v",
                    self.uri,
                    "-m",
                    "everywhere",
                ],
                root=True,
            )

        if self.default:
            current_default = target.runner.run(
                ["lpstat", "-d"],
                root=True,
                capture_output=True,
                check=False,
            )

            expected_default = f"system default destination: {self.name}"

            if expected_default not in (current_default.stdout or ""):
                target.output.info(f"Setting default printer to {self.name}.")

                target.runner.run(
                    ["lpadmin", "-d", self.name],
                    root=True,
                )
