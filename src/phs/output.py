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


@final
class RichOutput:
    def __init__(self, console: Console) -> None:
        self.console = console

    def text(self, message: str) -> None:
        self.console.print(message)
    def info(self, message: str) -> None:
        self.console.print(f"[bold]{message}[/bold]")
    def error(self, message: str) -> None:
        self.console.print(f"[bold][red]{message}[/red][/bold]")
    def success(self, message: str) -> None:
        self.console.print(f"[bold][green]{message}[/green][/bold]")
    def warning(self, message: str) -> None:
        self.console.print(f"[bold][orange]{message}[/orange][/bold]")
    def result(self, message: str) -> None:
        self.console.print(f"[blue]{message}[/blue]")
