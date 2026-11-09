# Author: Felix Fontein <felix@fontein.de>
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Test loader code.
"""

from __future__ import annotations

from pathlib import Path

import pytest  # pylint: disable=import-error

from antsibull_docs_loader.data import CollectionInfo
from antsibull_docs_loader.loader import (
    Documentation,
    DocumentationFragment,
    DocumentationFragments,
    RoleDocumentation,
    load_collection_info,
    load_docs,
    load_docs_from_python_contents,
    load_docs_from_python_doc_fragment_contents,
    load_docs_from_python_doc_fragment_file,
    load_docs_from_python_file,
    load_docs_from_role_argspec_contents,
    load_docs_from_role_argspec_file,
    load_docs_from_yaml_contents,
    load_docs_from_yaml_file,
)


def test_load_collection_info(tmp_path: Path) -> None:
    galaxy_yml = tmp_path / "galaxy.yml"
    galaxy_yml.write_text("""---
namespace: foo
name: bar
version: 1.2.3
""")
    assert load_collection_info(tmp_path) == CollectionInfo(
        path=tmp_path,
        namespace="foo",
        name="bar",
        full_name="foo.bar",
        version="1.2.3",
        is_ansible_core=False,
    )

    galaxy_yml.write_text("""---
namespace: foo
name: bar
""")
    assert load_collection_info(tmp_path) == CollectionInfo(
        path=tmp_path,
        namespace="foo",
        name="bar",
        full_name="foo.bar",
        version=None,
        is_ansible_core=False,
    )

    galaxy_yml.write_text("[]")
    with pytest.raises(
        ValueError, match="/galaxy.yml is not a mapping, but <class 'list'>$"
    ):
        load_collection_info(tmp_path)

    galaxy_yml.write_text("""
namespace: 1
""")
    with pytest.raises(
        ValueError,
        match="^namespace field of .*/galaxy.yml is not a string, but <class 'int'>$",
    ):
        load_collection_info(tmp_path)

    galaxy_yml.write_text("""
namespace: foo
name: no
""")
    with pytest.raises(
        ValueError,
        match="^name field of .*/galaxy.yml is not a string, but <class 'bool'>$",
    ):
        load_collection_info(tmp_path)

    galaxy_yml.write_text("""
namespace: foo
name: bar
version: 1.2
""")
    with pytest.raises(
        ValueError,
        match="^version field of .*/galaxy.yml is not a string, but <class 'float'>$",
    ):
        load_collection_info(tmp_path)


def test_load_docs_from_python_contents() -> None:
    with pytest.raises(ValueError, match="^Python parsing failed: invalid syntax"):
        load_docs_from_python_contents("foo =")

    with pytest.raises(
        ValueError,
        match="^Error while parsing DOCUMENTATION: while parsing a flow node",
    ):
        load_docs_from_python_contents("DOCUMENTATION = 'a: {'")


def test_load_docs_from_python_file(tmp_path: Path) -> None:
    file = tmp_path / "foo.py"
    with pytest.raises(
        ValueError, match="^Error while reading .*/foo.py: .*No such file or directory"
    ):
        load_docs_from_python_file(file)

    file.write_text("foo =")
    with pytest.raises(
        ValueError,
        match="^Error while parsing .*/foo.py: Python parsing failed: invalid syntax",
    ):
        load_docs_from_python_file(file)

    file.write_text("RETURN = 'b: ['")
    with pytest.raises(
        ValueError,
        match=(
            "^Error while parsing .*/foo.py: Error while parsing RETURN:"
            " while parsing a flow node"
        ),
    ):
        load_docs_from_python_file(file)


LOAD_DOCS_FROM_PYTHON_DATA: list[tuple[str, Documentation | None]] = [
    (
        "",
        None,
    ),
    (
        """
a[:] = z = x, y = a = "foo"
""",
        None,
    ),
    (
        """
x, y = 1, 2
y = 1
x = y
x = y = 1
x, y = y, x = 1, 2
z = ""
EXAMPLES = "baz: bam"
RETURN = "foo: bar"
""",
        None,
    ),
    (
        """
DOCUMENTATION = "mii: moo"
EXAMPLES = "baz: bam"
RETURN = "foo: bar"
""",
        Documentation(
            documentation={
                "mii": "moo",
            },
            return_values={
                "foo": "bar",
            },
            examples="baz: bam",
            example_format="yaml",
        ),
    ),
    (
        """
DOCUMENTATION = "mii: moo"
EXAMPLES = '''
# fmt: ini
baz = bam
'''
RETURN = "foo: bar"

def foo():
    return 1
""",
        Documentation(
            documentation={
                "mii": "moo",
            },
            return_values={
                "foo": "bar",
            },
            examples="\n# fmt: ini\nbaz = bam\n",
            example_format="ini",
        ),
    ),
]


@pytest.mark.parametrize(
    "content, expected_docs",
    LOAD_DOCS_FROM_PYTHON_DATA,
)
def test_load_docs_from_python(
    content: str, expected_docs: Documentation | None, tmp_path: Path
) -> None:
    docs = load_docs_from_python_contents(content)
    assert docs == expected_docs

    file = tmp_path / "foo.py"
    file.write_text(content)
    docs = load_docs_from_python_file(file)
    assert docs == expected_docs


def test_load_docs_from_yaml_contents() -> None:
    with pytest.raises(
        ValueError, match="^Error while parsing: while parsing a flow node"
    ):
        load_docs_from_yaml_contents("foo: [")

    with pytest.raises(
        ValueError,
        match="^Side-car documentation does not contain DOCUMENTATION$",
    ):
        load_docs_from_yaml_contents("")

    with pytest.raises(
        ValueError,
        match="^Expected top-level mapping, got <class 'list'>$",
    ):
        load_docs_from_yaml_contents("[]")

    with pytest.raises(
        ValueError,
        match="^Expected DOCUMENTATION to be a mapping, got <class 'int'>$",
    ):
        load_docs_from_yaml_contents("DOCUMENTATION: 42")

    with pytest.raises(
        ValueError,
        match="^Side-car documentation does not contain DOCUMENTATION$",
    ):
        load_docs_from_yaml_contents("")


def test_load_docs_from_yaml_file(tmp_path: Path) -> None:
    file = tmp_path / "foo.py"
    with pytest.raises(
        ValueError, match="^Error while reading .*/foo.py: .*No such file or directory"
    ):
        load_docs_from_yaml_file(file)

    file.write_text("[]")
    with pytest.raises(
        ValueError,
        match="^Error while parsing .*/foo.py: Expected top-level mapping, got <class 'list'>$",
    ):
        load_docs_from_yaml_file(file)


LOAD_DOCS_FROM_YAML_DATA: list[tuple[str, Documentation | None]] = [
    (
        """
DOCUMENTATION: {}
""",
        Documentation(
            documentation={},
            return_values=None,
            examples=None,
            example_format="yaml",
        ),
    ),
    (
        """
DOCUMENTATION:
  mii: moo
EXAMPLES: "baz: bam"
RETURN:
  foo: bar
""",
        Documentation(
            documentation={
                "mii": "moo",
            },
            return_values={
                "foo": "bar",
            },
            examples="baz: bam",
            example_format="yaml",
        ),
    ),
    (
        """
DOCUMENTATION:
  mii: moo
EXAMPLES: |-
  # fmt: ini
  baz = bam
RETURN:
  foo: bar
whatever: []
""",
        Documentation(
            documentation={
                "mii": "moo",
            },
            return_values={
                "foo": "bar",
            },
            examples="# fmt: ini\nbaz = bam",
            example_format="ini",
        ),
    ),
    (
        """
DOCUMENTATION:
  mii: moo
EXAMPLES:
  - baz: bam
  - foo
RETURN:
  foo: bar
whatever: []
""",
        Documentation(
            documentation={
                "mii": "moo",
            },
            return_values={
                "foo": "bar",
            },
            examples="- baz: bam\n- foo\n",
            example_format="yaml",
        ),
    ),
]


@pytest.mark.parametrize(
    "content, expected_docs",
    LOAD_DOCS_FROM_YAML_DATA,
)
def test_load_docs_from_yaml(
    content: str, expected_docs: Documentation | None, tmp_path: Path
) -> None:
    docs = load_docs_from_yaml_contents(content)
    assert docs == expected_docs

    file = tmp_path / "foo.yaml"
    file.write_text(content)
    docs = load_docs_from_yaml_file(file)
    assert docs == expected_docs


def test_load_docs(tmp_path: Path) -> None:
    py = tmp_path / "foo.py"
    yml = tmp_path / "foo.yml"

    py.write_text("")
    assert load_docs([py]) is None

    yml.write_text("")
    with pytest.raises(
        ValueError,
        match=(
            "^Error while parsing .*/foo.yml:"
            " Side-car documentation does not contain DOCUMENTATION$"
        ),
    ):
        load_docs([py, yml])

    yml.write_text("DOCUMENTATION: {}")
    assert load_docs([py, yml]) == Documentation(
        documentation={},
        return_values=None,
        examples=None,
        example_format="yaml",
    )

    py.write_text("DOCUMENTATION = 'short_description: hello'")
    assert load_docs([py]) == Documentation(
        documentation={
            "short_description": "hello",
        },
        return_values=None,
        examples=None,
        example_format="yaml",
    )


def test_load_docs_from_role_argspec_contents() -> None:
    with pytest.raises(
        ValueError, match="^Error while parsing: while parsing a flow node"
    ):
        load_docs_from_role_argspec_contents("foo: [")

    with pytest.raises(
        ValueError,
        match="^Expected top-level mapping, got <class 'list'>$",
    ):
        load_docs_from_role_argspec_contents("[]")

    with pytest.raises(
        ValueError,
        match="^Expected argument_specs to be a mapping, got <class 'int'>$",
    ):
        load_docs_from_role_argspec_contents("argument_specs: 42")

    with pytest.raises(
        ValueError,
        match="^Expected argument_specs\\.foo to be a mapping, got <class 'str'>$",
    ):
        load_docs_from_role_argspec_contents("argument_specs: {foo: bar}")


def test_load_docs_from_role_argspec_file(tmp_path: Path) -> None:
    file = tmp_path / "foo.yaml"
    with pytest.raises(
        ValueError,
        match="^Error while reading .*/foo.yaml: .*No such file or directory",
    ):
        load_docs_from_role_argspec_file(file)

    file.write_text("[]")
    with pytest.raises(
        ValueError,
        match="^Error while parsing .*/foo.yaml: Expected top-level mapping, got <class 'list'>$",
    ):
        load_docs_from_role_argspec_file(file)


LOAD_DOCS_FROM_ROLE_ARGSPEC_DATA: list[tuple[str, RoleDocumentation | None]] = [
    ("", None),
    ("foo: bar", None),
    (
        "argument_specs: {}",
        RoleDocumentation(entrypoints={}),
    ),
    (
        """
argument_specs:
  main:
    mii: moo
    foo:
      - bar
""",
        RoleDocumentation(
            entrypoints={
                "main": Documentation(
                    documentation={"mii": "moo", "foo": ["bar"]},
                    return_values=None,
                    examples=None,
                    example_format="yaml",
                ),
            },
        ),
    ),
    (
        """
argument_specs:
  main:
    mii: moo
    examples: "baz: bam"
  foo:
""",
        RoleDocumentation(
            entrypoints={
                "main": Documentation(
                    documentation={
                        "mii": "moo",
                    },
                    return_values=None,
                    examples="baz: bam",
                    example_format="yaml",
                ),
            },
        ),
    ),
]


@pytest.mark.parametrize(
    "content, expected_docs",
    LOAD_DOCS_FROM_ROLE_ARGSPEC_DATA,
)
def test_load_docs_from_role_argspec(
    content: str, expected_docs: RoleDocumentation | None, tmp_path: Path
) -> None:
    docs = load_docs_from_role_argspec_contents(content)
    assert docs == expected_docs

    file = tmp_path / "argument_specs.yaml"
    file.write_text(content)
    docs = load_docs_from_role_argspec_file(file)
    assert docs == expected_docs


def test_load_docs_from_python_doc_fragment_contents() -> None:
    with pytest.raises(
        ValueError, match="^Python parsing failed: '{' was never closed"
    ):
        load_docs_from_python_doc_fragment_contents("foo = {")

    with pytest.raises(
        ValueError,
        match="^Error while parsing fragment DOCUMENTATION: while parsing a flow node",
    ):
        load_docs_from_python_doc_fragment_contents("""
class ModuleDocFragment:
    DOCUMENTATION = "foo: {"
""")

    with pytest.raises(
        ValueError,
        match="^Fragment DOCUMENTATION is not a mapping, but <class 'list'>$",
    ):
        load_docs_from_python_doc_fragment_contents("""
class ModuleDocFragment:
    DOCUMENTATION = "[]"
""")


def test_load_docs_from_python_doc_fragment_file(tmp_path: Path) -> None:
    file = tmp_path / "foo.py"
    with pytest.raises(
        ValueError, match="^Error while reading .*/foo.py: .*No such file or directory"
    ):
        load_docs_from_python_doc_fragment_file(file)

    file.write_text("foo = {")
    with pytest.raises(
        ValueError,
        match="^Error while parsing .*/foo.py: Python parsing failed: '{' was never closed",
    ):
        load_docs_from_python_doc_fragment_file(file)


LOAD_DOCS_FROM_PYTHON_DOC_FRAGMENT_DATA: list[
    tuple[str, DocumentationFragments | None]
] = [
    ("", None),
    (
        """
a = 1

class Foo:
    pass
""",
        None,
    ),
    (
        """
class ModuleDocFragment:
    x = 1

    def foo():
        pass
""",
        DocumentationFragments(fragments={}),
    ),
    (
        """
class ModuleDocFragment:
    DOCUMENTATION = ""

    FOO = "bar: baz"
""",
        DocumentationFragments(
            fragments={
                "DOCUMENTATION": DocumentationFragment(data={}),
                "FOO": DocumentationFragment(data={"bar": "baz"}),
            }
        ),
    ),
]


@pytest.mark.parametrize(
    "content, expected_docs",
    LOAD_DOCS_FROM_PYTHON_DOC_FRAGMENT_DATA,
)
def test_load_docs_from_python_doc_fragment(
    content: str, expected_docs: DocumentationFragments | None, tmp_path: Path
) -> None:
    docs = load_docs_from_python_doc_fragment_contents(content)
    assert docs == expected_docs

    file = tmp_path / "foo.py"
    file.write_text(content)
    docs = load_docs_from_python_doc_fragment_file(file)
    assert docs == expected_docs
