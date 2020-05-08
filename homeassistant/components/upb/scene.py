"""Platform for UPB link integration."""
from homeassistant.components.scene import Scene
from homeassistant.helpers import entity_platform

from . import UpbEntity
from .const import DOMAIN, UPB_BLINK_RATE_SCHEMA, UPB_BRIGHTNESS_RATE_SCHEMA

ATTR_BLINK_RATE = "blink_rate"
SERVICE_LINK_ACTIVATE = "link_activate"
SERVICE_LINK_DEACTIVATE = "link_deactivate"
SERVICE_LINK_FADE_STOP = "link_fade_stop"
SERVICE_LINK_GOTO = "link_goto"
SERVICE_LINK_FADE_START = "link_fade_start"
SERVICE_LINK_BLINK = "link_blink"

UPB_COMMAND_TO_EVENT_MAPPING = {
    "goto": "goto",
    "activate": "activated",
    "deactivate": "deactivated",
    "blink": "blink",
    "fade_start": "fade_started",
    "fade_stop": "fade_stopped",
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the UPB link based on a config entry."""
    upb = hass.data[DOMAIN][config_entry.entry_id]["upb"]
    unique_id = config_entry.entry_id
    async_add_entities(UpbLink(upb.links[link], unique_id, upb) for link in upb.links)

    platform = entity_platform.current_platform.get()

    platform.async_register_entity_service(
        SERVICE_LINK_ACTIVATE, {}, "async_link_activate"
    )
    platform.async_register_entity_service(
        SERVICE_LINK_DEACTIVATE, {}, "async_link_deactivate"
    )
    platform.async_register_entity_service(
        SERVICE_LINK_FADE_STOP, {}, "async_link_fade_stop"
    )
    platform.async_register_entity_service(
        SERVICE_LINK_GOTO, UPB_BRIGHTNESS_RATE_SCHEMA, "async_link_goto"
    )
    platform.async_register_entity_service(
        SERVICE_LINK_FADE_START, UPB_BRIGHTNESS_RATE_SCHEMA, "async_link_fade_start"
    )
    platform.async_register_entity_service(
        SERVICE_LINK_BLINK, UPB_BLINK_RATE_SCHEMA, "async_link_blink"
    )


class UpbLink(UpbEntity, Scene):
    """Representation of an UPB Link."""

    def __init__(self, element, unique_id, upb):
        """Initialize an UpbLink."""
        super().__init__(element, unique_id, upb)

    def _element_changed(self, element, changeset):
        if changeset.get("last_change") is None:
            return

        command = changeset["last_change"]["command"]
        event = f"{DOMAIN}_scene_{UPB_COMMAND_TO_EVENT_MAPPING[command]}"
        data = {"entity_id": self.entity_id}
        if command == "goto" or command == "fade_start":
            data["brightness_pct"] = changeset["last_change"]["level"]
        rate = changeset["last_change"].get("rate")
        if rate:
            data["rate"] = rate

        self.hass.bus.fire(event, data)

    async def async_activate(self):
        """Activate the task."""
        self._element.activate()

    async def async_link_activate(self):
        """Activate the task."""
        self._element.activate()

    async def async_link_deactivate(self):
        """Activate the task."""
        self._element.deactivate()

    async def async_link_goto(self, rate, brightness=None, brightness_pct=None):
        """Activate the task."""
        if brightness:
            brightness_pct = brightness / 2.55
        self._element.goto(brightness_pct, rate)

    async def async_link_fade_start(self, rate, brightness=None, brightness_pct=None):
        """Start dimming a link."""
        if brightness:
            brightness_pct = brightness / 2.55
        self._element.fade_start(brightness_pct, rate)

    async def async_link_fade_stop(self):
        """Stop dimming a link."""
        self._element.fade_stop()

    async def async_link_blink(self, blink_rate):
        """Blink a link."""
        blink_rate = int(blink_rate * 60)
        self._element.blink(blink_rate)
