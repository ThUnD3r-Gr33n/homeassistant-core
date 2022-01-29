"""Sensor from an SQL Query."""
from __future__ import annotations

import datetime
import decimal
import logging

import sqlalchemy
from sqlalchemy.orm import scoped_session, sessionmaker
import voluptuous as vol

from homeassistant.components.recorder import CONF_DB_URL
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_NAME, CONF_UNIT_OF_MEASUREMENT, CONF_VALUE_TEMPLATE
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.template import Template
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import CONF_COLUMN_NAME, CONF_QUERIES, CONF_QUERY, DB_URL_RE, DOMAIN

_LOGGER = logging.getLogger(__name__)


def redact_credentials(data) -> str:
    """Redact credentials from string data."""
    return DB_URL_RE.sub("//****:****@", data)


def validate_sql_select(value) -> str:
    """Validate that value is a SQL SELECT query."""
    if not value.lstrip().lower().startswith("select"):
        raise vol.Invalid("Only SELECT queries allowed")
    return value


_QUERY_SCHEME = vol.Schema(
    {
        vol.Required(CONF_COLUMN_NAME): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_QUERY): vol.All(cv.string, validate_sql_select),
        vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
        vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Required(CONF_QUERIES): [_QUERY_SCHEME], vol.Optional(CONF_DB_URL): cv.string}
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the SQL sensor platform."""

    _LOGGER.warning(
        # Config flow added in Home Assistant Core 2022.3, remove import flow in 2022.7
        "Loading SQL via platform setup is deprecated; Please remove it from your configuration"
    )

    for query in config[CONF_QUERIES]:
        new_config = {
            CONF_DB_URL: config.get(CONF_DB_URL),
            CONF_NAME: query.get(CONF_NAME),
            CONF_QUERY: query.get(CONF_QUERY),
            CONF_UNIT_OF_MEASUREMENT: query.get(CONF_UNIT_OF_MEASUREMENT),
            CONF_VALUE_TEMPLATE: query.get(CONF_VALUE_TEMPLATE),
            CONF_COLUMN_NAME: query.get(CONF_COLUMN_NAME),
        }
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=new_config,
            )
        )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the SQL sensor entry."""

    db_url = entry.data[CONF_DB_URL]
    name = entry.data[CONF_NAME]
    query_str = entry.data[CONF_QUERY]
    unit = entry.data.get(CONF_UNIT_OF_MEASUREMENT)
    value_template = entry.data.get(CONF_VALUE_TEMPLATE)
    column_name = entry.data[CONF_COLUMN_NAME]

    if value_template is not None:
        value_template.hass = hass

    engine = sqlalchemy.create_engine(db_url)
    sessmaker = scoped_session(sessionmaker(bind=engine))

    # MSSQL uses TOP and not LIMIT
    if not ("LIMIT" in query_str.upper() or "SELECT TOP" in query_str.upper()):
        query_str = (
            query_str.replace("SELECT", "SELECT TOP 1")
            if "mssql" in db_url
            else query_str.replace(";", " LIMIT 1;")
        )

    async_add_entities(
        [
            SQLSensor(
                name,
                sessmaker,
                query_str,
                column_name,
                unit,
                value_template,
                entry.entry_id,
            )
        ],
        True,
    )


class SQLSensor(SensorEntity):
    """Representation of an SQL sensor."""

    def __init__(
        self,
        name: str,
        sessmaker: scoped_session,
        query: str,
        column: str,
        unit: str | None,
        value_template: Template | None,
        entry_id: str,
    ) -> None:
        """Initialize the SQL sensor."""
        self._name = name
        self._query = query
        self._unit_of_measurement = unit
        self._template = value_template
        self._column_name = column
        self.sessionmaker = sessmaker
        self._state = None
        self._attributes = None
        self._attr_unique_id = entry_id

    @property
    def name(self):
        """Return the name of the query."""
        return self._name

    @property
    def native_value(self):
        """Return the query's current state."""
        return self._state

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    def update(self):
        """Retrieve sensor data from the query."""

        data = None
        try:
            sess = self.sessionmaker()
            result = sess.execute(self._query)
            self._attributes = {}

            if not result.returns_rows or result.rowcount == 0:
                _LOGGER.warning("%s returned no results", self._query)
                self._state = None
                return

            for res in result.mappings():
                _LOGGER.debug("result = %s", res.items())
                data = res[self._column_name]
                for key, value in res.items():
                    if isinstance(value, decimal.Decimal):
                        value = float(value)
                    if isinstance(value, datetime.date):
                        value = str(value)
                    self._attributes[key] = value
        except sqlalchemy.exc.SQLAlchemyError as err:
            _LOGGER.error(
                "Error executing query %s: %s",
                self._query,
                redact_credentials(str(err)),
            )
            return
        finally:
            sess.close()

        if data is not None and self._template is not None:
            self._state = self._template.async_render_with_possible_json_value(
                data, None
            )
        else:
            self._state = data
