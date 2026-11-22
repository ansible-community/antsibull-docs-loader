# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Use routing information to find plugins.
"""

from __future__ import annotations

import dataclasses
import enum
import typing as t

from .routing import CollectionRouting, File, PluginRouting, RemovalData

if t.TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Mapping

    from .ansible import PluginType


class Resolved(enum.Enum):
    NOT_FOUND = 1
    REDIRECT_ERROR = 2
    COLLECTION_MISSING = 3
    TOMBSTONE = 4
    FOUND = 5


@dataclasses.dataclass(frozen=True)
class ResolveResult:
    status: Resolved
    fqcn: str
    deprecations: list[tuple[str, RemovalData]]
    tombstone: RemovalData | None  # present for TOMBSTONE
    error: str | None  # present for COLLECTION_MISSING and REDIRECT_ERROR
    resolved: File | None  # present for FOUND


def _get_routing(
    routing: CollectionRouting, *, fqcn: list[str], plugin_type: PluginType
) -> PluginRouting | None:
    plugin_routing = routing.plugin_data.get(plugin_type)
    if plugin_routing is None:
        return None
    return plugin_routing.get(".".join(fqcn[2:]))


def _get_file(
    routing: CollectionRouting, *, fqcn: list[str], plugin_type: PluginType
) -> File | None:
    file_data = routing.files.get(plugin_type)
    if file_data is None:
        return None
    return file_data.get(tuple(fqcn[2:]))


def _handle_redirect(
    *,
    routing_data: Mapping[str, CollectionRouting],
    fqcn: str,
    parts: list[str],
    plugin_type: PluginType,
    collection_name: str,
    collection_routing: CollectionRouting,
    routing: PluginRouting,
    deprecations: list[tuple[str, RemovalData]],
) -> tuple[str, list[str], CollectionRouting, ResolveResult | None]:
    if routing.tombstone is not None:
        return (
            fqcn,
            parts,
            collection_routing,
            ResolveResult(
                status=Resolved.TOMBSTONE,
                fqcn=fqcn,
                deprecations=deprecations,
                tombstone=routing.tombstone,
                error=None,
                resolved=None,
            ),
        )
    if routing.redirect_deprecations is not None:
        deprecations.extend(routing.redirect_deprecations)
    is_routing = False
    if routing.redirect is not None and routing.redirect is not ...:
        is_routing = True
        fqcn = routing.redirect
        parts = fqcn.split(".")
        if len(parts) >= 3:
            collection_name = ".".join(parts[:2])
            collection_routing_opt = routing_data.get(collection_name)
            if collection_routing_opt is None:
                return (
                    fqcn,
                    parts,
                    collection_routing,
                    ResolveResult(
                        status=Resolved.COLLECTION_MISSING,
                        fqcn=fqcn,
                        deprecations=deprecations,
                        tombstone=None,
                        error=f"Collection {collection_name} not found",
                        resolved=None,
                    ),
                )
            collection_routing = collection_routing_opt
        else:
            assert routing.redirect_dead_end or routing.redirect_error is not None
    elif routing.deprecation is not None:
        deprecations.append((fqcn, routing.deprecation))
    if routing.redirect_dead_end or routing.redirect_error is not None:
        return (
            fqcn,
            parts,
            collection_routing,
            ResolveResult(
                status=Resolved.REDIRECT_ERROR,
                fqcn=fqcn,
                deprecations=deprecations,
                tombstone=None,
                error=routing.redirect_error or "Unknown error",
                resolved=None,
            ),
        )
    if not is_routing:
        return fqcn, parts, collection_routing, None
    routing_opt = _get_routing(collection_routing, fqcn=parts, plugin_type=plugin_type)
    if routing_opt is None:
        return fqcn, parts, collection_routing, None
    return _handle_redirect(
        routing_data=routing_data,
        fqcn=fqcn,
        parts=parts,
        plugin_type=plugin_type,
        collection_name=collection_name,
        collection_routing=collection_routing,
        routing=routing_opt,
        deprecations=deprecations,
    )


def resolve(
    routing_data: Mapping[str, CollectionRouting], *, fqcn: str, plugin_type: PluginType
) -> ResolveResult:
    """
    Resolve a plugin/object ``fqcn`` of type ``plugin_type``.

    Assumes that all redirects in ``routing_data`` have been completed.
    """
    parts = fqcn.split(".")
    if len(parts) < 3:
        raise ValueError(f"Expected FQCN, got {fqcn!r}")
    deprecations: list[tuple[str, RemovalData]] = []
    collection_name = ".".join(parts[:2])
    collection_routing = routing_data.get(collection_name)
    if collection_routing is None:
        return ResolveResult(
            status=Resolved.COLLECTION_MISSING,
            fqcn=fqcn,
            deprecations=deprecations,
            tombstone=None,
            error=f"Collection {collection_name} not found",
            resolved=None,
        )
    routing = _get_routing(collection_routing, fqcn=parts, plugin_type=plugin_type)
    if routing is not None:
        fqcn, parts, collection_routing, result = _handle_redirect(
            routing_data=routing_data,
            fqcn=fqcn,
            parts=parts,
            plugin_type=plugin_type,
            collection_name=collection_name,
            collection_routing=collection_routing,
            routing=routing,
            deprecations=deprecations,
        )
        if result is not None:
            return result
    file = _get_file(collection_routing, fqcn=parts, plugin_type=plugin_type)
    if file is None:
        return ResolveResult(
            status=Resolved.NOT_FOUND,
            fqcn=fqcn,
            deprecations=deprecations,
            tombstone=None,
            error=None,
            resolved=None,
        )
    return ResolveResult(
        status=Resolved.FOUND,
        fqcn=fqcn,
        deprecations=deprecations,
        tombstone=None,
        error=None,
        resolved=file,
    )


__all__ = ("Resolved", "ResolveResult", "resolve")
