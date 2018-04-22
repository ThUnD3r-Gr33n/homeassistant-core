"""Example auth provider."""
from collections import OrderedDict
import hmac

import voluptuous as vol

from homeassistant import auth, data_entry_flow
from homeassistant.core import callback


USER_SCHEMA = vol.Schema({
    vol.Required('username'): str,
    vol.Required('password'): str,
    vol.Optional('name'): str,
})


CONFIG_SCHEMA = auth.AUTH_PROVIDER_SCHEMA.extend({
    vol.Required('users'): [USER_SCHEMA]
}, extra=vol.PREVENT_EXTRA)


@auth.AUTH_PROVIDERS.register('insecure_example')
class ExampleAuthProvider(auth.AuthProvider):
    """Example auth provider based on hardcoded usernames and passwords."""

    async def async_credential_flow(self):
        """Return a flow to login."""
        return LoginFlow(self)

    @callback
    def async_validate_login(self, username, password):
        """Helper to validate a username and password."""
        user = None

        # Compare all users to avoid timing attacks.
        for usr in self.config['users']:
            if hmac.compare_digest(username, usr['username']):
                user = usr

        if user is None:
            # Do one more compare to make timing the same as if user was found.
            hmac.compare_digest(password, password)
            raise auth.InvalidUser

        if not hmac.compare_digest(user['password'], password):
            raise auth.InvalidPassword

    async def async_get_or_create_credentials(self, flow_result):
        """Get credentials based on the flow result."""
        username = flow_result['username']
        password = flow_result['password']

        self.async_validate_login(username, password)

        for credential in await self.async_credentials():
            if credential.data['username'] == username:
                return credential

        # Create new credentials.
        return self.async_create_credentials({
            'username': username
        })

    async def async_user_meta_for_credentials(self, credentials):
        """Return extra user metadata for credentials.

        Will be used to populate info when creating a new user.
        """
        username = credentials.data['username']

        for user in self.config['users']:
            if user['username'] == username:
                return {
                    'name': user.get('name')
                }

        return {}


class LoginFlow(data_entry_flow.FlowHandler):
    """Handler for the login flow."""

    def __init__(self, auth_provider):
        """Initialize the login flow."""
        self._auth_provider = auth_provider

    async def async_step_init(self, user_input=None):
        """Handle the step of the form."""
        errors = {}

        if user_input is not None:
            try:
                self._auth_provider.async_validate_login(
                    user_input['username'], user_input['password'])
            except auth.InvalidUser:
                errors['username'] = 'Invalid username'
            except auth.InvalidPassword:
                errors['password'] = 'Invalid password'

            if not errors:
                return self.async_create_entry(
                    title=self._auth_provider.name,
                    data=user_input
                )

        schema = OrderedDict()
        schema['username'] = str
        schema['password'] = str

        return self.async_show_form(
            step_id='init',
            data_schema=vol.Schema(schema),
            errors=errors,
        )
