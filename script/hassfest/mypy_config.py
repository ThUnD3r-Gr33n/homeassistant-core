"""Generate mypy config."""
from __future__ import annotations

from collections.abc import Iterable
import configparser
import io
import os
from pathlib import Path
from typing import Final

from homeassistant.const import REQUIRED_PYTHON_VER

from .model import Config, Integration

# Component modules which should set no_implicit_reexport = true.
NO_IMPLICIT_REEXPORT_MODULES: set[str] = {
    "homeassistant.components",
    "homeassistant.components.application_credentials.*",
    "homeassistant.components.diagnostics.*",
    "homeassistant.components.spotify.*",
    "homeassistant.components.stream.*",
    "homeassistant.components.update.*",
}

HEADER: Final = """
# Automatically generated by hassfest.
#
# To update, run python3 -m script.hassfest -p mypy_config

""".lstrip()

GENERAL_SETTINGS: Final[dict[str, str]] = {
    "python_version": ".".join(str(x) for x in REQUIRED_PYTHON_VER[:2]),
    "plugins": ", ".join(["pydantic.mypy"]),
    "show_error_codes": "true",
    "follow_imports": "silent",
    # Enable some checks globally.
    "local_partial_types": "true",
    "strict_equality": "true",
    "no_implicit_optional": "true",
    "warn_incomplete_stub": "true",
    "warn_redundant_casts": "true",
    "warn_unused_configs": "true",
    "warn_unused_ignores": "true",
    "enable_error_code": ", ".join(
        [
            "ignore-without-code",
            "redundant-self",
            "truthy-iterable",
        ]
    ),
    "disable_error_code": ", ".join(
        [
            "annotation-unchecked",
            "import-not-found",
            "import-untyped",
        ]
    ),
    # Impractical in real code
    # E.g. this breaks passthrough ParamSpec typing with Concatenate
    "extra_checks": "false",
}

# This is basically the list of checks which is enabled for "strict=true".
# "strict=false" in config files does not turn strict settings off if they've been
# set in a more general section (it instead means as if strict was not specified at
# all), so we need to list all checks manually to be able to flip them wholesale.
STRICT_SETTINGS: Final[list[str]] = [
    "check_untyped_defs",
    "disallow_incomplete_defs",
    "disallow_subclassing_any",
    "disallow_untyped_calls",
    "disallow_untyped_decorators",
    "disallow_untyped_defs",
    "warn_return_any",
    "warn_unreachable",
    # TODO: turn these on, address issues
    # "disallow_any_generics",
    # "no_implicit_reexport",
]

# Strict settings are already applied for core files.
# To enable granular typing, add additional settings if core files are given.
STRICT_SETTINGS_CORE: Final[list[str]] = [
    "disallow_any_generics",
]

# Plugin specific settings
# Bump mypy cache when updating! Some plugins don't invalidate the cache properly.
# pydantic: https://docs.pydantic.dev/mypy_plugin/#plugin-settings
PLUGIN_CONFIG: Final[dict[str, dict[str, str]]] = {
    "pydantic-mypy": {
        "init_forbid_extra": "true",
        "init_typed": "true",
        "warn_required_dynamic_aliases": "true",
        "warn_untyped_fields": "true",
    }
}


def _sort_within_sections(line_iter: Iterable[str]) -> Iterable[str]:
    """Sort lines within sections.

    Sections are defined as anything not delimited by a blank line
    or an octothorpe-prefixed comment line.
    """
    section: list[str] = []
    for line in line_iter:
        if line.startswith("#") or not line.strip():
            yield from sorted(section)
            section.clear()
            yield line
            continue
        section.append(line)
    yield from sorted(section)


def _get_strict_typing_path(config: Config) -> Path:
    return config.root / ".strict-typing"


def _get_mypy_ini_path(config: Config) -> Path:
    return config.root / "mypy.ini"


def _generate_and_validate_strict_typing(config: Config) -> str:
    """Validate and generate strict_typing."""
    lines = [
        line.strip()
        for line in _get_strict_typing_path(config).read_text().splitlines()
    ]
    return "\n".join(_sort_within_sections(lines)) + "\n"


def _generate_and_validate_mypy_config(config: Config) -> str:
    """Validate and generate mypy config."""

    # Filter empty and commented lines.
    parsed_modules: list[str] = [
        line.strip()
        for line in config.cache["strict_typing"].splitlines()
        if line.strip() != "" and not line.startswith("#")
    ]

    strict_modules: list[str] = []
    strict_core_modules: list[str] = []
    for module in parsed_modules:
        if module.startswith("homeassistant.components"):
            strict_modules.append(module)
        else:
            strict_core_modules.append(module)

    # Validate that all modules exist.
    all_modules = (
        strict_modules + strict_core_modules + list(NO_IMPLICIT_REEXPORT_MODULES)
    )
    for module in all_modules:
        if module.endswith(".*"):
            module_path = Path(module[:-2].replace(".", os.path.sep))
            if not module_path.is_dir():
                config.add_error("mypy_config", f"Module '{module} is not a folder")
        else:
            module = module.replace(".", os.path.sep)
            module_path = Path(f"{module}.py")
            if module_path.is_file():
                continue
            module_path = Path(module) / "__init__.py"
            if not module_path.is_file():
                config.add_error("mypy_config", f"Module '{module} doesn't exist")

    # Don't generate mypy.ini if there're errors found because it will likely crash.
    if any(err.plugin == "mypy_config" for err in config.errors):
        return ""

    mypy_config = configparser.ConfigParser()

    general_section = "mypy"
    mypy_config.add_section(general_section)
    for key, value in GENERAL_SETTINGS.items():
        mypy_config.set(general_section, key, value)
    for key in STRICT_SETTINGS:
        mypy_config.set(general_section, key, "true")

    for plugin_name, plugin_config in PLUGIN_CONFIG.items():
        if not plugin_config:
            continue
        mypy_config.add_section(plugin_name)
        for key, value in plugin_config.items():
            mypy_config.set(plugin_name, key, value)

    # By default enable no_implicit_reexport only for homeassistant.*
    # Disable it afterwards for all components
    components_section = "mypy-homeassistant.*"
    mypy_config.add_section(components_section)
    mypy_config.set(components_section, "no_implicit_reexport", "true")

    for core_module in strict_core_modules:
        core_section = f"mypy-{core_module}"
        mypy_config.add_section(core_section)
        for key in STRICT_SETTINGS_CORE:
            mypy_config.set(core_section, key, "true")

    # By default strict checks are disabled for components.
    components_section = "mypy-homeassistant.components.*"
    mypy_config.add_section(components_section)
    for key in STRICT_SETTINGS:
        mypy_config.set(components_section, key, "false")
    mypy_config.set(components_section, "no_implicit_reexport", "false")

    for strict_module in strict_modules:
        strict_section = f"mypy-{strict_module}"
        mypy_config.add_section(strict_section)
        for key in STRICT_SETTINGS:
            mypy_config.set(strict_section, key, "true")
        if strict_module in NO_IMPLICIT_REEXPORT_MODULES:
            mypy_config.set(strict_section, "no_implicit_reexport", "true")

    for reexport_module in sorted(
        NO_IMPLICIT_REEXPORT_MODULES.difference(strict_modules)
    ):
        reexport_section = f"mypy-{reexport_module}"
        mypy_config.add_section(reexport_section)
        mypy_config.set(reexport_section, "no_implicit_reexport", "true")

    # Disable strict checks for tests
    tests_section = "mypy-tests.*"
    mypy_config.add_section(tests_section)
    for key in STRICT_SETTINGS:
        mypy_config.set(tests_section, key, "false")

    with io.StringIO() as fp:
        mypy_config.write(fp)
        fp.seek(0)
        return f"{HEADER}{fp.read().strip()}\n"


def validate(integrations: dict[str, Integration], config: Config) -> None:
    """Validate strict_typing and mypy config."""
    strict_typing_content = _generate_and_validate_strict_typing(config)
    config.cache["strict_typing"] = strict_typing_content

    mypy_content = _generate_and_validate_mypy_config(config)
    config.cache["mypy_config"] = mypy_content

    if any(err.plugin == "mypy_config" for err in config.errors):
        return

    if _get_strict_typing_path(config).read_text() != strict_typing_content:
        config.add_error(
            "mypy_config",
            "File .strict_typing is not up to date. Run python3 -m script.hassfest",
            fixable=True,
        )

    if _get_mypy_ini_path(config).read_text() != mypy_content:
        config.add_error(
            "mypy_config",
            "File mypy.ini is not up to date. Run python3 -m script.hassfest",
            fixable=True,
        )


def generate(integrations: dict[str, Integration], config: Config) -> None:
    """Generate strict_typing and mypy config."""
    _get_mypy_ini_path(config).write_text(config.cache["mypy_config"])
    _get_strict_typing_path(config).write_text(config.cache["strict_typing"])
