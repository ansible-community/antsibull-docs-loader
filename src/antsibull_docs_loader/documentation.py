# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Documentation processing.
"""

from __future__ import annotations

import copy
import dataclasses
import typing as t
from collections.abc import (
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Sequence,
)


@dataclasses.dataclass
class Documentation:
    """
    Documentation of a module, plugin, or role entrypoint.
    """

    documentation: dict[str, t.Any]
    return_values: dict[str, t.Any] | None
    examples: str | None
    example_format: str

    def add_collection_name(self, *, collection_name: str, plugin_type: str) -> None:
        _add_collection_to_versions_and_dates(
            self.documentation,
            collection_name=collection_name,
            is_module=plugin_type == "module",
            is_return=False,
        )
        if self.return_values:
            _add_collection_to_versions_and_dates(
                self.return_values,
                collection_name=collection_name,
                is_module=plugin_type == "module",
                is_return=True,
            )

    def get_doc_fragments(self) -> list[str]:
        """
        Return the list of doc fragments.
        """
        return _get_fragment_list(self.documentation)

    def get_return_fragments(self) -> list[str]:
        """
        Return the list of return fragments.
        """
        return _get_fragment_list(self.return_values)

    def merge_doc_fragment(self, *, fragment: DocumentationFragment) -> None:
        """
        Merge the given doc fragment into the documentation.
        """
        _merge_doc_fragment(self.documentation, fragment.data)

    def merge_return_fragment(self, *, fragment: DocumentationFragment) -> None:
        """
        Merge the given doc fragment into the return value documentation.
        """
        if self.return_values is None:
            self.return_values = {}
        _merge_return_doc_fragment(self.return_values, fragment.return_data)


@dataclasses.dataclass
class RoleDocumentation:
    """
    Documentation of a role.
    """

    entrypoints: dict[str, Documentation]

    def add_collection_name(self, *, collection_name: str) -> None:
        for doc in self.entrypoints.values():
            _add_collection_to_versions_and_dates(
                doc.documentation,
                collection_name=collection_name,
                is_module=False,
                is_return=False,
            )


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

    Upon loading, both ``data`` and ``return_data`` are the same
    object. Only when calling ``add_collection_name`` a deep copy
    of ``data`` is stored in ``return_data``, and both will be
    adjusted accordingly their potential (but not yet known) type.
    """

    data: dict[str, t.Any]
    return_data: dict[str, t.Any]

    def add_collection_name(self, *, collection_name: str) -> None:
        assert self.data is self.return_data
        self.return_data = copy.deepcopy(self.data)
        _add_collection_to_versions_and_dates(
            self.data,
            collection_name=collection_name,
            is_module=False,
            is_return=False,
        )
        _add_collection_to_versions_and_dates(
            self.return_data,
            collection_name=collection_name,
            is_module=False,
            is_return=True,
        )


@dataclasses.dataclass
class DocumentationFragments:
    """
    A documentation fragment file's contents.
    """

    fragments: dict[str, DocumentationFragment]

    def add_collection_name(self, *, collection_name: str) -> None:
        for fragment in self.fragments.values():
            fragment.add_collection_name(collection_name=collection_name)


def _process_versions_and_dates(  # noqa: C901
    fragment: MutableMapping[str, t.Any],
    *,
    is_module: bool,
    is_return: bool,
    callback: t.Callable[[MutableMapping[str, t.Any], str, str], None],
) -> None:
    def process_deprecation(
        deprecation: MutableMapping[str, t.Any], *, top_level: bool = False
    ) -> None:
        collection_name = "removed_from_collection" if top_level else "collection_name"
        if (
            is_module or top_level
        ) and "removed_in" in deprecation:  # used in module deprecations
            callback(deprecation, "removed_in", collection_name)
        if "removed_at_date" in deprecation:
            callback(deprecation, "removed_at_date", collection_name)
        if (
            not (is_module or top_level) and "version" in deprecation
        ):  # used in plugin option deprecations
            callback(deprecation, "version", collection_name)

    def process_option_specifiers(specifiers: MutableSequence[t.Any]) -> None:
        for specifier in specifiers:
            if not isinstance(specifier, MutableMapping):
                continue
            if "version_added" in specifier:
                callback(specifier, "version_added", "version_added_collection")
            if isinstance(specifier.get("deprecated"), MutableMapping):
                process_deprecation(specifier["deprecated"])

    def process_options(options: MutableMapping[str, t.Any]) -> None:
        for option in options.values():
            if not isinstance(option, MutableMapping):
                continue
            if "version_added" in option:
                callback(option, "version_added", "version_added_collection")
            if not is_module:
                if isinstance(option.get("env"), MutableSequence):
                    process_option_specifiers(option["env"])
                if isinstance(option.get("ini"), MutableSequence):
                    process_option_specifiers(option["ini"])
                if isinstance(option.get("vars"), MutableSequence):
                    process_option_specifiers(option["vars"])
                if isinstance(option.get("deprecated"), MutableMapping):
                    process_deprecation(option["deprecated"])
            if isinstance(option.get("suboptions"), MutableMapping):
                process_options(option["suboptions"])

    def process_return_values(return_values: MutableMapping[str, t.Any]) -> None:
        for return_value in return_values.values():
            if not isinstance(return_value, MutableMapping):
                continue
            if "version_added" in return_value:
                callback(return_value, "version_added", "version_added_collection")
            if isinstance(return_value.get("contains"), MutableMapping):
                process_return_values(return_value["contains"])

    def process_attributes(attributes: MutableMapping[str, t.Any]) -> None:
        for attribute in attributes.values():
            if not isinstance(attribute, MutableMapping):
                continue
            if "version_added" in attribute:
                callback(attribute, "version_added", "version_added_collection")

    if not fragment:
        return

    if is_return:
        process_return_values(fragment)
        return

    if "version_added" in fragment:
        callback(fragment, "version_added", "version_added_collection")
    if isinstance(fragment.get("deprecated"), MutableMapping):
        process_deprecation(fragment["deprecated"], top_level=True)
    if isinstance(fragment.get("options"), MutableMapping):
        process_options(fragment["options"])
    if isinstance(fragment.get("attributes"), MutableMapping):
        process_attributes(fragment["attributes"])


def _add_collection_to_versions_and_dates(
    fragment: MutableMapping[str, t.Any],
    *,
    collection_name: str,
    is_module: bool,
    is_return: bool,
) -> None:
    def add(
        options: MutableMapping[str, t.Any], _option: str, collection_name_field: str
    ) -> None:
        if collection_name_field not in options:
            options[collection_name_field] = collection_name

    _process_versions_and_dates(
        fragment, is_module=is_module, is_return=is_return, callback=add
    )


def _get_fragment_list(docs: Mapping[str, t.Any] | None) -> list[str]:
    if not docs:
        return []
    fragments = docs.get("extends_documentation_fragment")
    if isinstance(fragments, str):
        return [fragments]
    if not isinstance(fragments, list):
        return []
    if any(not isinstance(f, str) for f in fragments):
        return []
    return fragments


def _merge_fragment(
    target: MutableMapping[str, t.Any], source: Mapping[str, t.Any], key_prefix: str
):
    for key, value in source.items():
        if key in target:
            t_value = target[key]
            if isinstance(value, MutableMapping) and isinstance(
                t_value, MutableMapping
            ):
                value.update(t_value)
            elif isinstance(value, MutableSet) and isinstance(t_value, MutableSet):
                # MutableSet does not have update()
                for v in t_value:
                    value.add(v)
            elif isinstance(value, MutableSequence) and isinstance(
                t_value, MutableSequence
            ):
                v = set(value)
                v.update(t_value)
                value = sorted(v)
            else:
                raise ValueError(
                    "Type mismatch when merging a documentation fragment:"
                    f" trying to merge {type(t_value)} into {type(value)} for key {key_prefix}{key}"
                )
        target[key] = value


def _merge_doc_fragment(
    documentation: MutableMapping[str, t.Any], fragment: Mapping[str, t.Any]
) -> None:
    temp_fragment = {k: copy.deepcopy(v) for k, v in fragment.items()}
    for doc_key in ("notes", "seealso"):
        elements = temp_fragment.pop(doc_key, None)
        if elements:
            if isinstance(elements, str) or not isinstance(elements, Sequence):
                raise ValueError(
                    f"{doc_key} not a list in documentation fragment, but {type(elements)}"
                )
            if doc_key not in documentation:
                documentation[doc_key] = []
            if not isinstance(documentation[doc_key], MutableSequence):
                raise ValueError(
                    f"{doc_key} not a list in documentation, but {type(documentation[doc_key])}"
                )
            documentation[doc_key].extend(elements)

    for doc_key in ("options", "attributes"):
        elements = temp_fragment.pop(doc_key, None)
        if not isinstance(elements, Mapping):
            continue
        if isinstance(documentation.get(doc_key), MutableMapping):
            _merge_fragment(documentation[doc_key], elements, f"{doc_key}.")
        else:
            documentation[doc_key] = elements

    _merge_fragment(documentation, temp_fragment, "")


def _merge_return_doc_fragment(
    return_values: MutableMapping[str, t.Any], fragment: Mapping[str, t.Any]
) -> None:
    _merge_fragment(return_values, copy.deepcopy(fragment), "")


__all__ = (
    "Documentation",
    "RoleDocumentation",
    "DocumentationFragment",
    "DocumentationFragments",
)
