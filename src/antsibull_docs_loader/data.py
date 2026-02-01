# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Data structures.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterable
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class CollectionInfo:
    path: Path
    namespace: str
    name: str
    full_name: str
    version: str | None
    is_ansible_core: bool = False


@dataclasses.dataclass(frozen=True)
class CollectionInfos:
    ansible_core: CollectionInfo | None
    collections: dict[str, CollectionInfo]

    @staticmethod
    def build(collections: Iterable[CollectionInfo]) -> CollectionInfos:
        ansible_core: CollectionInfo | None = None
        name_to_coll: dict[str, CollectionInfo] = {}
        cores = [collection for collection in collections if collection.is_ansible_core]
        if len(cores) > 1:
            raise ValueError(
                "Found more than one collection claiming to be ansible-core"
            )
        ansible_core = cores[0] if cores else None
        if ansible_core:
            if ansible_core.full_name != "ansible.builtin":
                raise ValueError(
                    f"Ansible-core has wrong full name {ansible_core.full_name!r}"
                )
            name_to_coll[ansible_core.full_name] = ansible_core
        for collection in collections:
            if collection.full_name in ("ansible.builtin", "ansible.legacy"):
                continue
            if collection.full_name not in name_to_coll:
                name_to_coll[collection.full_name] = collection
        return CollectionInfos(
            ansible_core=ansible_core,
            collections=name_to_coll,
        )


__all__ = (
    "CollectionInfo",
    "CollectionInfos",
)
