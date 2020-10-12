"""Base class for fritzbox_callmonitor entities."""
import re

from fritzconnection.lib.fritzphonebook import FritzPhonebook

from homeassistant.util import Throttle

from .const import LOGGER, MIN_TIME_PHONEBOOK_UPDATE


class FritzBoxPhonebook:
    """This connects to a FritzBox router and downloads its phone book."""

    def __init__(self, host, port, username, password, phonebook_id, prefixes):
        """Initialize the class."""
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.phonebook_id = phonebook_id
        self.phonebook_dict = None
        self.number_dict = None
        self.prefixes = prefixes

        # Establish a connection to the FRITZ!Box.
        self.fph = FritzPhonebook(
            address=self.host, user=self.username, password=self.password
        )

        if self.phonebook_id not in self.fph.list_phonebooks:
            raise ValueError("Phonebook with this ID not found.")

        self.update_phonebook()

    @Throttle(MIN_TIME_PHONEBOOK_UPDATE)
    def update_phonebook(self):
        """Update the phone book dictionary."""
        self.phonebook_dict = self.fph.get_all_names(self.phonebook_id)
        self.number_dict = {
            re.sub(r"[^\d\+]", "", nr): name
            for name, nrs in self.phonebook_dict.items()
            for nr in nrs
        }
        LOGGER.info("Fritz!Box phone book successfully updated")

    def get_name(self, number):
        """Return a name for a given phone number."""
        number = re.sub(r"[^\d\+]", "", str(number))
        if self.number_dict is None:
            return "unknown"
        try:
            return self.number_dict[number]
        except KeyError:
            pass

        if not self.prefixes:
            return "unknown"

        for prefix in self.prefixes:
            try:
                return self.number_dict[prefix + number]
            except KeyError:
                pass
            try:
                return self.number_dict[prefix + number.lstrip("0")]
            except KeyError:
                pass
