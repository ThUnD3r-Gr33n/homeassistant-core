"""The exceptions used by Home Assistant."""
from typing import Optional, Tuple, TYPE_CHECKING
import jinja2

# pylint: disable=using-constant-test
if TYPE_CHECKING:
    from .core import Context  # noqa


class HomeAssistantError(Exception):
    """General Home Assistant exception occurred."""


class InvalidEntityFormatError(HomeAssistantError):
    """When an invalid formatted entity is encountered."""


class NoEntitySpecifiedError(HomeAssistantError):
    """When no entity is specified."""


class TemplateError(HomeAssistantError):
    """Error during template rendering."""

    def __init__(self, exception: jinja2.TemplateError) -> None:
        """Init the error."""
        super().__init__('{}: {}'.format(exception.__class__.__name__,
                                         exception))


class PlatformNotReady(HomeAssistantError):
    """Error to indicate that platform is not ready."""


class ConfigEntryNotReady(HomeAssistantError):
    """Error to indicate that config entry is not ready."""


class InvalidStateError(HomeAssistantError):
    """When an invalid state is encountered."""


class Unauthorized(HomeAssistantError):
    """When an action is unauthorized."""

    def __init__(self, context: Optional['Context'] = None,
                 user_id: Optional[str] = None,
                 entity_id: Optional[str] = None,
                 permission: Optional[Tuple[str]] = None) -> None:
        """Unauthorized error."""
        super().__init__(self.__class__.__name__)
        self.context = context
        self.user_id = user_id
        self.entity_id = entity_id
        self.permission = permission


class UnknownUser(Unauthorized):
    """When call is made with user ID that doesn't exist."""
