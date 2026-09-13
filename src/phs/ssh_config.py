"""Rendering and minimal edits for user-owned OpenSSH configuration."""

import re
import shlex
from collections.abc import Mapping
from pathlib import Path

from phs.inventory.config import SshHostConfig

INCLUDE = "Include ~/.ssh/config.d/*"


def render_ssh_config(hosts: Mapping[str, SshHostConfig]) -> str:
    # Preserve inventory order: overlapping Host patterns are order-sensitive.
    blocks = []
    for alias, host in hosts.items():
        lines = [f"Host {alias}"]
        for directive, value in (
            ("HostName", host.hostname),
            ("Port", host.port),
            ("User", host.user),
        ):
            if value is None:
                continue
            text = ("yes" if value else "no") if isinstance(value, bool) else str(value)
            if any(character.isspace() for character in text) or any(
                character in text for character in "#'"
            ):
                text = f'"{text}"'
            lines.append(f"    {directive} {text}")
        blocks.append("\n".join(lines))
    header = "# Managed by phs. Do not edit manually.\n"
    return header + ("\n" + "\n\n".join(blocks) + "\n" if blocks else "")


def ensure_ssh_include(content: str, home: Path) -> str:
    """Keep a global Include, or relocate only our standalone Include line.

    Mixed-path Includes can be reused globally, but cannot be moved out of a
    Host/Match block without changing the scope of unrelated user settings.
    """
    equivalents = {"~/.ssh/config.d/*", "config.d/*", str(home / ".ssh/config.d/*")}
    lines = content.splitlines(keepends=True)
    matches: list[int] = []
    scoped = False
    global_include = False
    for index, line in enumerate(lines):
        if re.match(r"^\s*(Host|Match)(?:\s|=)", line, re.IGNORECASE):
            scoped = True
        match = re.match(
            r"^\s*Include(?:\s*=\s*|\s+)(.*)$", line.rstrip("\r\n"), re.IGNORECASE
        )
        if match is None:
            continue
        try:
            paths = shlex.split(match[1], comments=True)
        except ValueError as error:
            raise ValueError(
                "Cannot safely edit malformed SSH Include directive"
            ) from error
        if not equivalents.intersection(paths):
            continue
        if len(paths) != 1:
            if scoped:
                raise ValueError(
                    "Move the config.d Include to global scope before running phs (it shares a line with other paths)"
                )
            global_include = True
            continue
        matches.append(index)
        if not scoped:
            global_include = True

    if global_include:
        return content
    newline = "\r\n" if "\r\n" in content else "\n"
    if matches:
        # Preserve spelling, comments, and whitespace on an existing directive.
        include = lines[matches[0]].rstrip("\r\n")
        remaining = "".join(
            line for index, line in enumerate(lines) if index not in matches
        )
    else:
        include = INCLUDE
        remaining = content
    return include + newline + (newline + remaining if remaining else "")
