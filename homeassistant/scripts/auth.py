"""Script to manage users for the Home Assistant auth provider."""
import argparse
import asyncio
import logging
import os

from homeassistant.auth import auth_manager_from_config
from homeassistant.core import HomeAssistant
from homeassistant.config import get_default_config_dir
from homeassistant.auth.providers import homeassistant as hass_auth


def run(args):
    """Handle Home Assistant auth provider script."""
    parser = argparse.ArgumentParser(
        description=("Manage Home Assistant users"))
    parser.add_argument(
        '--script', choices=['auth'])
    parser.add_argument(
        '-c', '--config',
        default=get_default_config_dir(),
        help="Directory that contains the Home Assistant configuration")

    subparsers = parser.add_subparsers(dest='func')
    subparsers.required = True
    parser_list = subparsers.add_parser('list')
    parser_list.set_defaults(func=list_users)

    parser_add = subparsers.add_parser('add')
    parser_add.add_argument('username', type=str)
    parser_add.add_argument('password', type=str)
    parser_add.set_defaults(func=add_user)

    parser_validate_login = subparsers.add_parser('validate')
    parser_validate_login.add_argument('username', type=str)
    parser_validate_login.add_argument('password', type=str)
    parser_validate_login.set_defaults(func=validate_login)

    parser_change_pw = subparsers.add_parser('change_password')
    parser_change_pw.add_argument('username', type=str)
    parser_change_pw.add_argument('new_password', type=str)
    parser_change_pw.set_defaults(func=change_password)

    args = parser.parse_args(args)
    loop = asyncio.get_event_loop()
    hass = HomeAssistant(loop=loop)
    loop.run_until_complete(run_command(hass, args))

    # Triggers save on used storage helpers with delay (core auth)
    logging.getLogger('homeassistant.core').setLevel(logging.WARNING)
    loop.run_until_complete(hass.async_stop())


async def run_command(hass, args):
    """Run the command."""
    hass.config.config_dir = os.path.join(os.getcwd(), args.config)
    hass.auth = await auth_manager_from_config(hass, [{
        'type': 'homeassistant',
    }])
    provider = hass.auth.auth_providers[0]
    await provider._async_initialize()
    await args.func(hass, provider, provider._data, args)


async def list_users(hass, provider, data, args):
    """List the users."""
    count = 0
    for user in data.users:
        count += 1
        print(user['username'])

    print()
    print("Total users:", count)


async def add_user(hass, provider, data, args):
    """Create a user."""
    try:
        data.add_auth(args.username, args.password)
    except hass_auth.InvalidUser:
        print("Username already exists!")
        return

    credentials = await provider.async_get_or_create_credentials({
        'username': args.username
    })

    user = await hass.auth.async_create_user(args.username)
    await hass.auth.async_link_user(user, credentials)

    # Save username/password
    await data.async_save()
    print("User created")


async def validate_login(hass, provider, data, args):
    """Validate a login."""
    try:
        data.validate_login(args.username, args.password)
        print("Auth valid")
    except hass_auth.InvalidAuth:
        print("Auth invalid")


async def change_password(hass, provider, data, args):
    """Change password."""
    try:
        data.change_password(args.username, args.new_password)
        await data.async_save()
        print("Password changed")
    except hass_auth.InvalidUser:
        print("User not found")
