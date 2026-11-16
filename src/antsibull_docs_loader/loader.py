# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or
# https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Data loader.
"""

from __future__ import annotations

import ast
import re
import typing as t
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from ._yaml import format_yaml as _format_yaml
from ._yaml import load_yaml_data as _load_yaml_data
from ._yaml import load_yaml_file as _load_yaml_file
from .data import CollectionInfo
from .documentation import (
    Documentation,
    DocumentationFragment,
    DocumentationFragments,
    RoleDocumentation,
)

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
) -> t.Generator[tuple[ast.expr, str]]:
    for target in assignment.targets:
        if isinstance(target, ast.Name):
            yield assignment.value, target.id


def _str_constant(expression: ast.expr) -> str | None:
    if not isinstance(expression, ast.Constant):
        return None
    if not isinstance(expression.value, str):
        return None
    return expression.value


def _iterate_constant_string_assign_targets(
    assignment: ast.Assign,
) -> t.Generator[tuple[ast.Constant, str, str]]:
    value = _str_constant(assignment.value)
    if value is None:
        return
    assert isinstance(assignment.value, ast.Constant)  # guaranteed by _str_constant
    for target in assignment.targets:
        if isinstance(target, ast.Name):
            yield assignment.value, value, target.id


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
        for _constant, data, section in _iterate_constant_string_assign_targets(child):
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
) -> dict[str, t.Any] | None:
    data = root.get(section)
    if data is None:
        return data
    if not isinstance(data, dict):
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
    documentation: dict[str, t.Any] | None = _extract_yaml_section(
        root, DOCUMENTATION_SECTION
    )
    return_values: dict[str, t.Any] | None = _extract_yaml_section(root, RETURN_SECTION)
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
            for (
                _constant,
                data,
                fragment_name,
            ) in _iterate_constant_string_assign_targets(fragment):
                try:
                    parsed_data = _load_yaml_data(data)
                except Exception as exc:
                    raise ValueError(
                        f"Error while parsing fragment {fragment_name}: {exc}"
                    ) from exc
                if parsed_data is None:
                    parsed_data = {}
                if not isinstance(parsed_data, dict):
                    raise ValueError(
                        f"Fragment {fragment_name} is not a mapping, but {type(parsed_data)}"
                    )
                fragments[fragment_name] = DocumentationFragment(
                    data=parsed_data, return_data=parsed_data
                )
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


def _get_known(
    expression: ast.expr,
    *,
    self_name: str | None,
    known: dict[str, dict[str, t.Any]],
    self_known: dict[str, dict[str, t.Any]],
) -> dict[str, t.Any] | None:
    # Check for <known>
    if isinstance(expression, ast.Name):
        return known.get(expression.id)
    # Check for self.<known>
    if (
        self_name is None
        or not isinstance(expression, ast.Attribute)
        or not isinstance(expression.value, ast.Name)
        or expression.value.id != self_name
    ):
        return None
    return self_known.get(expression.attr)


def _evaluate_dict_literal(
    value: ast.Dict,
    *,
    self_name: str | None,
    known: dict[str, dict[str, t.Any]],
    self_known: dict[str, dict[str, t.Any]],
) -> dict[str, t.Any] | None:
    result = {}
    for k, v in zip(value.keys, value.values):
        if k is None:
            known_value = _get_known(
                v, self_name=self_name, known=known, self_known=self_known
            )
            if known_value is not None:
                result.update(known_value)
                continue
            return None
        kstr = _str_constant(k)
        if kstr is None:
            return None
        result[kstr] = v
    return result


def _evaluate_dict_call(
    value: ast.Call,
    *,
    self_name: str | None,
    known: dict[str, dict[str, t.Any]],
    self_known: dict[str, dict[str, t.Any]],
) -> dict[str, t.Any] | None:
    result = {}
    for kv in value.keywords:
        if kv.arg is not None:
            result[kv.arg] = kv.value
            continue
        known_value = _get_known(
            kv.value, self_name=self_name, known=known, self_known=self_known
        )
        if known_value is None:
            return None
        result.update(known_value)
    return result


def _get_dict_value(
    expression: ast.expr,
    *,
    self_name: str | None,
    known: dict[str, dict[str, t.Any]],
    self_known: dict[str, dict[str, t.Any]],
) -> dict[str, t.Any] | None:
    if isinstance(expression, ast.Dict):
        return _evaluate_dict_literal(
            expression, self_name=self_name, known=known, self_known=self_known
        )
    if (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Name)
        and expression.func.id == "dict"
        and not expression.args
    ):
        return _evaluate_dict_call(
            expression, self_name=self_name, known=known, self_known=self_known
        )
    return _get_known(
        expression,
        self_name=self_name,
        known=known,
        self_known=self_known,
    )


def _get_dict_assignments(
    node: Iterable[ast.stmt],
    *,
    self_name: str | None,
    known: dict[str, dict[str, t.Any]],
    self_known: dict[str, dict[str, t.Any]],
) -> dict[str, dict[str, t.Any]]:
    """
    Find all assignments ``x = {...}`` where the dict literal keys are strings.
    """
    result: dict[str, dict[str, t.Any]] = {}
    current_known = known.copy()
    for child in node:
        if not isinstance(child, ast.Assign):
            continue
        entry = _get_dict_value(
            child.value, self_name=self_name, known=current_known, self_known=self_known
        )
        if entry is not None:
            for _, name in _iterate_targets(child):
                result[name] = entry
                current_known[name] = entry
    return result


def _has_staticmethod(fdef: ast.FunctionDef) -> bool:
    for decorator in fdef.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "staticmethod":
            return True
    return False


def _get_self_name(method: ast.FunctionDef) -> str | None:
    if _has_staticmethod(method):
        return None
    args = method.args.posonlyargs + method.args.args
    if not args:
        return None
    return args[0].arg


# ast.TryStar ('except*' syntax for handling ``ExceptionGroup``s) has been added in Python 3.11
try:
    _TRY: tuple[type[ast.Try], ...] = (ast.Try, ast.TryStar)  # type: ignore[assignment]
except AttributeError:
    _TRY = (ast.Try,)


def _get_returns(statements: Sequence[ast.stmt]) -> t.Generator[ast.Return]:
    for statement in statements:
        if isinstance(statement, ast.Return):
            yield statement
        if isinstance(statement, (ast.For, ast.While, ast.If)):
            yield from _get_returns(statement.body)
            yield from _get_returns(statement.orelse)
        if isinstance(statement, ast.With):
            yield from _get_returns(statement.body)
        if isinstance(statement, _TRY):
            yield from _get_returns(statement.body)
            for handler in statement.handlers:
                yield from _get_returns(handler.body)
            yield from _get_returns(statement.orelse)
            yield from _get_returns(statement.finalbody)


def load_plugin_list_from_jinja2_plugin_contents(
    contents: str,
    *,
    path: Path | None = None,
    class_name: str,
    method_name: str,
) -> set[str] | None:
    """
    Load the list of Jinja2 plugins from a filter or test plugin Python file's contents.
    """
    root = _parse(contents, path=path)

    top_level_assignments = _get_dict_assignments(
        root.body, self_name=None, known={}, self_known={}
    )

    for child in root.body:
        # We look for top-level classes named ``class_name``.
        if not isinstance(child, ast.ClassDef) or child.name != class_name:
            continue
        class_assignments = _get_dict_assignments(
            child.body, self_name=None, known=top_level_assignments, self_known={}
        )
        for elt in child.body:
            if not isinstance(elt, ast.FunctionDef) or elt.name != method_name:
                continue
            self_name = _get_self_name(elt) or class_name
            method_assignments = _get_dict_assignments(
                elt.body,
                self_name=self_name,
                known=top_level_assignments,
                self_known=class_assignments,
            )
            candidate: set[str] | None = None
            assignments = dict(top_level_assignments)
            assignments.update(method_assignments)
            for return_stmt in _get_returns(elt.body):
                if return_stmt.value is None:
                    return None
                value = _get_dict_value(
                    return_stmt.value,
                    self_name=self_name,
                    known=assignments,
                    self_known=class_assignments,
                )
                if value is None:
                    continue
                if candidate is None:
                    candidate = set(value)
                else:
                    candidate.update(value)
            return candidate

    return None


def load_plugin_list_from_jinja2_plugin_file(
    path: Path,
    *,
    class_name: str,
    method_name: str,
) -> set[str] | None:
    """
    Load the list of Jinja2 plugins from a filter or test plugin Python file.
    """
    try:
        with path.open("rt", encoding="utf-8") as f:
            contents = f.read()
    except Exception as exc:
        raise ValueError(f"Error while reading {path}: {exc}") from exc
    try:
        return load_plugin_list_from_jinja2_plugin_contents(
            contents,
            path=path,
            class_name=class_name,
            method_name=method_name,
        )
    except Exception as exc:
        raise ValueError(f"Error while parsing {path}: {exc}") from exc


__all__ = (
    "load_collection_info",
    "load_docs_from_python_contents",
    "load_docs_from_python_file",
    "load_docs_from_yaml_contents",
    "load_docs_from_yaml_file",
    "load_docs",
    "load_docs_from_role_argspec_contents",
    "load_docs_from_role_argspec_file",
    "load_docs_from_python_doc_fragment_contents",
    "load_docs_from_python_doc_fragment_file",
    "load_plugin_list_from_jinja2_plugin_contents",
    "load_plugin_list_from_jinja2_plugin_file",
)
