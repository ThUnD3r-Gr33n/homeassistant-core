"""Schema migration helpers."""
import logging
import os

from sqlalchemy import Table, text
from sqlalchemy.engine import reflection
from sqlalchemy.exc import InternalError, OperationalError, SQLAlchemyError

from .models import SCHEMA_VERSION, Base, SchemaChanges
from .util import session_scope
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def migrate_schema(instance):
    """Check if the schema needs to be upgraded."""
    with session_scope(session=instance.get_session()) as session:
        res = (
            session.query(SchemaChanges)
            .order_by(SchemaChanges.change_id.desc())
            .first()
        )
        current_version = getattr(res, "schema_version", None)

        if current_version is None:
            current_version = _inspect_schema_version(instance.engine, session)
            _LOGGER.debug(
                "No schema version found. Inspected version: %s", current_version
            )

        if current_version == SCHEMA_VERSION:
            return

        _LOGGER.warning(
            "Database is about to upgrade. Schema version: %s", current_version
        )

        with instance.hass.timeout.freeze(zone_name=DOMAIN):
            for version in range(current_version, SCHEMA_VERSION):
                new_version = version + 1
                _LOGGER.info("Upgrading recorder db schema to version %s", new_version)
                _apply_update(instance.engine, new_version, current_version)
                session.add(SchemaChanges(schema_version=new_version))

                _LOGGER.info("Upgrade to version %s done", new_version)


def _create_index(engine, table_name, index_name):
    """Create an index for the specified table.

    The index name should match the name given for the index
    within the table definition described in the models
    """
    table = Table(table_name, Base.metadata)
    _LOGGER.debug("Looking up index %s for table %s", index_name, table_name)
    # Look up the index object by name from the table is the models
    index_list = [idx for idx in table.indexes if idx.name == index_name]
    if not index_list:
        _LOGGER.debug("The index %s no longer exists", index_name)
        return
    index = index_list[0]
    _LOGGER.debug("Creating %s index", index_name)
    _LOGGER.warning(
        "Adding index `%s` to database. Note: this can take several "
        "minutes on large databases and slow computers. Please "
        "be patient!",
        index_name,
    )
    try:
        index.create(engine)
    except OperationalError as err:
        lower_err_str = str(err).lower()

        if "already exists" not in lower_err_str and "duplicate" not in lower_err_str:
            raise

        _LOGGER.warning(
            "Index %s already exists on %s, continuing", index_name, table_name
        )
    except InternalError as err:
        if "duplicate" not in str(err).lower():
            raise

        _LOGGER.warning(
            "Index %s already exists on %s, continuing", index_name, table_name
        )

    _LOGGER.debug("Finished creating %s", index_name)


def _drop_index(engine, table_name, index_name):
    """Drop an index from a specified table.

    There is no universal way to do something like `DROP INDEX IF EXISTS`
    so we will simply execute the DROP command and ignore any exceptions

    WARNING: Due to some engines (MySQL at least) being unable to use bind
    parameters in a DROP INDEX statement (at least via SQLAlchemy), the query
    string here is generated from the method parameters without sanitizing.
    DO NOT USE THIS FUNCTION IN ANY OPERATION THAT TAKES USER INPUT.
    """
    _LOGGER.debug("Dropping index %s from table %s", index_name, table_name)
    success = False

    # Engines like DB2/Oracle
    try:
        engine.execute(text(f"DROP INDEX {index_name}"))
    except SQLAlchemyError:
        pass
    else:
        success = True

    # Engines like SQLite, SQL Server
    if not success:
        try:
            engine.execute(
                text(
                    "DROP INDEX {table}.{index}".format(
                        index=index_name, table=table_name
                    )
                )
            )
        except SQLAlchemyError:
            pass
        else:
            success = True

    if not success:
        # Engines like MySQL, MS Access
        try:
            engine.execute(
                text(
                    "DROP INDEX {index} ON {table}".format(
                        index=index_name, table=table_name
                    )
                )
            )
        except SQLAlchemyError:
            pass
        else:
            success = True

    if success:
        _LOGGER.debug(
            "Finished dropping index %s from table %s", index_name, table_name
        )
    else:
        if index_name == "ix_states_context_parent_id":
            # Was only there on nightly so we do not want
            # to generate log noise or issues about it.
            return

        _LOGGER.warning(
            "Failed to drop index %s from table %s. Schema "
            "Migration will continue; this is not a "
            "critical operation",
            index_name,
            table_name,
        )


def _add_columns(engine, table_name, columns_def):
    """Add columns to a table."""
    _LOGGER.warning(
        "Adding columns %s to table %s. Note: this can take several "
        "minutes on large databases and slow computers. Please "
        "be patient!",
        ", ".join(column.split(" ")[0] for column in columns_def),
        table_name,
    )

    columns_def = [f"ADD {col_def}" for col_def in columns_def]

    try:
        engine.execute(
            text(
                "ALTER TABLE {table} {columns_def}".format(
                    table=table_name, columns_def=", ".join(columns_def)
                )
            )
        )
        return
    except (InternalError, OperationalError):
        # Some engines support adding all columns at once,
        # this error is when they don't
        _LOGGER.info("Unable to use quick column add. Adding 1 by 1")

    for column_def in columns_def:
        try:
            engine.execute(
                text(
                    "ALTER TABLE {table} {column_def}".format(
                        table=table_name, column_def=column_def
                    )
                )
            )
        except (InternalError, OperationalError) as err:
            if "duplicate" not in str(err).lower():
                raise

            _LOGGER.warning(
                "Column %s already exists on %s, continuing",
                column_def.split(" ")[1],
                table_name,
            )


def _apply_update(engine, new_version, old_version):
    """Perform operations to bring schema up to date."""
    if new_version == 1:
        _create_index(engine, "events", "ix_events_time_fired")
    elif new_version == 2:
        # Create compound start/end index for recorder_runs
        _create_index(engine, "recorder_runs", "ix_recorder_runs_start_end")
        # Create indexes for states
        _create_index(engine, "states", "ix_states_last_updated")
    elif new_version == 3:
        # There used to be a new index here, but it was removed in version 4.
        pass
    elif new_version == 4:
        # Queries were rewritten in this schema release. Most indexes from
        # earlier versions of the schema are no longer needed.

        if old_version == 3:
            # Remove index that was added in version 3
            _drop_index(engine, "states", "ix_states_created_domain")
        if old_version == 2:
            # Remove index that was added in version 2
            _drop_index(engine, "states", "ix_states_entity_id_created")

        # Remove indexes that were added in version 0
        _drop_index(engine, "states", "states__state_changes")
        _drop_index(engine, "states", "states__significant_changes")
        _drop_index(engine, "states", "ix_states_entity_id_created")

        _create_index(engine, "states", "ix_states_entity_id_last_updated")
    elif new_version == 5:
        # Create supporting index for States.event_id foreign key
        _create_index(engine, "states", "ix_states_event_id")
    elif new_version == 6:
        _add_columns(
            engine,
            "events",
            ["context_id CHARACTER(36)", "context_user_id CHARACTER(36)"],
        )
        _create_index(engine, "events", "ix_events_context_id")
        _create_index(engine, "events", "ix_events_context_user_id")
        _add_columns(
            engine,
            "states",
            ["context_id CHARACTER(36)", "context_user_id CHARACTER(36)"],
        )
        _create_index(engine, "states", "ix_states_context_id")
        _create_index(engine, "states", "ix_states_context_user_id")
    elif new_version == 7:
        _create_index(engine, "states", "ix_states_entity_id")
    elif new_version == 8:
        _add_columns(engine, "events", ["context_parent_id CHARACTER(36)"])
        _add_columns(engine, "states", ["old_state_id INTEGER"])
        _create_index(engine, "events", "ix_events_context_parent_id")
    elif new_version == 9:
        # We now get the context from events with a join
        # since its always there on state_changed events
        #
        # Ideally we would drop the columns from the states
        # table as well but sqlite doesn't support that
        # and we would have to move to something like
        # sqlalchemy alembic to make that work
        #
        _drop_index(engine, "states", "ix_states_context_id")
        _drop_index(engine, "states", "ix_states_context_user_id")
        # This index won't be there if they were not running
        # nightly but we don't treat that as a critical issue
        _drop_index(engine, "states", "ix_states_context_parent_id")
        # Redundant keys on composite index:
        # We already have ix_states_entity_id_last_updated
        _drop_index(engine, "states", "ix_states_entity_id")
        _create_index(engine, "events", "ix_events_event_type_time_fired")
        _drop_index(engine, "events", "ix_events_event_type")
    else:
        raise ValueError(f"No schema migration defined for version {new_version}")


def _inspect_schema_version(engine, session):
    """Determine the schema version by inspecting the db structure.

    When the schema version is not present in the db, either db was just
    created with the correct schema, or this is a db created before schema
    versions were tracked. For now, we'll test if the changes for schema
    version 1 are present to make the determination. Eventually this logic
    can be removed and we can assume a new db is being created.
    """
    inspector = reflection.Inspector.from_engine(engine)
    indexes = inspector.get_indexes("events")

    for index in indexes:
        if index["column_names"] == ["time_fired"]:
            # Schema addition from version 1 detected. New DB.
            session.add(SchemaChanges(schema_version=SCHEMA_VERSION))
            return SCHEMA_VERSION

    # Version 1 schema changes not found, this db needs to be migrated.
    current_version = SchemaChanges(schema_version=0)
    session.add(current_version)
    return current_version.schema_version
