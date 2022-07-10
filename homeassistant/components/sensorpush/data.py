"""Parser for SensorPush BLE advertisements.

This file is shamlessly copied from the following repository:
https://github.com/Ernst79/bleparser/blob/c42ae922e1abed2720c7fac993777e1bd59c0c93/package/bleparser/sensorpush.py

MIT License applies.
"""
from __future__ import annotations

import logging

from homeassistant.components.bluetooth import BluetoothServiceInfo
from homeassistant.components.bluetooth.device import BluetoothDeviceData
from homeassistant.components.bluetooth.sensor import BluetoothSensorType
from homeassistant.const import PERCENTAGE, PRESSURE_MBAR, TEMP_CELSIUS

_LOGGER = logging.getLogger(__name__)

SENSORPUSH_DEVICE_TYPES = {64: "HTP.xw", 65: "HT.w"}

SENSORPUSH_PACK_PARAMS = {
    64: [[-40.0, 140.0, 0.0025], [0.0, 100.0, 0.0025], [30000.0, 125000.0, 1.0]],
    65: [[-40.0, 125.0, 0.0025], [0.0, 100.0, 0.0025]],
}

SENSORPUSH_DATA_TYPES = {
    64: ["temperature", "humidity", "pressure"],
    65: ["temperature", "humidity"],
}


def decode_values(mfg_data: bytes, device_type_id: int) -> dict:
    """Decode values."""
    pack_params = SENSORPUSH_PACK_PARAMS.get(device_type_id, None)
    if pack_params is None:
        _LOGGER.error("SensorPush device type id %s unknown", device_type_id)
        return {}

    values = {}

    packed_values = 0
    for i in range(1, len(mfg_data)):
        packed_values += mfg_data[i] << (8 * (i - 1))

    mod = 1
    div = 1
    for i, block in enumerate(pack_params):
        min_value = block[0]
        max_value = block[1]
        step = block[2]
        mod *= int((max_value - min_value) / step + step / 2.0) + 1
        value_count = int((packed_values % mod) / div)
        data_type = SENSORPUSH_DATA_TYPES[device_type_id][i]
        value = round(value_count * step + min_value, 2)
        if data_type == "pressure":
            value = value / 100.0
        values[data_type] = value
        div *= int((max_value - min_value) / step + step / 2.0) + 1

    return values


class SensorPushBluetoothDeviceData(BluetoothDeviceData):
    """Date update for SensorPush Bluetooth devices."""

    def update(self, service_info: BluetoothServiceInfo) -> None:
        """Update from BLE advertisement data."""
        manufacturer_data = service_info.manufacturer_data
        local_name = service_info.name
        _LOGGER.debug(
            "Parsing SensorPush BLE advertisement data: %s", manufacturer_data
        )
        result = {}
        device_type = None
        if "HTP.xw" in local_name:
            device_type = "HTP.xw"
        elif "HT.xw" in local_name:
            device_type = "HT.xw"

        last_id = list(manufacturer_data)[-1]
        data = int(last_id).to_bytes(2, byteorder="little") + manufacturer_data[last_id]
        page_id = data[0] & 0x03
        if page_id == 0:
            device_type_id = 64 + (data[0] >> 2)
            if known_device_type := SENSORPUSH_DEVICE_TYPES.get(device_type_id):
                device_type = known_device_type
            result.update(decode_values(data, device_type_id))

        if device_type:
            self.set_device_type(device_type)
            if service_info.name.startswith("SensorPush "):
                self.set_device_name(service_info.name[11:])
            else:
                self.set_device_name(service_info.name)

        for key, value in result.items():
            if key == "temperature":
                self.update_predefined_sensor(
                    BluetoothSensorType.TEMPERATURE, TEMP_CELSIUS, value
                )
            if key == "humidity":
                self.update_predefined_sensor(
                    BluetoothSensorType.HUMIDITY, PERCENTAGE, value
                )
            if key == "pressure":
                self.update_predefined_sensor(
                    BluetoothSensorType.PRESSURE, PRESSURE_MBAR, value
                )
