from typing import Protocol, final

from rich.console import Console


class Output(Protocol):
    def info(self, message: str) -> None:
        ...
    def text(self, message: str) -> None:
        ...
    def result(self, message: str) -> None:
        ...
    def error(self, message: str) -> None:
        ...
    def success(self, message: str) -> None:
        ...
    def warning(self, message: str) -> None:
        ...
    def prompt(self, message: str) -> str:
        ...


@final
class RichOutput:
    def __init__(self, console: Console) -> None:
        self.console = console

    def text(self, message: str) -> None:
        self.console.print(message, markup=False, highlight=False)
    def info(self, message: str) -> None:
        self.console.print(f"{message}", style="bold")
    def error(self, message: str) -> None:
        self.console.print(f"{message}", style="bold red")
    def success(self, message: str) -> None:
        self.console.print(f"{message}", style="bold green")
    def warning(self, message: str) -> None:
        self.console.print(f"{message}", style="bold yellow")
    def result(self, message: str) -> None:
        self.console.print(f"{message}", style="blue")
    def prompt(self, message: str) -> str:
        return self.console.input(message, markup=False)
