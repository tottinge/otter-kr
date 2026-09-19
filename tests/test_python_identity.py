from pathlib import Path

from otter_kr.python_identity import identifier_words, module_name


def test_identifier_words_share_one_camel_and_separator_rule() -> None:
    assert identifier_words("HTTPServer-error") == ("http", "server", "error")


def test_module_name_handles_packages_and_modules() -> None:
    assert module_name(Path("pkg/__init__.py")) == "pkg"
    assert module_name(Path("pkg/service.py")) == "pkg.service"
