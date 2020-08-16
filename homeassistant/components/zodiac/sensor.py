"""Support for tracking the zodiac sign."""
import logging

from homeassistant.helpers.entity import Entity
import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)

SIGN_ARIES = "aries"
SIGN_TAURUS = "taurus"
SIGN_GEMINI = "gemini"
SIGN_CANCER = "cancer"
SIGN_LEO = "leo"
SIGN_VIRGO = "virgo"
SIGN_LIBRA = "libra"
SIGN_SCORPIO = "scorpio"
SIGN_SAGITTARIUS = "sagittarius"
SIGN_CAPRICORN = "capricorn"
SIGN_AQUARIUS = "aquarius"
SIGN_PISCES = "pisces"

ELEMENT_FIRE = "fire"
ELEMENT_AIR = "air"
ELEMENT_EARTH = "earth"
ELEMENT_WATER = "water"

MODALITY_CARDINAL = "cardinal"
MODALITY_FIXED = "fixed"
MODALITY_MUTABLE = "mutable"


ATTR_SIGN = "sign"
ATTR_ELEMENT = "element"
ATTR_MODALITY = "modality"

STATE_ATTR = ATTR_SIGN

ZODIAC_BY_DATE = (
    (
        (21, 3),
        (20, 4),
        {
            ATTR_SIGN: SIGN_ARIES,
            ATTR_ELEMENT: ELEMENT_FIRE,
            ATTR_MODALITY: MODALITY_CARDINAL,
        },
    ),
    (
        (21, 4),
        (20, 5),
        {
            ATTR_SIGN: SIGN_TAURUS,
            ATTR_ELEMENT: ELEMENT_EARTH,
            ATTR_MODALITY: MODALITY_FIXED,
        },
    ),
    (
        (21, 5),
        (21, 6),
        {
            ATTR_SIGN: SIGN_GEMINI,
            ATTR_ELEMENT: ELEMENT_AIR,
            ATTR_MODALITY: MODALITY_MUTABLE,
        },
    ),
    (
        (22, 6),
        (22, 7),
        {
            ATTR_SIGN: SIGN_CANCER,
            ATTR_ELEMENT: ELEMENT_WATER,
            ATTR_MODALITY: MODALITY_CARDINAL,
        },
    ),
    (
        (23, 7),
        (22, 8),
        {
            ATTR_SIGN: SIGN_LEO,
            ATTR_ELEMENT: ELEMENT_FIRE,
            ATTR_MODALITY: MODALITY_FIXED,
        },
    ),
    (
        (23, 8),
        (21, 9),
        {
            ATTR_SIGN: SIGN_VIRGO,
            ATTR_ELEMENT: ELEMENT_EARTH,
            ATTR_MODALITY: MODALITY_MUTABLE,
        },
    ),
    (
        (22, 9),
        (22, 10),
        {
            ATTR_SIGN: SIGN_LIBRA,
            ATTR_ELEMENT: ELEMENT_AIR,
            ATTR_MODALITY: MODALITY_CARDINAL,
        },
    ),
    (
        (23, 10),
        (22, 11),
        {
            ATTR_SIGN: SIGN_SCORPIO,
            ATTR_ELEMENT: ELEMENT_WATER,
            ATTR_MODALITY: MODALITY_FIXED,
        },
    ),
    (
        (23, 11),
        (21, 12),
        {
            ATTR_SIGN: SIGN_SAGITTARIUS,
            ATTR_ELEMENT: ELEMENT_FIRE,
            ATTR_MODALITY: MODALITY_MUTABLE,
        },
    ),
    (
        (22, 12),
        (20, 1),
        {
            ATTR_SIGN: SIGN_CAPRICORN,
            ATTR_ELEMENT: ELEMENT_EARTH,
            ATTR_MODALITY: MODALITY_CARDINAL,
        },
    ),
    (
        (21, 1),
        (19, 2),
        {
            ATTR_SIGN: SIGN_AQUARIUS,
            ATTR_ELEMENT: ELEMENT_AIR,
            ATTR_MODALITY: MODALITY_FIXED,
        },
    ),
    (
        (20, 2),
        (20, 3),
        {
            ATTR_SIGN: SIGN_PISCES,
            ATTR_ELEMENT: ELEMENT_WATER,
            ATTR_MODALITY: MODALITY_MUTABLE,
        },
    ),
)

ZODIAC_ICONS = {
    SIGN_ARIES: "mdi:zodiac-aries",
    SIGN_TAURUS: "mdi:zodiac-taurus",
    SIGN_GEMINI: "mdi:zodiac-gemini",
    SIGN_CANCER: "mdi:zodiac-cancer",
    SIGN_LEO: "mdi:zodiac-leo",
    SIGN_VIRGO: "mdi:zodiac-virgo",
    SIGN_LIBRA: "mdi:zodiac-libra",
    SIGN_SCORPIO: "mdi:zodiac-scorpio",
    SIGN_SAGITTARIUS: "mdi:zodiac-sagittarius",
    SIGN_CAPRICORN: "mdi:zodiac-capricorn",
    SIGN_AQUARIUS: "mdi:zodiac-aquarius",
    SIGN_PISCES: "mdi:zodiac-pisces",
}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Zodiac sensor platform."""
    async_add_entities([ZodiacSensor()], True)


class ZodiacSensor(Entity):
    """Representation of a Zodiac sensor."""

    def __init__(self):
        """Initialize the zodiac sensor."""
        self._attrs = None

    @property
    def name(self):
        """Return the name of the entity."""
        return "Zodiac"

    @property
    def device_class(self):
        """Return the device class of the entity."""
        return "zodiac__sign"

    @property
    def state(self):
        """Return the state of the device."""
        return self._attrs[STATE_ATTR]

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return ZODIAC_ICONS.get(self._attrs[STATE_ATTR])

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attrs

    async def async_update(self):
        """Get the time and updates the state."""
        today = dt_util.as_local(dt_util.utcnow()).date()

        month = int(today.month)
        day = int(today.day)

        for _, sign in enumerate(ZODIAC_BY_DATE):
            if (month == sign[0][1] and day >= sign[0][0]) or (
                month == sign[1][1] and day <= sign[1][0]
            ):
                self._attrs = sign[2]
                break
