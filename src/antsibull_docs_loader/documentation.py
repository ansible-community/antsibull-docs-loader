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
    documentation: dict[str, t.Any]
    return_values: dict[str, t.Any] | None
    examples: str | None
    example_format: str


@dataclasses.dataclass
class RoleDocumentation:
    entrypoints: dict[str, Documentation]


@dataclasses.dataclass
class DocumentationFragment:
    data: dict[str, t.Any]


@dataclasses.dataclass
class DocumentationFragments:
    fragments: dict[str, DocumentationFragment]


__all__ = (
    "Documentation",
    "RoleDocumentation",
    "DocumentationFragment",
    "DocumentationFragments",
)
