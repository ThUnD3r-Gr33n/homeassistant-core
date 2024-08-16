"""Support for KNX/IP lights."""

from __future__ import annotations

from typing import Any, cast

from xknx import XKNX
from xknx.devices.light import ColorTemperatureType, Light as XknxLight, XYYColor

from homeassistant import config_entries
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ATTR_RGBW_COLOR,
    ATTR_XY_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.const import CONF_ENTITY_CATEGORY, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.helpers.typing import ConfigType
import homeassistant.util.color as color_util

from . import KNXModule
from .const import CONF_SYNC_STATE, DATA_KNX_CONFIG, DOMAIN, KNX_ADDRESS, ColorTempModes
from .knx_entity import KnxUiEntity, KnxUiEntityPlatformController, KnxYamlEntity
from .schema import LightSchema
from .storage.const import (
    CONF_COLOR_TEMP_MAX,
    CONF_COLOR_TEMP_MIN,
    CONF_DEVICE_INFO,
    CONF_DPT,
    CONF_ENTITY,
    CONF_GA_BLUE_BRIGHTNESS,
    CONF_GA_BLUE_SWITCH,
    CONF_GA_BRIGHTNESS,
    CONF_GA_COLOR,
    CONF_GA_COLOR_TEMP,
    CONF_GA_GREEN_BRIGHTNESS,
    CONF_GA_GREEN_SWITCH,
    CONF_GA_HUE,
    CONF_GA_PASSIVE,
    CONF_GA_RED_BRIGHTNESS,
    CONF_GA_RED_SWITCH,
    CONF_GA_SATURATION,
    CONF_GA_STATE,
    CONF_GA_SWITCH,
    CONF_GA_WHITE_BRIGHTNESS,
    CONF_GA_WHITE_SWITCH,
    CONF_GA_WRITE,
)
from .storage.entity_store_schema import LightColorMode


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up light(s) for KNX platform."""
    knx_module: KNXModule = hass.data[DOMAIN]
    platform = async_get_current_platform()
    knx_module.config_store.add_platform(
        platform=Platform.LIGHT,
        controller=KnxUiEntityPlatformController(
            knx_module=knx_module,
            entity_platform=platform,
            entity_class=KnxUiLight,
        ),
    )

    entities: list[KnxYamlEntity | KnxUiEntity] = []
    if yaml_platform_config := hass.data[DATA_KNX_CONFIG].get(Platform.LIGHT):
        entities.extend(
            KnxYamlLight(knx_module, entity_config)
            for entity_config in yaml_platform_config
        )
    if ui_config := knx_module.config_store.data["entities"].get(Platform.LIGHT):
        entities.extend(
            KnxUiLight(knx_module, unique_id, config)
            for unique_id, config in ui_config.items()
        )
    if entities:
        async_add_entities(entities)


def _create_yaml_light(xknx: XKNX, config: ConfigType) -> XknxLight:
    """Return a KNX Light device to be used within XKNX."""

    def individual_color_addresses(color: str, feature: str) -> Any | None:
        """Load individual color address list from configuration structure."""
        if (
            LightSchema.CONF_INDIVIDUAL_COLORS not in config
            or color not in config[LightSchema.CONF_INDIVIDUAL_COLORS]
        ):
            return None
        return config[LightSchema.CONF_INDIVIDUAL_COLORS][color].get(feature)

    group_address_tunable_white = None
    group_address_tunable_white_state = None
    group_address_color_temp = None
    group_address_color_temp_state = None
    color_temperature_type = ColorTemperatureType.UINT_2_BYTE
    if config[LightSchema.CONF_COLOR_TEMP_MODE] == ColorTempModes.RELATIVE:
        group_address_tunable_white = config.get(LightSchema.CONF_COLOR_TEMP_ADDRESS)
        group_address_tunable_white_state = config.get(
            LightSchema.CONF_COLOR_TEMP_STATE_ADDRESS
        )
    else:
        # absolute uint or float
        group_address_color_temp = config.get(LightSchema.CONF_COLOR_TEMP_ADDRESS)
        group_address_color_temp_state = config.get(
            LightSchema.CONF_COLOR_TEMP_STATE_ADDRESS
        )
        if config[LightSchema.CONF_COLOR_TEMP_MODE] == ColorTempModes.ABSOLUTE_FLOAT:
            color_temperature_type = ColorTemperatureType.FLOAT_2_BYTE

    return XknxLight(
        xknx,
        name=config[CONF_NAME],
        group_address_switch=config.get(KNX_ADDRESS),
        group_address_switch_state=config.get(LightSchema.CONF_STATE_ADDRESS),
        group_address_brightness=config.get(LightSchema.CONF_BRIGHTNESS_ADDRESS),
        group_address_brightness_state=config.get(
            LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS
        ),
        group_address_color=config.get(LightSchema.CONF_COLOR_ADDRESS),
        group_address_color_state=config.get(LightSchema.CONF_COLOR_STATE_ADDRESS),
        group_address_rgbw=config.get(LightSchema.CONF_RGBW_ADDRESS),
        group_address_rgbw_state=config.get(LightSchema.CONF_RGBW_STATE_ADDRESS),
        group_address_hue=config.get(LightSchema.CONF_HUE_ADDRESS),
        group_address_hue_state=config.get(LightSchema.CONF_HUE_STATE_ADDRESS),
        group_address_saturation=config.get(LightSchema.CONF_SATURATION_ADDRESS),
        group_address_saturation_state=config.get(
            LightSchema.CONF_SATURATION_STATE_ADDRESS
        ),
        group_address_xyy_color=config.get(LightSchema.CONF_XYY_ADDRESS),
        group_address_xyy_color_state=config.get(LightSchema.CONF_XYY_STATE_ADDRESS),
        group_address_tunable_white=group_address_tunable_white,
        group_address_tunable_white_state=group_address_tunable_white_state,
        group_address_color_temperature=group_address_color_temp,
        group_address_color_temperature_state=group_address_color_temp_state,
        group_address_switch_red=individual_color_addresses(
            LightSchema.CONF_RED, KNX_ADDRESS
        ),
        group_address_switch_red_state=individual_color_addresses(
            LightSchema.CONF_RED, LightSchema.CONF_STATE_ADDRESS
        ),
        group_address_brightness_red=individual_color_addresses(
            LightSchema.CONF_RED, LightSchema.CONF_BRIGHTNESS_ADDRESS
        ),
        group_address_brightness_red_state=individual_color_addresses(
            LightSchema.CONF_RED, LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS
        ),
        group_address_switch_green=individual_color_addresses(
            LightSchema.CONF_GREEN, KNX_ADDRESS
        ),
        group_address_switch_green_state=individual_color_addresses(
            LightSchema.CONF_GREEN, LightSchema.CONF_STATE_ADDRESS
        ),
        group_address_brightness_green=individual_color_addresses(
            LightSchema.CONF_GREEN, LightSchema.CONF_BRIGHTNESS_ADDRESS
        ),
        group_address_brightness_green_state=individual_color_addresses(
            LightSchema.CONF_GREEN, LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS
        ),
        group_address_switch_blue=individual_color_addresses(
            LightSchema.CONF_BLUE, KNX_ADDRESS
        ),
        group_address_switch_blue_state=individual_color_addresses(
            LightSchema.CONF_BLUE, LightSchema.CONF_STATE_ADDRESS
        ),
        group_address_brightness_blue=individual_color_addresses(
            LightSchema.CONF_BLUE, LightSchema.CONF_BRIGHTNESS_ADDRESS
        ),
        group_address_brightness_blue_state=individual_color_addresses(
            LightSchema.CONF_BLUE, LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS
        ),
        group_address_switch_white=individual_color_addresses(
            LightSchema.CONF_WHITE, KNX_ADDRESS
        ),
        group_address_switch_white_state=individual_color_addresses(
            LightSchema.CONF_WHITE, LightSchema.CONF_STATE_ADDRESS
        ),
        group_address_brightness_white=individual_color_addresses(
            LightSchema.CONF_WHITE, LightSchema.CONF_BRIGHTNESS_ADDRESS
        ),
        group_address_brightness_white_state=individual_color_addresses(
            LightSchema.CONF_WHITE, LightSchema.CONF_BRIGHTNESS_STATE_ADDRESS
        ),
        color_temperature_type=color_temperature_type,
        min_kelvin=config[LightSchema.CONF_MIN_KELVIN],
        max_kelvin=config[LightSchema.CONF_MAX_KELVIN],
    )


def _create_ui_light(xknx: XKNX, knx_config: ConfigType, name: str) -> XknxLight:
    """Return a KNX Light device to be used within XKNX."""

    def get_write(key: str) -> str | None:
        """Get the write group address."""
        return knx_config[key][CONF_GA_WRITE] if key in knx_config else None

    def get_state(key: str) -> list[Any] | None:
        """Get the state group address."""
        return (
            [knx_config[key][CONF_GA_STATE], *knx_config[key][CONF_GA_PASSIVE]]
            if key in knx_config
            else None
        )

    def get_dpt(key: str) -> str | None:
        """Get the DPT."""
        return knx_config[key].get(CONF_DPT) if key in knx_config else None

    group_address_tunable_white = None
    group_address_tunable_white_state = None
    group_address_color_temp = None
    group_address_color_temp_state = None
    color_temperature_type = ColorTemperatureType.UINT_2_BYTE
    if ga_color_temp := knx_config.get(CONF_GA_COLOR_TEMP):
        if ga_color_temp[CONF_DPT] == ColorTempModes.RELATIVE.value:
            group_address_tunable_white = ga_color_temp[CONF_GA_WRITE]
            group_address_tunable_white_state = [
                ga_color_temp[CONF_GA_STATE],
                *ga_color_temp[CONF_GA_PASSIVE],
            ]
        else:
            # absolute uint or float
            group_address_color_temp = ga_color_temp[CONF_GA_WRITE]
            group_address_color_temp_state = [
                ga_color_temp[CONF_GA_STATE],
                *ga_color_temp[CONF_GA_PASSIVE],
            ]
            if ga_color_temp[CONF_DPT] == ColorTempModes.ABSOLUTE_FLOAT.value:
                color_temperature_type = ColorTemperatureType.FLOAT_2_BYTE

    _color_dpt = get_dpt(CONF_GA_COLOR)
    return XknxLight(
        xknx,
        name=name,
        group_address_switch=get_write(CONF_GA_SWITCH),
        group_address_switch_state=get_state(CONF_GA_SWITCH),
        group_address_brightness=get_write(CONF_GA_BRIGHTNESS),
        group_address_brightness_state=get_state(CONF_GA_BRIGHTNESS),
        group_address_color=get_write(CONF_GA_COLOR)
        if _color_dpt == LightColorMode.RGB
        else None,
        group_address_color_state=get_state(CONF_GA_COLOR)
        if _color_dpt == LightColorMode.RGB
        else None,
        group_address_rgbw=get_write(CONF_GA_COLOR)
        if _color_dpt == LightColorMode.RGBW
        else None,
        group_address_rgbw_state=get_state(CONF_GA_COLOR)
        if _color_dpt == LightColorMode.RGBW
        else None,
        group_address_hue=get_write(CONF_GA_HUE),
        group_address_hue_state=get_state(CONF_GA_HUE),
        group_address_saturation=get_write(CONF_GA_SATURATION),
        group_address_saturation_state=get_state(CONF_GA_SATURATION),
        group_address_xyy_color=get_write(CONF_GA_COLOR)
        if _color_dpt == LightColorMode.XYY
        else None,
        group_address_xyy_color_state=get_write(CONF_GA_COLOR)
        if _color_dpt == LightColorMode.XYY
        else None,
        group_address_tunable_white=group_address_tunable_white,
        group_address_tunable_white_state=group_address_tunable_white_state,
        group_address_color_temperature=group_address_color_temp,
        group_address_color_temperature_state=group_address_color_temp_state,
        group_address_switch_red=get_write(CONF_GA_RED_SWITCH),
        group_address_switch_red_state=get_state(CONF_GA_RED_SWITCH),
        group_address_brightness_red=get_write(CONF_GA_RED_BRIGHTNESS),
        group_address_brightness_red_state=get_state(CONF_GA_RED_BRIGHTNESS),
        group_address_switch_green=get_write(CONF_GA_GREEN_SWITCH),
        group_address_switch_green_state=get_state(CONF_GA_GREEN_SWITCH),
        group_address_brightness_green=get_write(CONF_GA_GREEN_BRIGHTNESS),
        group_address_brightness_green_state=get_state(CONF_GA_GREEN_BRIGHTNESS),
        group_address_switch_blue=get_write(CONF_GA_BLUE_SWITCH),
        group_address_switch_blue_state=get_state(CONF_GA_BLUE_SWITCH),
        group_address_brightness_blue=get_write(CONF_GA_BLUE_BRIGHTNESS),
        group_address_brightness_blue_state=get_state(CONF_GA_BLUE_BRIGHTNESS),
        group_address_switch_white=get_write(CONF_GA_WHITE_SWITCH),
        group_address_switch_white_state=get_state(CONF_GA_WHITE_SWITCH),
        group_address_brightness_white=get_write(CONF_GA_WHITE_BRIGHTNESS),
        group_address_brightness_white_state=get_state(CONF_GA_WHITE_BRIGHTNESS),
        color_temperature_type=color_temperature_type,
        min_kelvin=knx_config[CONF_COLOR_TEMP_MIN],
        max_kelvin=knx_config[CONF_COLOR_TEMP_MAX],
        sync_state=knx_config[CONF_SYNC_STATE],
    )


class _KnxLight(LightEntity):
    """Representation of a KNX light."""

    _attr_max_color_temp_kelvin: int
    _attr_min_color_temp_kelvin: int
    _device: XknxLight

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return bool(self._device.state)

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        if self._device.supports_brightness:
            return self._device.current_brightness
        if self._device.current_xyy_color is not None:
            return self._device.current_xyy_color.brightness
        if self._device.supports_color or self._device.supports_rgbw:
            rgb, white = self._device.current_color
            if rgb is None:
                return white
            if white is None:
                return max(rgb)
            return max(*rgb, white)
        return None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value [int, int, int]."""
        if self._device.supports_color:
            rgb, _ = self._device.current_color
            if rgb is not None:
                if not self._device.supports_brightness:
                    # brightness will be calculated from color so color must not hold brightness again
                    return cast(
                        tuple[int, int, int], color_util.match_max_scale((255,), rgb)
                    )
                return rgb
        return None

    @property
    def rgbw_color(self) -> tuple[int, int, int, int] | None:
        """Return the rgbw color value [int, int, int, int]."""
        if self._device.supports_rgbw:
            rgb, white = self._device.current_color
            if rgb is not None and white is not None:
                if not self._device.supports_brightness:
                    # brightness will be calculated from color so color must not hold brightness again
                    return cast(
                        tuple[int, int, int, int],
                        color_util.match_max_scale((255,), (*rgb, white)),
                    )
                return (*rgb, white)
        return None

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the hue and saturation color value [float, float]."""
        # Hue is scaled 0..360 int encoded in 1 byte in KNX (-> only 256 possible values)
        # Saturation is scaled 0..100 int
        return self._device.current_hs_color

    @property
    def xy_color(self) -> tuple[float, float] | None:
        """Return the xy color value [float, float]."""
        if self._device.current_xyy_color is not None:
            return self._device.current_xyy_color.color
        return None

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in Kelvin."""
        if self._device.supports_color_temperature:
            if kelvin := self._device.current_color_temperature:
                return int(kelvin)
        if self._device.supports_tunable_white:
            relative_ct = self._device.current_tunable_white
            if relative_ct is not None:
                return int(
                    self._attr_min_color_temp_kelvin
                    + (
                        (relative_ct / 255)
                        * (
                            self._attr_max_color_temp_kelvin
                            - self._attr_min_color_temp_kelvin
                        )
                    )
                )
        return None

    @property
    def color_mode(self) -> ColorMode:
        """Return the color mode of the light."""
        if self._device.supports_xyy_color:
            return ColorMode.XY
        if self._device.supports_hs_color:
            return ColorMode.HS
        if self._device.supports_rgbw:
            return ColorMode.RGBW
        if self._device.supports_color:
            return ColorMode.RGB
        if (
            self._device.supports_color_temperature
            or self._device.supports_tunable_white
        ):
            return ColorMode.COLOR_TEMP
        if self._device.supports_brightness:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF

    @property
    def supported_color_modes(self) -> set[ColorMode]:
        """Flag supported color modes."""
        return {self.color_mode}

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        color_temp = kwargs.get(ATTR_COLOR_TEMP_KELVIN)
        rgb = kwargs.get(ATTR_RGB_COLOR)
        rgbw = kwargs.get(ATTR_RGBW_COLOR)
        hs_color = kwargs.get(ATTR_HS_COLOR)
        xy_color = kwargs.get(ATTR_XY_COLOR)

        if (
            not self.is_on
            and brightness is None
            and color_temp is None
            and rgb is None
            and rgbw is None
            and hs_color is None
            and xy_color is None
        ):
            await self._device.set_on()
            return

        async def set_color(
            rgb: tuple[int, int, int], white: int | None, brightness: int | None
        ) -> None:
            """Set color of light. Normalize colors for brightness when not writable."""
            if self._device.brightness.writable:
                # let the KNX light controller handle brightness
                await self._device.set_color(rgb, white)
                if brightness:
                    await self._device.set_brightness(brightness)
                return

            if brightness is None:
                # normalize for brightness if brightness is derived from color
                brightness = self.brightness or 255
            rgb = cast(
                tuple[int, int, int],
                tuple(color * brightness // 255 for color in rgb),
            )
            white = white * brightness // 255 if white is not None else None
            await self._device.set_color(rgb, white)

        # return after RGB(W) color has changed as it implicitly sets the brightness
        if rgbw is not None:
            await set_color(rgbw[:3], rgbw[3], brightness)
            return
        if rgb is not None:
            await set_color(rgb, None, brightness)
            return

        if color_temp is not None:
            color_temp = min(
                self._attr_max_color_temp_kelvin,
                max(self._attr_min_color_temp_kelvin, color_temp),
            )
            if self._device.supports_color_temperature:
                await self._device.set_color_temperature(color_temp)
            elif self._device.supports_tunable_white:
                relative_ct = round(
                    255
                    * (color_temp - self._attr_min_color_temp_kelvin)
                    / (
                        self._attr_max_color_temp_kelvin
                        - self._attr_min_color_temp_kelvin
                    )
                )
                await self._device.set_tunable_white(relative_ct)

        if xy_color is not None:
            await self._device.set_xyy_color(
                XYYColor(color=xy_color, brightness=brightness)
            )
            return

        if hs_color is not None:
            # round so only one telegram will be sent if the other matches state
            hue = round(hs_color[0])
            sat = round(hs_color[1])
            await self._device.set_hs_color((hue, sat))

        if brightness is not None:
            # brightness: 1..255; 0 brightness will call async_turn_off()
            if self._device.brightness.writable:
                await self._device.set_brightness(brightness)
                return
            # brightness without color in kwargs; set via color
            if self.color_mode == ColorMode.XY:
                await self._device.set_xyy_color(XYYColor(brightness=brightness))
                return
            # default to white if color not known for RGB(W)
            if self.color_mode == ColorMode.RGBW:
                _rgbw = self.rgbw_color
                if not _rgbw or not any(_rgbw):
                    _rgbw = (0, 0, 0, 255)
                await set_color(_rgbw[:3], _rgbw[3], brightness)
                return
            if self.color_mode == ColorMode.RGB:
                _rgb = self.rgb_color
                if not _rgb or not any(_rgb):
                    _rgb = (255, 255, 255)
                await set_color(_rgb, None, brightness)
                return

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self._device.set_off()


class KnxYamlLight(_KnxLight, KnxYamlEntity):
    """Representation of a KNX light."""

    _device: XknxLight

    def __init__(self, knx_module: KNXModule, config: ConfigType) -> None:
        """Initialize of KNX light."""
        super().__init__(
            knx_module=knx_module,
            device=_create_yaml_light(knx_module.xknx, config),
        )
        self._attr_max_color_temp_kelvin: int = config[LightSchema.CONF_MAX_KELVIN]
        self._attr_min_color_temp_kelvin: int = config[LightSchema.CONF_MIN_KELVIN]
        self._attr_entity_category = config.get(CONF_ENTITY_CATEGORY)
        self._attr_unique_id = self._device_unique_id()

    def _device_unique_id(self) -> str:
        """Return unique id for this device."""
        if self._device.switch.group_address is not None:
            return f"{self._device.switch.group_address}"
        return (
            f"{self._device.red.brightness.group_address}_"
            f"{self._device.green.brightness.group_address}_"
            f"{self._device.blue.brightness.group_address}"
        )


class KnxUiLight(_KnxLight, KnxUiEntity):
    """Representation of a KNX light."""

    _attr_has_entity_name = True
    _device: XknxLight

    def __init__(
        self, knx_module: KNXModule, unique_id: str, config: ConfigType
    ) -> None:
        """Initialize of KNX light."""
        self._knx_module = knx_module
        self._device = _create_ui_light(
            knx_module.xknx, config[DOMAIN], config[CONF_ENTITY][CONF_NAME]
        )
        self._attr_max_color_temp_kelvin: int = config[DOMAIN][CONF_COLOR_TEMP_MAX]
        self._attr_min_color_temp_kelvin: int = config[DOMAIN][CONF_COLOR_TEMP_MIN]

        self._attr_entity_category = config[CONF_ENTITY][CONF_ENTITY_CATEGORY]
        self._attr_unique_id = unique_id
        if device_info := config[CONF_ENTITY].get(CONF_DEVICE_INFO):
            self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device_info)})
