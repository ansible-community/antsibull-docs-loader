# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt
# or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026, Ansible Project

"""
Test YAML loading.
"""

from __future__ import annotations

import typing as t
from pathlib import Path

import pytest  # pylint: disable=import-error
import yaml

from antsibull_docs_loader._yaml import load_yaml_data, load_yaml_file

ANSIBLE_TAGS: list[tuple[str, t.Any]] = [
    # !unsafe only marks a value as not templatable, which does not matter here.
    ('key: !unsafe "{{ foo }}"', "{{ foo }}"),
    (
        "key: !unsafe \"[{name: '{{.Comm}}', cmdline: [.+]}]\"",
        "[{name: '{{.Comm}}', cmdline: [.+]}]",
    ),
    ("key: !unsafe", None),
    ('key: !unsafe {subkey: "{{ foo }}"}', {"subkey": "{{ foo }}"}),
    ('key: !unsafe ["{{ foo }}", 2]', ["{{ foo }}", 2]),
    # Implicit resolution is repeated for tagged values, the same way that
    # ansible-core does it.
    ("key: !unsafe 42", 42),
    ('key: !unsafe "42"', 42),
    # Vaulted values are kept as their ciphertext and are never decrypted.
    (
        "key: !vault |\n  $ANSIBLE_VAULT;1.1;AES256\n  36383832626334\n",
        "$ANSIBLE_VAULT;1.1;AES256\n36383832626334\n",
    ),
    (
        "key: !vault-encrypted |\n  $ANSIBLE_VAULT;1.1;AES256\n  36383832626334\n",
        "$ANSIBLE_VAULT;1.1;AES256\n36383832626334\n",
    ),
    # Legacy aliases which ansible-core maps as well.
    ('key: !!python/unicode "foo"', "foo"),
    ("key: !!python/dict {subkey: 1}", {"subkey": 1}),
]

STANDARD_TAGS: list[tuple[str, t.Any]] = [
    ("key: foo", "foo"),
    ("key: 1.5", 1.5),
    ('key: !!int "42"', 42),
    ('key: !!str "42"', "42"),
    ('key: !!bool "yes"', True),
    ("key: !!set {foo, bar}", {"foo", "bar"}),
]


@pytest.mark.parametrize("yaml_data, expected", ANSIBLE_TAGS + STANDARD_TAGS)
def test_load_yaml_data_tags(yaml_data: str, expected: t.Any) -> None:
    assert load_yaml_data(yaml_data) == {"key": expected}


@pytest.mark.parametrize("yaml_data, expected", ANSIBLE_TAGS)
def test_load_yaml_file_tags(tmp_path: Path, yaml_data: str, expected: t.Any) -> None:
    path = tmp_path / "test.yml"
    path.write_text(yaml_data, encoding="utf-8")
    assert load_yaml_file(path) == {"key": expected}


def test_load_yaml_data_unknown_tag() -> None:
    with pytest.raises(yaml.YAMLError):
        load_yaml_data('key: !this_tag_does_not_exist "foo"')


@pytest.mark.parametrize("yaml_data", [yaml_data for yaml_data, _ in ANSIBLE_TAGS])
def test_ansible_tags_are_not_registered_globally(yaml_data: str) -> None:
    # The constructors must be registered on our own loader class, so that
    # other users of PyYAML in the same process are not affected.
    with pytest.raises(yaml.YAMLError):
        yaml.load(yaml_data, Loader=yaml.SafeLoader)
