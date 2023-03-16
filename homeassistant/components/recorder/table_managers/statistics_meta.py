"""Support managing StatesMeta."""
from __future__ import annotations

from collections.abc import Callable
import logging
import threading
from typing import TYPE_CHECKING, Literal, cast

from sqlalchemy import lambda_stmt, select
from sqlalchemy.orm.session import Session
from sqlalchemy.sql.expression import true
from sqlalchemy.sql.lambdas import StatementLambdaElement

from ..db_schema import StatisticsMeta
from ..models import StatisticMetaData
from ..util import execute_stmt_lambda_element

if TYPE_CHECKING:
    from ..core import Recorder

CACHE_SIZE = 8192

_LOGGER = logging.getLogger(__name__)

QUERY_STATISTIC_META = (
    StatisticsMeta.id,
    StatisticsMeta.statistic_id,
    StatisticsMeta.source,
    StatisticsMeta.unit_of_measurement,
    StatisticsMeta.has_mean,
    StatisticsMeta.has_sum,
    StatisticsMeta.name,
)


def _generate_get_metadata_stmt(
    statistic_ids: list[str] | None = None,
    statistic_type: Literal["mean"] | Literal["sum"] | None = None,
    statistic_source: str | None = None,
) -> StatementLambdaElement:
    """Generate a statement to fetch metadata."""
    stmt = lambda_stmt(lambda: select(*QUERY_STATISTIC_META))
    if statistic_ids:
        stmt += lambda q: q.where(
            # https://github.com/python/mypy/issues/2608
            StatisticsMeta.statistic_id.in_(statistic_ids)  # type:ignore[arg-type]
        )
    if statistic_source is not None:
        stmt += lambda q: q.where(StatisticsMeta.source == statistic_source)
    if statistic_type == "mean":
        stmt += lambda q: q.where(StatisticsMeta.has_mean == true())
    elif statistic_type == "sum":
        stmt += lambda q: q.where(StatisticsMeta.has_sum == true())
    return stmt


def _generate_filter(
    statistic_type: Literal["mean"] | Literal["sum"] | None = None,
    statistic_source: str | None = None,
) -> Callable[[tuple[int, StatisticMetaData]], bool]:
    """Generate a filter function for metadata."""
    if not statistic_type and not statistic_source:
        return lambda _: True

    def _filter(id_meta: tuple[int, StatisticMetaData]) -> bool:
        meta = id_meta[1]
        if statistic_source is not None and meta["source"] != statistic_source:
            return False
        if statistic_type == "mean" and not meta["has_mean"]:
            return False
        if statistic_type == "sum" and not meta["has_sum"]:
            return False
        return True

    return _filter


def _statistics_meta_to_id_statistics_metadata(
    meta: StatisticsMeta,
) -> tuple[int, StatisticMetaData]:
    """Convert StatisticsMeta tuple of metadata_id and StatisticMetaData."""
    return (
        meta.id,
        {
            "has_mean": meta.has_mean,  # type: ignore[typeddict-item]
            "has_sum": meta.has_sum,  # type: ignore[typeddict-item]
            "name": meta.name,
            "source": meta.source,  # type: ignore[typeddict-item]
            "statistic_id": meta.statistic_id,  # type: ignore[typeddict-item]
            "unit_of_measurement": meta.unit_of_measurement,
        },
    )


class StatisticsMetaManager:
    """Manage the StatisticsMeta table."""

    def __init__(self, recorder: Recorder) -> None:
        """Initialize the statistics meta manager."""
        self.recorder = recorder
        self._stat_id_to_id_meta: dict[str, tuple[int, StatisticMetaData]] = {}

    def load(self, session: Session) -> None:
        """Load the statistic_id to metadata_id mapping into memory.

        This call is not thread-safe and must be called from the
        recorder thread.
        """
        self.get_many(session)

    def get(
        self, session: Session, statistic_id: str
    ) -> tuple[int, StatisticMetaData] | None:
        """Resolve statistic_id to the metadata_id."""
        return self.get_many(session, [statistic_id]).get(statistic_id)

    def get_many(
        self,
        session: Session,
        statistic_ids: list[str] | None = None,
        statistic_type: Literal["mean"] | Literal["sum"] | None = None,
        statistic_source: str | None = None,
    ) -> dict[str, tuple[int, StatisticMetaData]]:
        """Fetch meta data.

        Returns a dict of (metadata_id, StatisticMetaData) tuples indexed by statistic_id.

        If statistic_ids is given, fetch metadata only for the listed statistics_ids.
        If statistic_type is given, fetch metadata only for statistic_ids supporting it.

        This call is not thread-safe after startup since
        purge can remove all references to an entity_id.

        When calling this method from the recorder thread, set
        from_recorder to True to ensure any missing entity_ids
        are added to the cache.
        """
        results: dict[str, tuple[int, StatisticMetaData]] = {}

        if statistic_ids is None:
            # Fetch metadata from the database
            self._process_into_results(
                results,
                session,
                statistic_ids,
                statistic_type,
                statistic_source,
            )
            return results

        missing: list[str] = []
        _filter = _generate_filter(statistic_type, statistic_source)
        for statistic_id in statistic_ids:
            id_meta = self._stat_id_to_id_meta.get(statistic_id)
            if id_meta is None:
                missing.append(statistic_id)
            elif _filter(id_meta):
                results[statistic_id] = id_meta

        if not missing:
            return results

        # Fetch metadata from the database
        self._process_into_results(
            results,
            session,
            missing,
            statistic_type,
            statistic_source,
        )

        return results

    def _process_into_results(
        self,
        results: dict[str, tuple[int, StatisticMetaData]],
        session: Session,
        statistic_ids: list[str] | None = None,
        statistic_type: Literal["mean"] | Literal["sum"] | None = None,
        statistic_source: str | None = None,
    ) -> None:
        """Fetch meta data and process it into results and/or cache."""
        # Only update the cache if we are in the recorder thread
        update_cache = self.recorder.thread_id == threading.get_ident()
        with session.no_autoflush:
            stat_id_to_id_meta = self._stat_id_to_id_meta
            for row in execute_stmt_lambda_element(
                session,
                _generate_get_metadata_stmt(
                    statistic_ids, statistic_type, statistic_source
                ),
            ):
                id_meta = _statistics_meta_to_id_statistics_metadata(
                    cast(StatisticsMeta, row)
                )
                statistic_id = row.statistic_id
                results[statistic_id] = id_meta
                if update_cache:
                    stat_id_to_id_meta[statistic_id] = id_meta

    def _add_metadata(
        self, session: Session, statistic_id: str, new_metadata: StatisticMetaData
    ) -> int:
        """Add metadata to the database."""
        meta = StatisticsMeta.from_meta(new_metadata)
        session.add(meta)
        session.flush()  # Flush to get the metadata id assigned
        _LOGGER.debug(
            "Added new statistics metadata for %s, new_metadata: %s",
            statistic_id,
            new_metadata,
        )
        if self.recorder.thread_id == threading.get_ident():
            id_meta = _statistics_meta_to_id_statistics_metadata(meta)
            self._stat_id_to_id_meta[statistic_id] = id_meta
        return meta.id

    def _update_metadata(
        self,
        session: Session,
        statistic_id: str,
        new_metadata: StatisticMetaData,
        old_metadata_dict: dict[str, tuple[int, StatisticMetaData]],
    ) -> int:
        """Update metadata in the database."""
        metadata_id, old_metadata = old_metadata_dict[statistic_id]
        if (
            old_metadata["has_mean"] != new_metadata["has_mean"]
            or old_metadata["has_sum"] != new_metadata["has_sum"]
            or old_metadata["name"] != new_metadata["name"]
            or old_metadata["unit_of_measurement"]
            != new_metadata["unit_of_measurement"]
        ):
            session.query(StatisticsMeta).filter_by(statistic_id=statistic_id).update(
                {
                    StatisticsMeta.has_mean: new_metadata["has_mean"],
                    StatisticsMeta.has_sum: new_metadata["has_sum"],
                    StatisticsMeta.name: new_metadata["name"],
                    StatisticsMeta.unit_of_measurement: new_metadata[
                        "unit_of_measurement"
                    ],
                },
                synchronize_session=False,
            )
            self._stat_id_to_id_meta.pop(statistic_id, None)
            _LOGGER.debug(
                "Updated statistics metadata for %s, old_metadata: %s, new_metadata: %s",
                statistic_id,
                old_metadata,
                new_metadata,
            )

        return metadata_id

    def update_or_add(
        self,
        session: Session,
        new_metadata: StatisticMetaData,
        old_metadata_dict: dict[str, tuple[int, StatisticMetaData]],
    ) -> int:
        """Get metadata_id for a statistic_id.

        If the statistic_id is previously unknown, add it. If it's already known, update
        metadata if needed.

        Updating metadata source is not possible.
        """
        statistic_id = new_metadata["statistic_id"]
        if statistic_id not in old_metadata_dict:
            return self._add_metadata(session, statistic_id, new_metadata)
        return self._update_metadata(
            session, statistic_id, new_metadata, old_metadata_dict
        )

    def clear_cache(self, statistic_ids: list[str]) -> None:
        """Clear the cache."""
        for statistic_id in statistic_ids:
            self._stat_id_to_id_meta.pop(statistic_id, None)

    def delete(self, session: Session, statistic_ids: list[str]) -> None:
        """Clear statistics for a list of statistic_ids."""
        session.query(StatisticsMeta).filter(
            StatisticsMeta.statistic_id.in_(statistic_ids)
        ).delete(synchronize_session=False)
        self.clear_cache(statistic_ids)

    def reset(self) -> None:
        """Reset the cache."""
        self._stat_id_to_id_meta = {}
