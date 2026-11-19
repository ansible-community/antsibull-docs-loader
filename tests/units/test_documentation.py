# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Test loader code.
"""

from __future__ import annotations

import pytest  # pylint: disable=import-error

from antsibull_docs_loader.ansible import PluginType
from antsibull_docs_loader.documentation import (
    Documentation,
    DocumentationFragment,
    DocumentationFragments,
    RoleDocumentation,
)

TEST_GET_DOC_RETURN_FRAGMENTS_DATA: list[tuple[Documentation, list[str], list[str]]] = [
    (
        Documentation(
            documentation={
                "foo": "bar",
            },
            return_values=None,
            examples=None,
            example_format="",
        ),
        [],
        [],
    ),
    (
        Documentation(
            documentation={
                "extends_documentation_fragment": None,
            },
            return_values={
                "extends_documentation_fragment": {
                    "hello": "world",
                },
            },
            examples=None,
            example_format="",
        ),
        [],
        [],
    ),
    (
        Documentation(
            documentation={
                "extends_documentation_fragment": [1, 2, 3],
            },
            return_values={
                "extends_documentation_fragment": ["true", False],
            },
            examples=None,
            example_format="",
        ),
        [],
        [],
    ),
    (
        Documentation(
            documentation={
                "extends_documentation_fragment": ["foo", "", "bar"],
            },
            return_values={
                "extends_documentation_fragment": "a.b.c",
            },
            examples=None,
            example_format="",
        ),
        ["foo", "", "bar"],
        ["a.b.c"],
    ),
]


@pytest.mark.parametrize(
    "documentation, expected_doc_fragments, expected_return_fragments",
    TEST_GET_DOC_RETURN_FRAGMENTS_DATA,
)
def test_get_doc_return_fragments_data(
    documentation: Documentation,
    expected_doc_fragments: list[str],
    expected_return_fragments: list[str],
) -> None:
    assert documentation.get_doc_fragments() == expected_doc_fragments
    assert documentation.get_return_fragments() == expected_return_fragments


TEST_MERGE_DOC_RETURN_FRAGMENT_DATA: list[
    tuple[Documentation, DocumentationFragment, Documentation]
] = [
    (
        Documentation(
            documentation={},
            return_values=None,
            examples=None,
            example_format="",
        ),
        DocumentationFragment(
            data={},
            return_data={},
        ),
        Documentation(
            documentation={},
            return_values={},
            examples=None,
            example_format="",
        ),
    ),
    (
        Documentation(
            documentation={
                "foo": "bar",
                "bar": {
                    "a": 1,
                    "b": 2,
                },
                "options": {
                    "foo": {
                        "type": "int",
                        "default": 42,
                    },
                    "bar": {
                        "type": "str",
                        "default": "hello",
                        "description": ["foo", "bar"],
                    },
                },
                "notes": ["baz", "bam"],
            },
            return_values={
                "foo": "bar",
                "bar": [12, 14, 13],
                "foobar": {1, 2},
            },
            examples=None,
            example_format="",
        ),
        DocumentationFragment(
            data={
                "baz": "bam",
                "bar": {
                    "b": 23,
                    "c": 3,
                },
                "options": {
                    "bar": {
                        "default": "world",
                        "description": ["duh"],
                    },
                    "baz": {
                        "type": "dict",
                        "elements": "list",
                    },
                },
                "notes": ["foo", "bar"],
                "seealso": [{"module": "a.b.c"}],
                "attributes": {"foo": {"support": "none"}},
            },
            return_data={
                "baz": "bam",
                "bar": [30, 23, 11],
                "foobar": {2, "bam"},
            },
        ),
        Documentation(
            documentation={
                "foo": "bar",
                "baz": "bam",
                "bar": {
                    "a": 1,
                    "b": 2,
                    "c": 3,
                },
                "options": {
                    "foo": {
                        "type": "int",
                        "default": 42,
                    },
                    "bar": {
                        "type": "str",
                        "default": "hello",
                        "description": ["foo", "bar"],
                    },
                    "baz": {
                        "type": "dict",
                        "elements": "list",
                    },
                },
                "notes": ["baz", "bam", "foo", "bar"],
                "seealso": [{"module": "a.b.c"}],
                "attributes": {"foo": {"support": "none"}},
            },
            return_values={
                "foo": "bar",
                "baz": "bam",
                "bar": [11, 12, 13, 14, 23, 30],
                "foobar": {1, 2, "bam"},
            },
            examples=None,
            example_format="",
        ),
    ),
]


@pytest.mark.parametrize(
    "documentation, fragment, expected_documentation",
    TEST_MERGE_DOC_RETURN_FRAGMENT_DATA,
)
def test_merge_doc_return_fragment(
    documentation: Documentation,
    fragment: DocumentationFragment,
    expected_documentation: Documentation,
) -> None:
    documentation.merge_doc_fragment(fragment=fragment)
    assert documentation.documentation == expected_documentation.documentation

    documentation.merge_return_fragment(fragment=fragment)
    assert documentation.return_values == expected_documentation.return_values


TEST_MERGE_DOC_RETURN_FRAGMENT_FAIL_DATA: list[
    tuple[Documentation, DocumentationFragment, str]
] = [
    (
        Documentation(
            documentation={
                "foo": ["bar"],
            },
            return_values=None,
            examples=None,
            example_format="",
        ),
        DocumentationFragment(
            data={
                "foo": {
                    "bar": ["baz"],
                },
            },
            return_data={},
        ),
        "^Type mismatch when merging a documentation fragment:"
        " trying to merge <class 'list'> into <class 'dict'> for key foo$",
    ),
    (
        Documentation(
            documentation={
                "notes": "123",
            },
            return_values=None,
            examples=None,
            example_format="",
        ),
        DocumentationFragment(
            data={"notes": [1, 2, 3]},
            return_data={},
        ),
        "^notes not a list in documentation, but <class 'str'>$",
    ),
    (
        Documentation(
            documentation={
                "notes": [1, 2, 3],
            },
            return_values=None,
            examples=None,
            example_format="",
        ),
        DocumentationFragment(
            data={"notes": "123"},
            return_data={},
        ),
        "^notes not a list in documentation fragment, but <class 'str'>$",
    ),
]


@pytest.mark.parametrize(
    "documentation, fragment, expected_error",
    TEST_MERGE_DOC_RETURN_FRAGMENT_FAIL_DATA,
)
def test_merge_doc_return_fragment_fail(
    documentation: Documentation,
    fragment: DocumentationFragment,
    expected_error: str,
) -> None:
    with pytest.raises(ValueError, match=expected_error):
        documentation.merge_doc_fragment(fragment=fragment)


TEST_DOCUMENTATION_ADD_COLLECTION_NAME_DATA: list[
    tuple[Documentation, str, PluginType, Documentation]
] = [
    (
        Documentation(
            documentation={},
            return_values=None,
            examples=None,
            example_format="",
        ),
        "foo.bar",
        "module",
        Documentation(
            documentation={},
            return_values=None,
            examples=None,
            example_format="",
        ),
    ),
    (
        Documentation(
            documentation={
                "foo": ["bar"],
            },
            return_values=None,
            examples=None,
            example_format="",
        ),
        "foo.bar",
        "module",
        Documentation(
            documentation={
                "foo": ["bar"],
            },
            return_values=None,
            examples=None,
            example_format="",
        ),
    ),
    (
        Documentation(
            documentation={
                "foo": ["bar"],
                "version_added": "1.2.3",
                "deprecated": {
                    "removed_in": "2.0.0",
                },
                "options": {
                    "foo": {
                        "version_added": "1.2.0",
                        "suboptions": {
                            "bar": {
                                "type": "str",
                                "version_added": "1.4.0",
                            },
                            "baz": {
                                "description": ["123"],
                            },
                        },
                        "vars": [
                            {
                                "name": "FOO",
                                "version_added": "1.9.0",
                            },
                            {
                                "name": "BAR",
                            },
                        ],
                        "ini": [
                            {
                                "name": "foo",
                                "section": "bar",
                                "version_added": "1.9.0",
                            },
                            {
                                "name": "bar",
                                "section": "bar",
                                "deprecated": {
                                    "version": "4.0.0",
                                },
                            },
                        ],
                        "env": [
                            {
                                "name": "FOO",
                                "version_added": "1.9.0",
                            },
                            {
                                "name": "BAR",
                            },
                        ],
                        "deprecated": {
                            "version": "3.2.1",
                        },
                    },
                    "blah": 123,
                },
                "attributes": {
                    "foo": {
                        "support": "none",
                        "version_added": "1.3.0",
                    },
                    "bar": {
                        "version_added": "1.1.1",
                        "version_added_collection": "meeple",
                    },
                    "baz": {},
                    "bam": "123",
                },
            },
            return_values={
                "foo": {
                    "type": "bar",
                    "version_added": "1.0.0",
                    "contains": {
                        "meh": {
                            "version_added": "1.5.0",
                        },
                    },
                },
                "meep": 123,
            },
            examples=None,
            example_format="",
        ),
        "foo.bar",
        "module",
        Documentation(
            documentation={
                "foo": ["bar"],
                "version_added": "1.2.3",
                "version_added_collection": "foo.bar",
                "deprecated": {
                    "removed_in": "2.0.0",
                    "removed_from_collection": "foo.bar",
                },
                "options": {
                    "foo": {
                        "version_added": "1.2.0",
                        "version_added_collection": "foo.bar",
                        "suboptions": {
                            "bar": {
                                "type": "str",
                                "version_added": "1.4.0",
                                "version_added_collection": "foo.bar",
                            },
                            "baz": {
                                "description": ["123"],
                            },
                        },
                        "vars": [
                            {
                                "name": "FOO",
                                "version_added": "1.9.0",
                            },
                            {
                                "name": "BAR",
                            },
                        ],
                        "ini": [
                            {
                                "name": "foo",
                                "section": "bar",
                                "version_added": "1.9.0",
                            },
                            {
                                "name": "bar",
                                "section": "bar",
                                "deprecated": {
                                    "version": "4.0.0",
                                },
                            },
                        ],
                        "env": [
                            {
                                "name": "FOO",
                                "version_added": "1.9.0",
                            },
                            {
                                "name": "BAR",
                            },
                        ],
                        "deprecated": {
                            "version": "3.2.1",
                        },
                    },
                    "blah": 123,
                },
                "attributes": {
                    "foo": {
                        "support": "none",
                        "version_added": "1.3.0",
                        "version_added_collection": "foo.bar",
                    },
                    "bar": {
                        "version_added": "1.1.1",
                        "version_added_collection": "meeple",
                    },
                    "baz": {},
                    "bam": "123",
                },
            },
            return_values={
                "foo": {
                    "type": "bar",
                    "version_added": "1.0.0",
                    "version_added_collection": "foo.bar",
                    "contains": {
                        "meh": {
                            "version_added": "1.5.0",
                            "version_added_collection": "foo.bar",
                        },
                    },
                },
                "meep": 123,
            },
            examples=None,
            example_format="",
        ),
    ),
    (
        Documentation(
            documentation={
                "foo": ["bar"],
                "version_added": "1.2.3",
                "deprecated": {
                    "removed_at_date": "2100-01-01",
                },
                "options": {
                    "foo": {
                        "version_added": "1.2.0",
                        "suboptions": {
                            "bar": {
                                "type": "str",
                                "version_added": "1.4.0",
                            },
                            "baz": {
                                "description": ["123"],
                            },
                        },
                        "vars": [
                            {
                                "name": "FOO",
                                "version_added": "1.9.0",
                            },
                            {
                                "name": "BAR",
                                "deprecated": 123,
                            },
                            "meh",
                        ],
                        "ini": [
                            {
                                "name": "foo",
                                "section": "bar",
                                "version_added": "1.9.0",
                            },
                            {
                                "name": "bar",
                                "section": "bar",
                                "deprecated": {
                                    "version": "4.0.0",
                                },
                            },
                        ],
                        "env": [
                            {
                                "name": "FOO",
                                "version_added": "1.9.0",
                            },
                            {
                                "name": "BAR",
                            },
                        ],
                        "deprecated": {
                            "version": "3.2.1",
                        },
                    },
                    "blah": 123,
                },
                "attributes": {
                    "foo": {
                        "support": "none",
                        "version_added": "1.3.0",
                    },
                    "bar": {
                        "version_added": "1.1.1",
                        "version_added_collection": "meeple",
                    },
                    "baz": {},
                    "bam": "123",
                },
            },
            return_values={
                "foo": {
                    "type": "bar",
                    "version_added": "1.0.0",
                    "contains": {
                        "meh": {
                            "version_added": "1.5.0",
                        },
                    },
                },
                "meep": 123,
            },
            examples=None,
            example_format="",
        ),
        "foo.bar",
        "lookup",
        Documentation(
            documentation={
                "foo": ["bar"],
                "version_added": "1.2.3",
                "version_added_collection": "foo.bar",
                "deprecated": {
                    "removed_at_date": "2100-01-01",
                    "removed_from_collection": "foo.bar",
                },
                "options": {
                    "foo": {
                        "version_added": "1.2.0",
                        "version_added_collection": "foo.bar",
                        "suboptions": {
                            "bar": {
                                "type": "str",
                                "version_added": "1.4.0",
                                "version_added_collection": "foo.bar",
                            },
                            "baz": {
                                "description": ["123"],
                            },
                        },
                        "vars": [
                            {
                                "name": "FOO",
                                "version_added": "1.9.0",
                                "version_added_collection": "foo.bar",
                            },
                            {
                                "name": "BAR",
                                "deprecated": 123,
                            },
                            "meh",
                        ],
                        "ini": [
                            {
                                "name": "foo",
                                "section": "bar",
                                "version_added": "1.9.0",
                                "version_added_collection": "foo.bar",
                            },
                            {
                                "name": "bar",
                                "section": "bar",
                                "deprecated": {
                                    "version": "4.0.0",
                                    "collection_name": "foo.bar",
                                },
                            },
                        ],
                        "env": [
                            {
                                "name": "FOO",
                                "version_added": "1.9.0",
                                "version_added_collection": "foo.bar",
                            },
                            {
                                "name": "BAR",
                            },
                        ],
                        "deprecated": {
                            "version": "3.2.1",
                            "collection_name": "foo.bar",
                        },
                    },
                    "blah": 123,
                },
                "attributes": {
                    "foo": {
                        "support": "none",
                        "version_added": "1.3.0",
                        "version_added_collection": "foo.bar",
                    },
                    "bar": {
                        "version_added": "1.1.1",
                        "version_added_collection": "meeple",
                    },
                    "baz": {},
                    "bam": "123",
                },
            },
            return_values={
                "foo": {
                    "type": "bar",
                    "version_added": "1.0.0",
                    "version_added_collection": "foo.bar",
                    "contains": {
                        "meh": {
                            "version_added": "1.5.0",
                            "version_added_collection": "foo.bar",
                        },
                    },
                },
                "meep": 123,
            },
            examples=None,
            example_format="",
        ),
    ),
]


@pytest.mark.parametrize(
    "documentation, collection_name, plugin_type, expected_documentation",
    TEST_DOCUMENTATION_ADD_COLLECTION_NAME_DATA,
)
def test_documentation_add_collection_name(
    documentation: Documentation,
    collection_name: str,
    plugin_type: PluginType,
    expected_documentation: Documentation,
) -> None:
    documentation.add_collection_name(
        collection_name=collection_name, plugin_type=plugin_type
    )
    assert documentation == expected_documentation


TEST_ROLE_DOCUMENTATION_ADD_COLLECTION_NAME_DATA: list[
    tuple[RoleDocumentation, str, RoleDocumentation]
] = [
    (
        RoleDocumentation(
            entrypoints={
                "main": Documentation(
                    documentation={
                        "foo": ["bar"],
                    },
                    return_values=None,
                    examples=None,
                    example_format="",
                ),
            },
        ),
        "foo.bar",
        RoleDocumentation(
            entrypoints={
                "main": Documentation(
                    documentation={
                        "foo": ["bar"],
                    },
                    return_values=None,
                    examples=None,
                    example_format="",
                ),
            },
        ),
    ),
]


@pytest.mark.parametrize(
    "role_docs, collection_name, expected_role_docs",
    TEST_ROLE_DOCUMENTATION_ADD_COLLECTION_NAME_DATA,
)
def test_role_documentation_add_collection_name(
    role_docs: RoleDocumentation,
    collection_name: str,
    expected_role_docs: RoleDocumentation,
) -> None:
    role_docs.add_collection_name(collection_name=collection_name)
    assert role_docs == expected_role_docs


TEST_DOCUMENTATION_FRAGMENT_ADD_COLLECTION_NAME_DATA: list[
    tuple[DocumentationFragment, str, DocumentationFragment]
] = [
    (
        DocumentationFragment(
            data={
                "foo": {
                    "bar": ["baz"],
                },
            },
            return_data={},
        ),
        "foo.bar",
        DocumentationFragment(
            data={
                "foo": {
                    "bar": ["baz"],
                },
            },
            return_data={
                "foo": {
                    "bar": ["baz"],
                },
            },
        ),
    ),
]


@pytest.mark.parametrize(
    "fragment, collection_name, expected_fragment",
    TEST_DOCUMENTATION_FRAGMENT_ADD_COLLECTION_NAME_DATA,
)
def test_documentation_fragment_add_collection_name(
    fragment: DocumentationFragment,
    collection_name: str,
    expected_fragment: DocumentationFragment,
) -> None:
    fragment.return_data = fragment.data
    fragment.add_collection_name(collection_name=collection_name)
    assert fragment == expected_fragment


TEST_DOCUMENTATION_FRAGMENTS_ADD_COLLECTION_NAME_DATA: list[
    tuple[DocumentationFragments, str, DocumentationFragments]
] = [
    (
        DocumentationFragments(
            fragments={
                "DOCUMENTATION": DocumentationFragment(
                    data={
                        "foo": {
                            "bar": ["baz"],
                        },
                    },
                    return_data={},
                ),
            }
        ),
        "foo.bar",
        DocumentationFragments(
            fragments={
                "DOCUMENTATION": DocumentationFragment(
                    data={
                        "foo": {
                            "bar": ["baz"],
                        },
                    },
                    return_data={
                        "foo": {
                            "bar": ["baz"],
                        },
                    },
                ),
            },
        ),
    ),
]


@pytest.mark.parametrize(
    "fragments, collection_name, expected_fragments",
    TEST_DOCUMENTATION_FRAGMENTS_ADD_COLLECTION_NAME_DATA,
)
def test_documentation_fragments_add_collection_name(
    fragments: DocumentationFragments,
    collection_name: str,
    expected_fragments: DocumentationFragments,
) -> None:
    for fragment in fragments.fragments.values():
        fragment.return_data = fragment.data
    fragments.add_collection_name(collection_name=collection_name)
    assert fragments == expected_fragments
