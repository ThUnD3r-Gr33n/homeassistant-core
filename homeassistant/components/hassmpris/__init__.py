"""The MPRIS media playback remote control integration."""
from __future__ import annotations

import datetime
from typing import List

from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509 import Certificate, load_pem_x509_certificate
import hassmpris_client

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from .const import (
    CONF_CLIENT_CERT,
    CONF_CLIENT_KEY,
    CONF_TRUST_CHAIN,
    DOMAIN,
    ENTRY_CLIENT,
    ENTRY_MANAGER,
    LOGGER as _LOGGER,
)

MIN_TIME_BETWEEN_UPDATES = datetime.timedelta(seconds=5)
PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]


def _load_cert_chain(c: bytes) -> list[Certificate]:
    start_line = b"-----BEGIN CERTIFICATE-----"
    cert_slots = c.split(start_line)
    certificates: list[Certificate] = []
    for single_pem_cert in cert_slots[1:]:
        loaded = load_pem_x509_certificate(start_line + single_pem_cert)
        certificates.append(loaded)
    return certificates


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MPRIS media playback remote control from a config entry."""
    client_cert = load_pem_x509_certificate(
        entry.data[CONF_CLIENT_CERT].encode("ascii"),
    )
    client_key = load_pem_private_key(
        entry.data[CONF_CLIENT_KEY].encode("ascii"),
        None,
    )
    trust_chain = _load_cert_chain(
        entry.data[CONF_TRUST_CHAIN].encode("ascii"),
    )

    c = hassmpris_client.AsyncMPRISClient(
        entry.data[CONF_HOST],
        40051,
        client_cert,
        client_key,
        trust_chain,
    )
    try:
        _LOGGER.debug("Pinging the server")
        await c.ping()
        _LOGGER.debug("Successfully pinged the server")

    except hassmpris_client.Unauthenticated as e:
        raise ConfigEntryAuthFailed(e)
    except Exception as e:
        _LOGGER.exception("Cannot ping the server")
        raise ConfigEntryNotReady(str(e))

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        ENTRY_CLIENT: c,
    }

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        data = hass.data[DOMAIN].pop(entry.entry_id)
        if ENTRY_MANAGER in data:
            _LOGGER.debug("Stopping entity manager.")
            waitable = data[ENTRY_MANAGER].stop()
        await data[ENTRY_CLIENT].close()
        if ENTRY_MANAGER in data:
            _LOGGER.debug("Waiting for entity manager to fully stop.")
            await waitable

    return unload_ok
