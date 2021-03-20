"""Test util methods."""
from datetime import timedelta
import os
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.components.recorder import util
from homeassistant.components.recorder.const import DATA_INSTANCE, SQLITE_URL_PREFIX
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.util import dt as dt_util

from .common import corrupt_db_file

from tests.common import (
    async_init_recorder_component,
    get_test_home_assistant,
    init_recorder_component,
)


@pytest.fixture
def hass_recorder():
    """Home Assistant fixture with in-memory recorder."""
    hass = get_test_home_assistant()

    def setup_recorder(config=None):
        """Set up with params."""
        init_recorder_component(hass, config)
        hass.start()
        hass.block_till_done()
        hass.data[DATA_INSTANCE].block_till_done()
        return hass

    yield setup_recorder
    hass.stop()


def test_recorder_bad_commit(hass_recorder):
    """Bad _commit should retry 3 times."""
    hass = hass_recorder()

    def work(session):
        """Bad work."""
        session.execute("select * from notthere")

    with patch(
        "homeassistant.components.recorder.time.sleep"
    ) as e_mock, util.session_scope(hass=hass) as session:
        res = util.commit(session, work)
    assert res is False
    assert e_mock.call_count == 3


def test_recorder_bad_execute(hass_recorder):
    """Bad execute, retry 3 times."""
    from sqlalchemy.exc import SQLAlchemyError

    hass_recorder()

    def to_native(validate_entity_id=True):
        """Raise exception."""
        raise SQLAlchemyError()

    mck1 = MagicMock()
    mck1.to_native = to_native

    with pytest.raises(SQLAlchemyError), patch(
        "homeassistant.components.recorder.time.sleep"
    ) as e_mock:
        util.execute((mck1,), to_native=True)

    assert e_mock.call_count == 2


def test_validate_or_move_away_sqlite_database_with_integrity_check(
    hass, tmpdir, caplog
):
    """Ensure a malformed sqlite database is moved away.

    A quick_check is run here
    """

    db_integrity_check = True

    test_dir = tmpdir.mkdir("test_validate_or_move_away_sqlite_database")
    test_db_file = f"{test_dir}/broken.db"
    dburl = f"{SQLITE_URL_PREFIX}{test_db_file}"

    assert util.validate_sqlite_database(test_db_file, db_integrity_check) is False
    assert os.path.exists(test_db_file) is True
    assert (
        util.validate_or_move_away_sqlite_database(dburl, db_integrity_check) is False
    )

    corrupt_db_file(test_db_file)

    assert util.validate_sqlite_database(dburl, db_integrity_check) is False

    assert (
        util.validate_or_move_away_sqlite_database(dburl, db_integrity_check) is False
    )

    assert "corrupt or malformed" in caplog.text

    assert util.validate_sqlite_database(dburl, db_integrity_check) is False

    assert util.validate_or_move_away_sqlite_database(dburl, db_integrity_check) is True


def test_validate_or_move_away_sqlite_database_without_integrity_check(
    hass, tmpdir, caplog
):
    """Ensure a malformed sqlite database is moved away.

    The quick_check is skipped, but we can still find
    corruption if the whole database is unreadable
    """

    db_integrity_check = False

    test_dir = tmpdir.mkdir("test_validate_or_move_away_sqlite_database")
    test_db_file = f"{test_dir}/broken.db"
    dburl = f"{SQLITE_URL_PREFIX}{test_db_file}"

    assert util.validate_sqlite_database(test_db_file, db_integrity_check) is False
    assert os.path.exists(test_db_file) is True
    assert (
        util.validate_or_move_away_sqlite_database(dburl, db_integrity_check) is False
    )

    corrupt_db_file(test_db_file)

    assert util.validate_sqlite_database(dburl, db_integrity_check) is False

    assert (
        util.validate_or_move_away_sqlite_database(dburl, db_integrity_check) is False
    )

    assert "corrupt or malformed" in caplog.text

    assert util.validate_sqlite_database(dburl, db_integrity_check) is False

    assert util.validate_or_move_away_sqlite_database(dburl, db_integrity_check) is True


async def test_last_run_was_recently_clean(hass):
    """Test we can check if the last recorder run was recently clean."""
    await async_init_recorder_component(hass)
    await hass.async_block_till_done()

    cursor = hass.data[DATA_INSTANCE].engine.raw_connection().cursor()

    assert (
        await hass.async_add_executor_job(util.last_run_was_recently_clean, cursor)
        is False
    )

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()

    assert (
        await hass.async_add_executor_job(util.last_run_was_recently_clean, cursor)
        is True
    )

    thirty_min_future_time = dt_util.utcnow() + timedelta(minutes=30)

    with patch(
        "homeassistant.components.recorder.dt_util.utcnow",
        return_value=thirty_min_future_time,
    ):
        assert (
            await hass.async_add_executor_job(util.last_run_was_recently_clean, cursor)
            is False
        )


def test_basic_sanity_check(hass_recorder):
    """Test the basic sanity checks with a missing table."""
    hass = hass_recorder()

    cursor = hass.data[DATA_INSTANCE].engine.raw_connection().cursor()

    assert util.basic_sanity_check(cursor) is True

    cursor.execute("DROP TABLE states;")

    with pytest.raises(sqlite3.DatabaseError):
        util.basic_sanity_check(cursor)


def test_combined_checks(hass_recorder):
    """Run Checks on the open database."""
    hass = hass_recorder()

    db_integrity_check = False

    cursor = hass.data[DATA_INSTANCE].engine.raw_connection().cursor()

    assert (
        util.run_checks_on_open_db("fake_db_path", cursor, db_integrity_check) is None
    )

    # We are patching recorder.util here in order
    # to avoid creating the full database on disk
    with patch("homeassistant.components.recorder.util.last_run_was_recently_clean"):
        assert (
            util.run_checks_on_open_db("fake_db_path", cursor, db_integrity_check)
            is None
        )

    with patch(
        "homeassistant.components.recorder.util.last_run_was_recently_clean",
        side_effect=sqlite3.DatabaseError,
    ), pytest.raises(sqlite3.DatabaseError):
        util.run_checks_on_open_db("fake_db_path", cursor, db_integrity_check)

    cursor.execute("DROP TABLE events;")

    with pytest.raises(sqlite3.DatabaseError):
        util.run_checks_on_open_db("fake_db_path", cursor, True)
