# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Data loader.
"""

from __future__ import annotations

import ast
import dataclasses
import re
import typing as t
from collections.abc import Mapping, Sequence
from pathlib import Path

from ._yaml import format_yaml as _format_yaml
from ._yaml import load_yaml_data as _load_yaml_data
from ._yaml import load_yaml_file as _load_yaml_file
from .data import CollectionInfo

EXAMPLES_FMT_RE = re.compile(r"^# fmt:\s+(\S+)")

DOCUMENTATION_SECTION = "DOCUMENTATION"
EXAMPLES_SECTION = "EXAMPLES"
RETURN_SECTION = "RETURN"


def load_collection_info(collection_root: Path) -> CollectionInfo:
    """
    Load collection information from ``galaxy.yml``.
    """
    path = collection_root / "galaxy.yml"
    data = _load_yaml_file(path)
    if not isinstance(data, Mapping):
        raise ValueError(f"{path} is not a mapping, but {type(data)}")
    namespace = data.get("namespace")
    if not isinstance(namespace, str):
        raise ValueError(
            f"namespace field of {path} is not a string, but {type(namespace)}"
        )
    name = data.get("name")
    if not isinstance(name, str):
        raise ValueError(f"name field of {path} is not a string, but {type(name)}")
    version = data.get("version")
    if version is not None and not isinstance(version, str):
        raise ValueError(
            f"version field of {path} is not a string, but {type(version)}"
        )
    return CollectionInfo(
        path=collection_root,
        namespace=namespace,
        name=name,
        full_name=f"{namespace}.{name}",
        version=version,
        is_ansible_core=False,
    )


def _iterate_targets(
    assignment: ast.Assign,
) -> t.Generator[tuple[ast.Constant, str, str]]:
    if not isinstance(assignment.value, ast.Constant):
        return
    if not isinstance(assignment.value.value, str):
        return
    for target in assignment.targets:
        if isinstance(target, ast.Name):
            yield assignment.value, assignment.value.value, target.id


@dataclasses.dataclass
class Documentation:
    documentation: Mapping[str, t.Any]
    return_values: Mapping[str, t.Any] | None
    examples: str | None
    example_format: str


@t.overload  # pragma: no cover
def get_examples_format(examples: str, *, default: str) -> str: ...


@t.overload  # pragma: no cover
def get_examples_format(examples: str, *, default: str | None = None) -> str | None: ...


def get_examples_format(examples: str, *, default: str | None = None) -> str | None:
    """
    Extract the example's format, if present.
    Return ``default`` if no format specifier was found.
    """
    fmt_match = EXAMPLES_FMT_RE.match(examples.lstrip())
    if fmt_match:
        return fmt_match.group(1)
    return default


def _parse(contents: str, *, path: Path | None) -> ast.Module:
    filename = "<unknown>"
    if path is not None:
        filename = str(path)
    try:
        return ast.parse(contents, filename=filename)
    except Exception as exc:
        raise ValueError(f"Python parsing failed: {exc}") from exc


def load_docs_from_python_contents(
    contents: str, *, path: Path | None = None
) -> Documentation | None:
    """
    Load documentation from a regular Python module/plugin's contents.

    Does not support doc fragments or roles!
    """
    root = _parse(contents, path=path)

    documentation: dict[str, t.Any] | None = None
    return_values: dict[str, t.Any] | None = None
    examples: str | None = None
    example_format: str = "yaml"

    for child in root.body:
        # We look for top-level assignments
        if not isinstance(child, ast.Assign):
            continue
        for _constant, data, section in _iterate_targets(child):
            if section not in (DOCUMENTATION_SECTION, EXAMPLES_SECTION, RETURN_SECTION):
                continue

            if section == EXAMPLES_SECTION:
                examples = data
                example_format = get_examples_format(data, default="yaml")
            else:
                try:
                    parsed_data = _load_yaml_data(data)
                except Exception as exc:
                    raise ValueError(f"Error while parsing {section}: {exc}") from exc
                if section == DOCUMENTATION_SECTION:
                    documentation = parsed_data
                else:
                    return_values = parsed_data

    if documentation is None:
        return None
    return Documentation(
        documentation=documentation,
        return_values=return_values,
        examples=examples,
        example_format=example_format,
    )


def load_docs_from_python_file(path: Path) -> Documentation | None:
    """
    Load documentation from a regular Python module/plugin.

    Does not support doc fragments or roles!
    """
    try:
        with path.open("rt", encoding="utf-8") as f:
            data = f.read()
    except Exception as exc:
        raise ValueError(f"Error while reading {path}: {exc}") from exc
    try:
        return load_docs_from_python_contents(data, path=path)
    except Exception as exc:
        raise ValueError(f"Error while parsing {path}: {exc}") from exc


def _extract_yaml_section(
    root: Mapping[str, t.Any], section: str
) -> Mapping[str, t.Any] | None:
    data = root.get(section)
    if data is None:
        return data
    if not isinstance(data, Mapping):
        raise ValueError(f"Expected {section} to be a mapping, got {type(data)}")
    return data


def _extract_examples(examples: t.Any) -> tuple[str, str] | None:
    if examples is None:
        return examples
    if isinstance(examples, str):
        return examples, get_examples_format(examples, default="yaml")
    examples = _format_yaml(examples)
    return examples, "yaml"


def _extract_yaml_docs(root: Mapping[str, t.Any]) -> Documentation | None:
    documentation: Mapping[str, t.Any] | None = _extract_yaml_section(
        root, DOCUMENTATION_SECTION
    )
    return_values: Mapping[str, t.Any] | None = _extract_yaml_section(
        root, RETURN_SECTION
    )
    examples: str | None = None
    example_format: str = "yaml"
    ex = _extract_examples(root.get(EXAMPLES_SECTION))
    if ex is not None:
        examples, example_format = ex
    if documentation is None:
        return None
    return Documentation(
        documentation=documentation,
        return_values=return_values,
        examples=examples,
        example_format=example_format,
    )


def load_docs_from_yaml_contents(
    contents: str, *, path: Path | None = None  # pylint: disable=unused-argument
) -> Documentation | None:
    """
    Load documentation from a regular side-car documentation's contents.

    Does not support doc fragments or roles!
    """
    try:
        root = _load_yaml_data(contents)
    except Exception as exc:
        raise ValueError(f"Error while parsing: {exc}") from exc
    if root is None:
        root = {}
    if not isinstance(root, Mapping):
        raise ValueError(f"Expected top-level mapping, got {type(root)}")

    result = _extract_yaml_docs(root)
    if result is not None:
        return result
    raise ValueError(f"Side-car documentation does not contain {DOCUMENTATION_SECTION}")


def load_docs_from_yaml_file(path: Path) -> Documentation | None:
    """
    Load documentation from a regular side-car documentation.

    Does not support doc fragments or roles!
    """
    try:
        with path.open("rt", encoding="utf-8") as f:
            data = f.read()
    except Exception as exc:
        raise ValueError(f"Error while reading {path}: {exc}") from exc
    try:
        return load_docs_from_yaml_contents(data, path=path)
    except Exception as exc:
        raise ValueError(f"Error while parsing {path}: {exc}") from exc


def load_docs(candidates: Sequence[Path]) -> Documentation | None:
    """
    Load documentation for a regular module/plugin.

    Does not support doc fragments or roles!
    """
    for candidate in candidates:
        if candidate.name.endswith(".py"):
            docs = load_docs_from_python_file(candidate)
            if docs is not None:
                return docs
        if candidate.name.endswith((".yml", ".yaml")):
            docs = load_docs_from_yaml_file(candidate)
            if docs is not None:
                return docs
    return None


@dataclasses.dataclass
class RoleDocumentation:
    entrypoints: Mapping[str, Documentation]


def _get_argspecs(root: t.Any) -> Mapping[str, t.Any] | None:
    if root is None:
        return None
    if not isinstance(root, Mapping):
        raise ValueError(f"Expected top-level mapping, got {type(root)}")
    argspecs = root.get("argument_specs")
    if argspecs is None:
        return None
    if not isinstance(argspecs, Mapping):
        raise ValueError(
            f"Expected argument_specs to be a mapping, got {type(argspecs)}"
        )
    return argspecs


def _extract_entrypoint(ep_data: Mapping[str, t.Any]) -> Documentation:
    documentation = dict(ep_data)
    raw_examples = documentation.pop("examples", None)
    examples: str | None = None
    example_format: str = "yaml"
    ex = _extract_examples(raw_examples)
    if ex is not None:
        examples, example_format = ex
    return Documentation(
        documentation=documentation,
        return_values=None,
        examples=examples,
        example_format=example_format,
    )


def load_docs_from_role_argspec_contents(
    contents: str, *, path: Path | None = None  # pylint: disable=unused-argument
) -> RoleDocumentation | None:
    """
    Load role documentation from role argument spec's contents.
    """
    try:
        root = _load_yaml_data(contents)
    except Exception as exc:
        raise ValueError(f"Error while parsing: {exc}") from exc
    argspecs = _get_argspecs(root)
    if argspecs is None:
        return None

    entrypoints: dict[str, Documentation] = {}
    for entrypoint, ep_data in argspecs.items():
        if ep_data is None:
            continue
        if not isinstance(ep_data, Mapping):
            raise ValueError(
                f"Expected argument_specs.{entrypoint} to be a mapping, got {type(ep_data)}"
            )
        try:
            entrypoints[entrypoint] = _extract_entrypoint(ep_data)
        except ValueError as exc:
            raise ValueError(
                f"Error while parsing entrypoint {entrypoint}: {exc}"
            ) from exc

    return RoleDocumentation(entrypoints=entrypoints)


def load_docs_from_role_argspec_file(path: Path) -> RoleDocumentation | None:
    """
    Load role documentation from a role argument spec.
    """
    try:
        with path.open("rt", encoding="utf-8") as f:
            data = f.read()
    except Exception as exc:
        raise ValueError(f"Error while reading {path}: {exc}") from exc
    try:
        return load_docs_from_role_argspec_contents(data, path=path)
    except Exception as exc:
        raise ValueError(f"Error while parsing {path}: {exc}") from exc


@dataclasses.dataclass
class DocumentationFragment:
    data: Mapping[str, t.Any]


@dataclasses.dataclass
class DocumentationFragments:
    fragments: Mapping[str, DocumentationFragment]


def load_docs_from_python_doc_fragment_contents(
    contents: str, *, path: Path | None = None
) -> DocumentationFragments | None:
    """
    Load documentation from a Python doc fragment.

    Does not support modules or plugins!
    """
    root = _parse(contents, path=path)

    for child in root.body:
        # We look for top-level classes named ``ModuleDocFragment``.
        if not isinstance(child, ast.ClassDef) or child.name != "ModuleDocFragment":
            continue
        fragments: dict[str, DocumentationFragment] = {}
        for fragment in child.body:
            if not isinstance(fragment, ast.Assign):
                continue
            for _constant, data, fragment_name in _iterate_targets(fragment):
                try:
                    parsed_data = _load_yaml_data(data)
                except Exception as exc:
                    raise ValueError(
                        f"Error while parsing fragment {fragment_name}: {exc}"
                    ) from exc
                if parsed_data is None:
                    parsed_data = {}
                if not isinstance(parsed_data, Mapping):
                    raise ValueError(
                        f"Fragment {fragment_name} is not a mapping, but {type(parsed_data)}"
                    )
                fragments[fragment_name] = DocumentationFragment(data=parsed_data)
        return DocumentationFragments(fragments=fragments)

    return None


def load_docs_from_python_doc_fragment_file(
    path: Path,
) -> DocumentationFragments | None:
    """
    Load documentation from a Python doc fragment.

    Does not support modules or plugins!
    """
    try:
        with path.open("rt", encoding="utf-8") as f:
            contents = f.read()
    except Exception as exc:
        raise ValueError(f"Error while reading {path}: {exc}") from exc
    try:
        return load_docs_from_python_doc_fragment_contents(contents, path=path)
    except Exception as exc:
        raise ValueError(f"Error while parsing {path}: {exc}") from exc


__all__ = (
    "load_collection_info",
    "Documentation",
    "load_docs_from_python_contents",
    "load_docs_from_python_file",
    "load_docs_from_yaml_contents",
    "load_docs_from_yaml_file",
    "load_docs",
    "RoleDocumentation",
    "load_docs_from_role_argspec_contents",
    "load_docs_from_role_argspec_file",
    "DocumentationFragment",
    "DocumentationFragments",
    "load_docs_from_python_doc_fragment_contents",
    "load_docs_from_python_doc_fragment_file",
)
