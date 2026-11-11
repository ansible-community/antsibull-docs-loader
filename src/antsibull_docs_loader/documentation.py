# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Documentation processing.
"""

from __future__ import annotations

import dataclasses
import typing as t


@dataclasses.dataclass
class Documentation:
    """
    Documentation of a module, plugin, or role entrypoint.
    """

    documentation: dict[str, t.Any]
    return_values: dict[str, t.Any] | None
    examples: str | None
    example_format: str


@dataclasses.dataclass
class RoleDocumentation:
    """
    Documentation of a role.
    """

    entrypoints: dict[str, Documentation]


@dataclasses.dataclass
class DocumentationFragment:
    """
    A documentation fragment.

    Since a documentation fragment might be used for documentation
    or for return values, and both have very different structures,
    we store the fragment twice.

    (It is unlikely that there exists a non-trivial useful fragment
    that can be used as both. But unless this is proven to not exist,
    we have to assume that the fragment can be used for both.)
    """

    data: dict[str, t.Any]
    return_data: dict[str, t.Any]


@dataclasses.dataclass
class DocumentationFragments:
    """
    A documentation fragment file's contents.
    """

    fragments: dict[str, DocumentationFragment]


__all__ = (
    "Documentation",
    "RoleDocumentation",
    "DocumentationFragment",
    "DocumentationFragments",
)
