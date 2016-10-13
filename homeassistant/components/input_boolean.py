"""
Component to keep track of user controlled booleans for within automation.

For more details about this component, please refer to the documentation
at https://home-assistant.io/components/input_boolean/
"""
import logging

import voluptuous as vol

from homeassistant.const import (
    ATTR_ENTITY_ID, CONF_ICON, CONF_NAME, SERVICE_TURN_OFF, SERVICE_TURN_ON,
    SERVICE_TOGGLE, STATE_ON)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import ToggleEntity
from homeassistant.helpers.entity_component import (EntityComponent,
                                                    generate_entity_id)
from homeassistant.helpers import extract_domain_configs

DOMAIN = 'input_boolean'

ENTITY_ID_FORMAT = DOMAIN + '.{}'

_LOGGER = logging.getLogger(__name__)

CONF_INITIAL = 'initial'

SERVICE_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
})

CONFIG_SCHEMA = vol.Schema({DOMAIN: {
    cv.slug: vol.Any({
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_INITIAL, default=False): cv.boolean,
        vol.Optional(CONF_ICON): cv.icon,
    }, None)}}, extra=vol.ALLOW_EXTRA)


def is_on(hass, entity_id):
    """Test if input_boolean is True."""
    return hass.states.is_state(entity_id, STATE_ON)


def turn_on(hass, entity_id):
    """Set input_boolean to True."""
    hass.services.call(DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id})


def turn_off(hass, entity_id):
    """Set input_boolean to False."""
    hass.services.call(DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id})


def toggle(hass, entity_id):
    """Set input_boolean to False."""
    hass.services.call(DOMAIN, SERVICE_TOGGLE, {ATTR_ENTITY_ID: entity_id})


def setup(hass, config):
    """Set up input boolean."""
    component = EntityComponent(_LOGGER, DOMAIN, hass)

    entities = []
    entity_ids = []

    for config_key in extract_domain_configs(config, DOMAIN):
        for object_id, cfg in config[config_key].items():
            if not cfg:
                cfg = {}

            name = cfg.get(CONF_NAME)
            state = cfg.get(CONF_INITIAL, False)
            icon = cfg.get(CONF_ICON)
            entity_id = generate_entity_id(ENTITY_ID_FORMAT,
                                           object_id, entity_ids)
            entity_ids.append(entity_id)
            entities.append(InputBoolean(entity_id, name, state, icon))

    if not entities:
        return False

    def handler_service(service):
        """Handle a calls to the input boolean services."""
        target_inputs = component.extract_from_service(service)

        for input_b in target_inputs:
            if service.service == SERVICE_TURN_ON:
                input_b.turn_on()
            elif service.service == SERVICE_TURN_OFF:
                input_b.turn_off()
            else:
                input_b.toggle()

    hass.services.register(DOMAIN, SERVICE_TURN_OFF, handler_service,
                           schema=SERVICE_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_TURN_ON, handler_service,
                           schema=SERVICE_SCHEMA)
    hass.services.register(DOMAIN, SERVICE_TOGGLE, handler_service,
                           schema=SERVICE_SCHEMA)

    component.add_entities(entities)

    return True


class InputBoolean(ToggleEntity):
    """Representation of a boolean input."""

    def __init__(self, entity_id, name, state, icon):
        """Initialize a boolean input."""
        self.entity_id = entity_id
        self._name = name
        self._state = state
        self._icon = icon

    @property
    def should_poll(self):
        """If entity should be polled."""
        return False

    @property
    def name(self):
        """Return name of the boolean input."""
        return self._name

    @property
    def icon(self):
        """Returh the icon to be used for this entity."""
        return self._icon

    @property
    def is_on(self):
        """Return true if entity is on."""
        return self._state

    def turn_on(self, **kwargs):
        """Turn the entity on."""
        self._state = True
        self.update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the entity off."""
        self._state = False
        self.update_ha_state()
