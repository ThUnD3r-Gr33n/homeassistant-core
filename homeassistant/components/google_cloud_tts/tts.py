"""Support for the Google Cloud TTS service."""
import logging
import os
import asyncio
import async_timeout
import voluptuous as vol
from google.cloud import texttospeech
from homeassistant.components.tts import CONF_LANG, PLATFORM_SCHEMA, Provider
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

GENDERS = [
    'Neutral', 'Female', 'Male',
]
DEFAULT_GENDER = GENDERS[0]

SUPPORT_LANGUAGES = [
    'en', 'da', 'nl', 'fr', 'de', 'it', 'ja', 'ko', 'nb',
    'pl', 'pt', 'ru', 'sk', 'es', 'sv', 'tr', 'uk',
]
DEFAULT_LANG = SUPPORT_LANGUAGES[0]

CONF_GENDER = 'gender'
CONF_VOICE = 'voice'
CONF_KEY_FILE = 'key_file'
GOOGLE_APPLICATION_CREDENTIALS = 'GOOGLE_APPLICATION_CREDENTIALS'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_LANG, default=DEFAULT_LANG): vol.In(SUPPORT_LANGUAGES),
    vol.Optional(CONF_GENDER, default=DEFAULT_GENDER): vol.In(GENDERS),
    vol.Optional(CONF_VOICE, default=''): cv.string,
    vol.Optional(CONF_KEY_FILE, default=''): cv.string,
})


async def async_get_engine(hass, config):
    """Set up Google Cloud TTS component."""
    return GoogleCloudTTSProvider(
        hass,
        config[CONF_KEY_FILE],
        config[CONF_LANG],
        config[CONF_GENDER],
        config[CONF_VOICE]
    )


class GoogleCloudTTSProvider(Provider):
    """The Google Cloud TTS API provider."""

    def __init__(self, hass, key_file, lang, gender, voice):
        """Init Google Cloud TTS service."""
        self.hass = hass
        self._lang = lang
        self._gender = gender
        self._voice = voice
        self.name = 'Google Cloud TTS'
        path = hass.config.path(key_file)
        if key_file and os.path.isfile(path):
            os.environ[GOOGLE_APPLICATION_CREDENTIALS] = path
        if GOOGLE_APPLICATION_CREDENTIALS not in os.environ:
            _LOGGER.error(
                "You need to specify valid"
                " GOOGLE_APPLICATION_CREDENTIALS file location."
            )
        self.client = texttospeech.TextToSpeechClient()
        self.audio_config = texttospeech.types.AudioConfig(
            audio_encoding=texttospeech.enums.AudioEncoding.MP3
        )

    @property
    def default_language(self):
        """Return the default language."""
        return self._lang

    @property
    def supported_languages(self):
        """Return list of supported languages."""
        return SUPPORT_LANGUAGES

    @property
    def supported_options(self):
        """Return a list of supported options."""
        return ["voice", "gender"]

    async def async_get_tts_audio(self, message, language, options=None):
        """Load TTS from google."""
        try:
            with async_timeout.timeout(10, loop=self.hass.loop):
                _language = language or self._lang
                _gender = self._gender
                _voice = self._voice
                if options:
                    if CONF_GENDER in options:
                        _gender = options[CONF_GENDER].lower().capitalize()
                    if CONF_VOICE in options:
                        _voice = options[CONF_VOICE]
                voice = texttospeech.types.VoiceSelectionParams(
                    language_code=_language,
                    ssml_gender={
                        'Neutral': texttospeech.enums.SsmlVoiceGender.NEUTRAL,
                        'Female': texttospeech.enums.SsmlVoiceGender.FEMALE,
                        'Male': texttospeech.enums.SsmlVoiceGender.MALE,
                    }.get(_gender, DEFAULT_GENDER),
                    name=_voice
                )
                synthesis_input = texttospeech.types.SynthesisInput(
                    text=message
                )
                response = self.client.synthesize_speech(
                    synthesis_input,
                    voice,
                    self.audio_config
                )
                return "mp3", response.audio_content

        except asyncio.TimeoutError as ex:
            _LOGGER.error("Timeout for Google Cloud TTS: %s", ex)
        except Exception as ex:
            _LOGGER.error("Error occured during Google Cloud TTS call: %s", ex)

        return None, None
