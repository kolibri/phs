from collections.abc import Callable, Hashable
from functools import partial
from operator import itemgetter
from typing import Any

from phs.inventory.host import AllHostDataFragment, HostDataFragment


def merge_unique[T: Hashable](base: list[T], override: list[T]) -> list[T]:
    return list(dict.fromkeys(base + override))


def merge_mapping[K, V](base: dict[K, V], override: dict[K, V]) -> dict[K, V]:
    return {**base, **override}


def merge_by[T, K: Hashable](
    base: list[T], override: list[T], *, key: Callable[[T], K]
) -> list[T]:
    """Replace whole entries, retaining the first occurrence's position."""
    return list({key(item): item for item in base + override}.values())


def inherit_empty(base: str, override: str) -> str:
    # Preserve the legacy scalar behavior: empty strings inherit defaults.
    return override or base


# Unlisted fields use host replacement when provided, inheritance otherwise.
# Collection policies also run for omitted host fields to deduplicate defaults.
MERGE_POLICIES: dict[str, Callable[[Any, Any], Any]] = {
    "username": inherit_empty,
    "groupname": inherit_empty,
    "homedir": inherit_empty,
    "git_user": inherit_empty,
    "git_email": inherit_empty,
    "shell": inherit_empty,
    "packages": merge_unique,
    "aur_packages": merge_unique,
    "services": merge_unique,
    "fonts": merge_unique,
    "file_associations": merge_mapping,
    "files": partial(merge_by, key=itemgetter("target")),
    "nfs_sources": partial(merge_by, key=itemgetter("source")),
    "printers": partial(merge_by, key=itemgetter("name")),
}


def merge_host_data(
    defaults: AllHostDataFragment, host: HostDataFragment
) -> dict[str, Any]:
    base = defaults.model_dump()
    override = host.model_dump(exclude_unset=True, exclude_none=True)
    merged = {**base, **override}
    for field, policy in MERGE_POLICIES.items():
        merged[field] = policy(base[field], override.get(field, base[field]))
    return merged
