"""Generate dhcp file."""
from __future__ import annotations

import pprint
import re

from .model import Config, Integration

BASE = """
\"\"\"Automatically generated by hassfest.

To update, run python3 -m script.hassfest
\"\"\"
from __future__ import annotations

# fmt: off

DHCP: list[dict[str, str | bool]] = {}
""".strip()


def generate_and_validate(integrations: list[dict[str, str]]):
    """Validate and generate dhcp data."""
    match_list = []

    for domain in sorted(integrations):
        integration = integrations[domain]

        if not integration.manifest or not integration.config_flow:
            continue

        match_types = integration.manifest.get("dhcp", [])

        if not match_types:
            continue

        for entry in match_types:
            match_list.append({"domain": domain, **entry})

    # JSON will format `True` as `true`
    # re.sub for flake8 E128
    formatted = pprint.pformat(match_list)
    formatted_aligned_continuation = re.sub(r"^\[\{", "[\n {", formatted)
    formatted_align_indent = re.sub(
        r"(?m)^ ", "    ", formatted_aligned_continuation, flags=re.MULTILINE, count=0
    )
    return BASE.format(formatted_align_indent)


def validate(integrations: dict[str, Integration], config: Config):
    """Validate dhcp file."""
    dhcp_path = config.root / "homeassistant/generated/dhcp.py"
    config.cache["dhcp"] = content = generate_and_validate(integrations)

    if config.specific_integrations:
        return

    with open(str(dhcp_path)) as fp:
        current = fp.read().strip()
        if current != content:
            config.add_error(
                "dhcp",
                "File dhcp.py is not up to date. Run python3 -m script.hassfest",
                fixable=True,
            )
        return


def generate(integrations: dict[str, Integration], config: Config):
    """Generate dhcp file."""
    dhcp_path = config.root / "homeassistant/generated/dhcp.py"
    with open(str(dhcp_path), "w") as fp:
        fp.write(f"{config.cache['dhcp']}\n")
