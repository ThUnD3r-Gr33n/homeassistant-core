"""Support for Homekit motion sensors."""
from __future__ import annotations

from aiohomekit.model.characteristics import Characteristic, CharacteristicsTypes
from aiohomekit.model.characteristics.const import InputEventValues
from aiohomekit.model.services import Service, ServicesTypes
from aiohomekit.utils import clamp_enum_to_char

from homeassistant.components.event import (
    EventDeviceClass,
    EventEntity,
    EventEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import KNOWN_DEVICES
from .connection import HKDevice
from .entity import HomeKitEntity

INPUT_EVENT_VALUES = {
    InputEventValues.SINGLE_PRESS: "single_press",
    InputEventValues.DOUBLE_PRESS: "double_press",
    InputEventValues.LONG_PRESS: "long_press",
}


class HomeKitEventEntity(HomeKitEntity, EventEntity):
    """Representation of a Homekit event entity."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        connection: HKDevice,
        service: Service,
        entity_description: EventEntityDescription,
    ) -> None:
        """Initialise a generic HomeKit event entity."""
        super().__init__(
            connection,
            {
                "aid": service.accessory.aid,
                "iid": service.iid,
            },
        )
        self._service = service
        self._characteristic = service.characteristics_by_type[
            CharacteristicsTypes.INPUT_EVENT
        ]

        self.entity_description = entity_description

        # An INPUT_EVENT may support single_press, long_press and double_press. All are optional. So we have to
        # clamp InputEventValues for this exact device
        self._attr_event_types = [
            INPUT_EVENT_VALUES[v]
            for v in clamp_enum_to_char(InputEventValues, self._characteristic)
        ]

    def get_characteristic_types(self) -> list[str]:
        """Define the homekit characteristics the entity cares about."""
        return [CharacteristicsTypes.INPUT_EVENT]

    async def async_added_to_hass(self) -> None:
        """Entity added to hass."""
        await super().async_added_to_hass()

        self.async_on_remove(
            self._accessory.async_subscribe(
                [(self._aid, self._characteristic.iid)],
                self._handle_event,
            )
        )

    @callback
    def _handle_event(self):
        self._trigger_event(INPUT_EVENT_VALUES[self._characteristic.value])
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homekit event."""
    hkid: str = config_entry.data["AccessoryPairingID"]
    conn: HKDevice = hass.data[KNOWN_DEVICES][hkid]

    @callback
    def async_add_characteristic(char: Characteristic) -> bool:
        service = char.service
        entities = []

        if service.type == ServicesTypes.DOORBELL:
            entities.append(
                HomeKitEventEntity(
                    conn,
                    service,
                    EventEntityDescription(
                        key=f"{service.accessory.aid}_{service.iid}",
                        device_class=EventDeviceClass.DOORBELL,
                        translation_key="doorbell",
                        name="Doorbell",
                    ),
                )
            )

        elif service.type == ServicesTypes.SERVICE_LABEL:
            switches = list(
                service.accessory.services.filter(
                    service_type=ServicesTypes.STATELESS_PROGRAMMABLE_SWITCH,
                    child_service=service,
                    order_by=[CharacteristicsTypes.SERVICE_LABEL_INDEX],
                )
            )

            for idx, switch in enumerate(switches):
                entities.append(
                    HomeKitEventEntity(
                        conn,
                        switch,
                        EventEntityDescription(
                            key=f"{service.accessory.aid}_{service.iid}",
                            device_class=EventDeviceClass.BUTTON,
                            translation_key="button",
                            name=f"Button {idx}",
                        ),
                    )
                )

        elif service.type == ServicesTypes.STATELESS_PROGRAMMABLE_SWITCH:
            # A stateless switch that has a SERVICE_LABEL_INDEX is part of a group
            # And is handled separately
            if not service.has(CharacteristicsTypes.SERVICE_LABEL_INDEX):
                entities.append(
                    HomeKitEventEntity(
                        conn,
                        service,
                        EventEntityDescription(
                            key=f"{service.accessory.aid}_{service.iid}",
                            device_class=EventDeviceClass.BUTTON,
                            translation_key="button",
                            name="Button",
                        ),
                    )
                )

        if entities:
            async_add_entities(entities)
            return True

        return False

    conn.add_char_factory(async_add_characteristic)
