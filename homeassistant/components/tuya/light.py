"""Support for the Tuya lights."""
from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Any

from tuya_iot import TuyaDevice, TuyaDeviceManager

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    COLOR_MODE_BRIGHTNESS,
    COLOR_MODE_COLOR_TEMP,
    COLOR_MODE_HS,
    COLOR_MODE_ONOFF,
    SUPPORT_EFFECT,
    LightEntity,
    LightEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomeAssistantTuyaData
from .base import IntegerTypeData, TuyaEntity
from .const import DOMAIN, TUYA_DISCOVERY_NEW, DPCode, WorkMode

_LOGGER = logging.getLogger(__name__)


@dataclass
class TuyaLightEntityDescription(LightEntityDescription):
    """Describe an Tuya light entity."""

    color_mode: DPCode | None = None
    brightness: DPCode | tuple[DPCode, ...] | None = None
    color_temp: DPCode | tuple[DPCode, ...] | None = None
    color_data: DPCode | tuple[DPCode, ...] | None = None
    scene_data: DPCode | tuple[DPCode, ...] | None = None


LIGHTS: dict[str, tuple[TuyaLightEntityDescription, ...]] = {
    # String Lights
    # https://developer.tuya.com/en/docs/iot/dc?id=Kaof7taxmvadu
    "dc": (
        TuyaLightEntityDescription(
            key=DPCode.SWITCH_LED,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color_temp=DPCode.TEMP_VALUE,
            color_data=DPCode.COLOUR_DATA,
        ),
    ),
    # Strip Lights
    # https://developer.tuya.com/en/docs/iot/dd?id=Kaof804aibg2l
    "dd": (
        TuyaLightEntityDescription(
            key=DPCode.SWITCH_LED,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color_temp=DPCode.TEMP_VALUE,
            color_data=DPCode.COLOUR_DATA,
        ),
    ),
    # Light
    # https://developer.tuya.com/en/docs/iot/categorydj?id=Kaiuyzy3eheyy
    "dj": (
        TuyaLightEntityDescription(
            key=DPCode.SWITCH_LED,
            color_mode=DPCode.WORK_MODE,
            brightness=(DPCode.BRIGHT_VALUE_V2, DPCode.BRIGHT_VALUE),
            color_temp=(DPCode.TEMP_VALUE_V2, DPCode.TEMP_VALUE),
            color_data=(DPCode.COLOUR_DATA_V2, DPCode.COLOUR_DATA),
            scene_data=DPCode.SCENE_DATA_V2,
        ),
    ),
    # Ceiling Fan Light
    # https://developer.tuya.com/en/docs/iot/fsd?id=Kaof8eiei4c2v
    "fsd": (
        TuyaLightEntityDescription(
            key=DPCode.SWITCH_LED,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color_temp=DPCode.TEMP_VALUE,
            color_data=DPCode.COLOUR_DATA,
        ),
    ),
    # Ambient Light
    # https://developer.tuya.com/en/docs/iot/ambient-light?id=Kaiuz06amhe6g
    "fwd": (
        TuyaLightEntityDescription(
            key=DPCode.SWITCH_LED,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color_temp=DPCode.TEMP_VALUE,
            color_data=DPCode.COLOUR_DATA,
        ),
    ),
    # Motion Sensor Light
    # https://developer.tuya.com/en/docs/iot/gyd?id=Kaof8a8hycfmy
    "gyd": (
        TuyaLightEntityDescription(
            key=DPCode.SWITCH_LED,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color_temp=DPCode.TEMP_VALUE,
            color_data=DPCode.COLOUR_DATA,
        ),
    ),
    # Switch
    # https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
    "kg": (
        TuyaLightEntityDescription(
            key=DPCode.SWITCH_BACKLIGHT,
            name="Backlight",
        ),
    ),
    # Dimmer Switch
    # https://developer.tuya.com/en/docs/iot/categorytgkg?id=Kaiuz0ktx7m0o
    "tgkg": (
        TuyaLightEntityDescription(
            key=DPCode.SWITCH_LED_1,
            name="Light",
            brightness=DPCode.BRIGHT_VALUE_1,
        ),
        TuyaLightEntityDescription(
            key=DPCode.SWITCH_LED_2,
            name="Light 2",
            brightness=DPCode.BRIGHT_VALUE_2,
        ),
        TuyaLightEntityDescription(
            key=DPCode.SWITCH_LED_3,
            name="Light 3",
            brightness=DPCode.BRIGHT_VALUE_3,
        ),
    ),
    # Dimmer
    # https://developer.tuya.com/en/docs/iot/tgq?id=Kaof8ke9il4k4
    "tgq": (
        TuyaLightEntityDescription(
            key=DPCode.SWITCH_LED_1,
            name="Light",
            brightness=DPCode.BRIGHT_VALUE_1,
        ),
        TuyaLightEntityDescription(
            key=DPCode.SWITCH_LED_2,
            name="Light 2",
            brightness=DPCode.BRIGHT_VALUE_2,
        ),
    ),
    # Solar Light
    # https://developer.tuya.com/en/docs/iot/tynd?id=Kaof8j02e1t98
    "tyndj": (
        TuyaLightEntityDescription(
            key=DPCode.SWITCH_LED,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color_temp=DPCode.TEMP_VALUE,
            color_data=DPCode.COLOUR_DATA,
        ),
    ),
    # Ceiling Light
    # https://developer.tuya.com/en/docs/iot/ceiling-light?id=Kaiuz03xxfc4r
    "xdd": (
        TuyaLightEntityDescription(
            key=DPCode.SWITCH_LED,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_VALUE,
            color_temp=DPCode.TEMP_VALUE,
            color_data=DPCode.COLOUR_DATA,
        ),
        TuyaLightEntityDescription(
            key=DPCode.SWITCH_NIGHT_LIGHT,
            name="Night Light",
        ),
    ),
    # Remote Control
    # https://developer.tuya.com/en/docs/iot/ykq?id=Kaof8ljn81aov
    "ykq": (
        TuyaLightEntityDescription(
            key=DPCode.SWITCH_CONTROLLER,
            color_mode=DPCode.WORK_MODE,
            brightness=DPCode.BRIGHT_CONTROLLER,
            color_temp=DPCode.TEMP_CONTROLLER,
        ),
    ),
}

# Socket (duplicate of `kg`)
# https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
LIGHTS["cz"] = LIGHTS["kg"]

# Power Socket (duplicate of `kg`)
# https://developer.tuya.com/en/docs/iot/s?id=K9gf7o5prgf7s
LIGHTS["pc"] = LIGHTS["kg"]


@dataclass
class ColorTypeData:
    """Color Type Data."""

    h_type: IntegerTypeData
    s_type: IntegerTypeData
    v_type: IntegerTypeData


DEFAULT_COLOR_TYPE_DATA = ColorTypeData(
    h_type=IntegerTypeData(min=1, scale=0, max=360, step=1),
    s_type=IntegerTypeData(min=1, scale=0, max=255, step=1),
    v_type=IntegerTypeData(min=1, scale=0, max=255, step=1),
)

DEFAULT_COLOR_TYPE_DATA_V2 = ColorTypeData(
    h_type=IntegerTypeData(min=1, scale=0, max=360, step=1),
    s_type=IntegerTypeData(min=1, scale=0, max=1000, step=1),
    v_type=IntegerTypeData(min=1, scale=0, max=1000, step=1),
)

DEFAULT_SCENE_DATA_V2 = {
    "Night": {
        "scene_num": 1,
        "scene_units": [
            {
                "bright": 200,
                "h": 0,
                "s": 0,
                "temperature": 0,
                "unit_change_mode": "static",
                "unit_gradient_duration": 13,
                "unit_switch_duration": 14,
                "v": 0,
            }
        ],
    },
    "Read": {
        "scene_num": 2,
        "scene_units": [
            {
                "bright": 1000,
                "h": 0,
                "s": 0,
                "temperature": 500,
                "unit_change_mode": "static",
                "unit_gradient_duration": 13,
                "unit_switch_duration": 14,
                "v": 0,
            }
        ],
    },
    "Meeting": {
        "scene_num": 3,
        "scene_units": [
            {
                "bright": 1000,
                "h": 0,
                "s": 0,
                "temperature": 1000,
                "unit_change_mode": "static",
                "unit_gradient_duration": 13,
                "unit_switch_duration": 14,
                "v": 0,
            }
        ],
    },
    "Leisure": {
        "scene_num": 4,
        "scene_units": [
            {
                "bright": 500,
                "h": 0,
                "s": 0,
                "temperature": 500,
                "unit_change_mode": "static",
                "unit_gradient_duration": 13,
                "unit_switch_duration": 14,
                "v": 0,
            }
        ],
    },
    "Soft": {
        "scene_num": 5,
        "scene_units": [
            {
                "bright": 0,
                "h": 120,
                "s": 1000,
                "temperature": 0,
                "unit_change_mode": "gradient",
                "unit_gradient_duration": 70,
                "unit_switch_duration": 70,
                "v": 1000,
            },
            {
                "bright": 0,
                "h": 120,
                "s": 1000,
                "temperature": 0,
                "unit_change_mode": "gradient",
                "unit_gradient_duration": 70,
                "unit_switch_duration": 70,
                "v": 10,
            },
        ],
    },
    "Rainbow": {
        "scene_num": 6,
        "scene_units": [
            {
                "bright": 0,
                "h": 0,
                "s": 1000,
                "temperature": 0,
                "unit_change_mode": "jump",
                "unit_gradient_duration": 70,
                "unit_switch_duration": 70,
                "v": 1000,
            },
            {
                "bright": 0,
                "h": 120,
                "s": 1000,
                "temperature": 0,
                "unit_change_mode": "jump",
                "unit_gradient_duration": 70,
                "unit_switch_duration": 70,
                "v": 1000,
            },
            {
                "bright": 0,
                "h": 240,
                "s": 1000,
                "temperature": 0,
                "unit_change_mode": "jump",
                "unit_gradient_duration": 70,
                "unit_switch_duration": 70,
                "v": 1000,
            },
        ],
    },
    "Shine": {
        "scene_num": 7,
        "scene_units": [
            {
                "bright": 0,
                "h": 0,
                "s": 1000,
                "temperature": 0,
                "unit_change_mode": "jump",
                "unit_gradient_duration": 70,
                "unit_switch_duration": 70,
                "v": 1000,
            },
            {
                "bright": 0,
                "h": 120,
                "s": 1000,
                "temperature": 0,
                "unit_change_mode": "jump",
                "unit_gradient_duration": 70,
                "unit_switch_duration": 70,
                "v": 1000,
            },
            {
                "bright": 0,
                "h": 240,
                "s": 1000,
                "temperature": 0,
                "unit_change_mode": "jump",
                "unit_gradient_duration": 70,
                "unit_switch_duration": 70,
                "v": 1000,
            },
        ],
    },
    "Beautiful": {
        "scene_num": 8,
        "scene_units": [
            {
                "bright": 0,
                "h": 0,
                "s": 1000,
                "temperature": 0,
                "unit_change_mode": "gradient",
                "unit_gradient_duration": 70,
                "unit_switch_duration": 70,
                "v": 1000,
            },
            {
                "bright": 0,
                "h": 120,
                "s": 1000,
                "temperature": 0,
                "unit_change_mode": "gradient",
                "unit_gradient_duration": 70,
                "unit_switch_duration": 70,
                "v": 1000,
            },
            {
                "bright": 0,
                "h": 240,
                "s": 1000,
                "temperature": 0,
                "unit_change_mode": "gradient",
                "unit_gradient_duration": 70,
                "unit_switch_duration": 70,
                "v": 1000,
            },
            {
                "bright": 0,
                "h": 61,
                "s": 1000,
                "temperature": 0,
                "unit_change_mode": "gradient",
                "unit_gradient_duration": 70,
                "unit_switch_duration": 70,
                "v": 1000,
            },
            {
                "bright": 0,
                "h": 174,
                "s": 1000,
                "temperature": 0,
                "unit_change_mode": "gradient",
                "unit_gradient_duration": 70,
                "unit_switch_duration": 70,
                "v": 1000,
            },
            {
                "bright": 0,
                "h": 275,
                "s": 1000,
                "temperature": 0,
                "unit_change_mode": "gradient",
                "unit_gradient_duration": 70,
                "unit_switch_duration": 70,
                "v": 1000,
            },
        ],
    },
}


@dataclass
class ColorData:
    """Color Data."""

    type_data: ColorTypeData
    h_value: int
    s_value: int
    v_value: int

    @property
    def hs_color(self) -> tuple[float, float]:
        """Get the HS value from this color data."""
        return (
            self.type_data.h_type.remap_value_to(self.h_value, 0, 360),
            self.type_data.s_type.remap_value_to(self.s_value, 0, 100),
        )

    @property
    def brightness(self) -> int:
        """Get the brightness value from this color data."""
        return round(self.type_data.v_type.remap_value_to(self.v_value, 0, 255))


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up tuya light dynamically through tuya discovery."""
    hass_data: HomeAssistantTuyaData = hass.data[DOMAIN][entry.entry_id]

    @callback
    def async_discover_device(device_ids: list[str]):
        """Discover and add a discovered tuya light."""
        entities: list[TuyaLightEntity] = []
        for device_id in device_ids:
            device = hass_data.device_manager.device_map[device_id]
            if descriptions := LIGHTS.get(device.category):
                for description in descriptions:
                    if (
                        description.key in device.function
                        or description.key in device.status
                    ):
                        entities.append(
                            TuyaLightEntity(
                                device, hass_data.device_manager, description
                            )
                        )

        async_add_entities(entities)

    async_discover_device([*hass_data.device_manager.device_map])

    entry.async_on_unload(
        async_dispatcher_connect(hass, TUYA_DISCOVERY_NEW, async_discover_device)
    )


class TuyaLightEntity(TuyaEntity, LightEntity):
    """Tuya light device."""

    entity_description: TuyaLightEntityDescription
    _brightness_dpcode: DPCode | None = None
    _brightness_type: IntegerTypeData | None = None
    _color_data_dpcode: DPCode | None = None
    _color_data_type: ColorTypeData | None = None
    _color_temp_dpcode: DPCode | None = None
    _color_temp_type: IntegerTypeData | None = None

    def __init__(
        self,
        device: TuyaDevice,
        device_manager: TuyaDeviceManager,
        description: TuyaLightEntityDescription,
    ) -> None:
        """Init TuyaHaLight."""
        super().__init__(device, device_manager)
        self.entity_description = description
        self._attr_unique_id = f"{super().unique_id}{description.key}"
        self._attr_supported_color_modes = {COLOR_MODE_ONOFF}

        # Determine brightness DPCodes
        if (
            isinstance(description.brightness, DPCode)
            and description.brightness in device.function
        ):
            self._brightness_dpcode = description.brightness
        elif isinstance(description.brightness, tuple):
            self._brightness_dpcode = next(
                (
                    dpcode
                    for dpcode in description.brightness
                    if dpcode in device.function
                ),
                None,
            )

        # Determine DPCodes for color temperature
        if (
            isinstance(description.color_temp, DPCode)
            and description.color_temp in device.function
        ):
            self._color_temp_dpcode = description.color_temp
        elif isinstance(description.color_temp, tuple):
            self._color_temp_dpcode = next(
                (
                    dpcode
                    for dpcode in description.color_temp
                    if dpcode in device.function
                ),
                None,
            )

        # Determine DPCodes for color data
        if (
            isinstance(description.color_data, DPCode)
            and description.color_data in device.function
        ):
            self._color_data_dpcode = description.color_data
        elif isinstance(description.color_data, tuple):
            self._color_data_dpcode = next(
                (
                    dpcode
                    for dpcode in description.color_data
                    if dpcode in device.function
                ),
                None,
            )
        # Determine DPCodes for scene's / effects
        if isinstance(description.scene_data, DPCode):
            self._effect_dpcode = description.scene_data

        # Update internals based on found brightness dpcode
        if self._brightness_dpcode:
            self._attr_supported_color_modes.add(COLOR_MODE_BRIGHTNESS)
            self._brightness_type = IntegerTypeData.from_json(
                device.status_range[self._brightness_dpcode].values
            )

        # Update internals based on found color temperature dpcode
        if self._color_temp_dpcode:
            self._attr_supported_color_modes.add(COLOR_MODE_COLOR_TEMP)
            self._color_temp_type = IntegerTypeData.from_json(
                device.status_range[self._color_temp_dpcode].values
            )

        # Update internals based on found color data dpcode
        if self._color_data_dpcode:
            self._attr_supported_color_modes.add(COLOR_MODE_HS)
            # Fetch color data type information
            if function_data := json.loads(
                self.device.function[self._color_data_dpcode].values
            ):
                self._color_data_type = ColorTypeData(
                    h_type=IntegerTypeData(**function_data["h"]),
                    s_type=IntegerTypeData(**function_data["s"]),
                    v_type=IntegerTypeData(**function_data["v"]),
                )
            else:
                # If no type is found, use a default one
                self._color_data_type = DEFAULT_COLOR_TYPE_DATA
                if self._color_data_dpcode == DPCode.COLOUR_DATA_V2 or (
                    self._brightness_type and self._brightness_type.max > 255
                ):
                    self._color_data_type = DEFAULT_COLOR_TYPE_DATA_V2
        if self._effect_dpcode:
            curren_effect_data = json.loads(device.status[self._effect_dpcode])
            for key, value in DEFAULT_SCENE_DATA_V2.items():
                if value["scene_num"] == curren_effect_data["scene_num"]:
                    self._attr_effect = key
            self._attr_effect_list = list(DEFAULT_SCENE_DATA_V2.keys())

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self.device.status.get(self.entity_description.key, False)

    def turn_on(self, **kwargs: Any) -> None:
        """Turn on or control the light."""
        commands = [{"code": self.entity_description.key, "value": True}]
        _LOGGER.debug("turn on kwargs -> %s", kwargs)
        if self._color_data_type and (
            ATTR_HS_COLOR in kwargs
            or (ATTR_BRIGHTNESS in kwargs and self.color_mode == COLOR_MODE_HS)
        ):
            if color_mode_dpcode := self.entity_description.color_mode:
                commands += [
                    {
                        "code": color_mode_dpcode,
                        "value": WorkMode.COLOUR,
                    },
                ]

            if not (brightness := kwargs.get(ATTR_BRIGHTNESS)):
                brightness = self.brightness or 0

            if not (color := kwargs.get(ATTR_HS_COLOR)):
                color = self.hs_color or (0, 0)

            commands += [
                {
                    "code": self._color_data_dpcode,
                    "value": json.dumps(
                        {
                            "h": round(
                                self._color_data_type.h_type.remap_value_from(
                                    color[0], 0, 360
                                )
                            ),
                            "s": round(
                                self._color_data_type.s_type.remap_value_from(
                                    color[1], 0, 100
                                )
                            ),
                            "v": round(
                                self._color_data_type.v_type.remap_value_from(
                                    brightness
                                )
                            ),
                        }
                    ),
                },
            ]

        elif ATTR_COLOR_TEMP in kwargs and self._color_temp_type:
            if color_mode_dpcode := self.entity_description.color_mode:
                commands += [
                    {
                        "code": color_mode_dpcode,
                        "value": WorkMode.WHITE,
                    },
                ]

            commands += [
                {
                    "code": self._color_temp_dpcode,
                    "value": round(
                        self._color_temp_type.remap_value_from(
                            kwargs[ATTR_COLOR_TEMP],
                            self.min_mireds,
                            self.max_mireds,
                            reverse=True,
                        )
                    ),
                },
            ]

        if (
            ATTR_BRIGHTNESS in kwargs
            and self.color_mode != COLOR_MODE_HS
            and self._brightness_type
        ):
            commands += [
                {
                    "code": self._brightness_dpcode,
                    "value": round(
                        self._brightness_type.remap_value_from(kwargs[ATTR_BRIGHTNESS])
                    ),
                },
            ]
        if ATTR_EFFECT in kwargs and self._attr_effect_list:
            commands += [
                {
                    "code": self._effect_dpcode,
                    "value": DEFAULT_SCENE_DATA_V2[kwargs[ATTR_EFFECT]],
                }
            ]

        for command in commands:
            _LOGGER.debug("turn on commands -> %s", command)
        self._send_command(commands)

    def turn_off(self, **kwargs: Any) -> None:
        """Instruct the light to turn off."""
        self._send_command([{"code": self.entity_description.key, "value": False}])

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        # If the light is currently in color mode, extract the brightness from the color data
        if self.color_mode == COLOR_MODE_HS and (color_data := self._get_color_data()):
            return color_data.brightness

        if not self._brightness_dpcode or not self._brightness_type:
            return None

        brightness = self.device.status.get(self._brightness_dpcode)
        if brightness is None:
            return None

        return round(self._brightness_type.remap_value_to(brightness))

    @property
    def color_temp(self) -> int | None:
        """Return the color_temp of the light."""
        if not self._color_temp_dpcode or not self._color_temp_type:
            return None

        temperature = self.device.status.get(self._color_temp_dpcode)
        if temperature is None:
            return None

        return round(
            self._color_temp_type.remap_value_to(
                temperature, self.min_mireds, self.max_mireds, reverse=True
            )
        )

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the hs_color of the light."""
        if self._color_data_dpcode is None or not (
            color_data := self._get_color_data()
        ):
            return None
        return color_data.hs_color

    @property
    def color_mode(self) -> str:
        """Return the color_mode of the light."""
        # We consider it to be in HS color mode, when work mode is anything
        # else than "white".
        if (
            self.entity_description.color_mode
            and self.device.status.get(self.entity_description.color_mode)
            != WorkMode.WHITE
        ):
            return COLOR_MODE_HS
        if self._color_temp_dpcode:
            return COLOR_MODE_COLOR_TEMP
        if self._brightness_dpcode:
            return COLOR_MODE_BRIGHTNESS
        return COLOR_MODE_ONOFF

    def _get_color_data(self) -> ColorData | None:
        """Get current color data from device."""
        if (
            self._color_data_type is None
            or self._color_data_dpcode is None
            or self._color_data_dpcode not in self.device.status
        ):
            return None

        if not (status_data := self.device.status[self._color_data_dpcode]):
            return None

        if not (status := json.loads(status_data)):
            return None

        return ColorData(
            type_data=self._color_data_type,
            h_value=status["h"],
            s_value=status["s"],
            v_value=status["v"],
        )

    @property
    def supported_features(self) -> int:
        """Return the SUPPORT_EFFECT feature if available."""
        features = 0
        if self._attr_effect_list:
            features |= SUPPORT_EFFECT
        return features

    @property
    def effect(self) -> str | None:
        """Return the Current effect in use."""
        if self.device.status[DPCode.WORK_MODE] == WorkMode.SCENE:
            return self._attr_effect
        return None
