"""Provide pre-made queries on top of the recorder component."""
from __future__ import annotations

from collections.abc import Callable, Iterable
import json
from typing import Any

from sqlalchemy import JSON, Column, Text, cast, not_, or_
from sqlalchemy.sql.elements import ClauseList

from homeassistant.const import CONF_DOMAINS, CONF_ENTITIES, CONF_EXCLUDE, CONF_INCLUDE
from homeassistant.helpers.entityfilter import CONF_ENTITY_GLOBS
from homeassistant.helpers.typing import ConfigType

from .models import ENTITY_ID_IN_EVENT, OLD_ENTITY_ID_IN_EVENT, States

DOMAIN = "history"
HISTORY_FILTERS = "history_filters"

GLOB_TO_SQL_CHARS = {
    ord("*"): "%",
    ord("?"): "_",
    ord("%"): "\\%",
    ord("_"): "\\_",
    ord("\\"): "\\\\",
}

FILTER_TYPES = (CONF_EXCLUDE, CONF_INCLUDE)
FITLER_MATCHERS = (CONF_ENTITIES, CONF_DOMAINS, CONF_ENTITY_GLOBS)


def extract_include_exclude_filter_conf(conf: ConfigType) -> dict[str, Any]:
    """Extract an include exclude filter from configuration.

    This makes a copy so we do not alter the original data.
    """
    return {
        filter_type: {
            matcher: set(conf.get(filter_type, {}).get(matcher) or [])
            for matcher in FITLER_MATCHERS
        }
        for filter_type in FILTER_TYPES
    }


def merge_include_exclude_filters(
    base_filter: dict[str, Any], add_filter: dict[str, Any]
) -> dict[str, Any]:
    """Merge two filters.

    This makes a copy so we do not alter the original data.
    """
    return {
        filter_type: {
            matcher: base_filter[filter_type][matcher]
            | add_filter[filter_type][matcher]
            for matcher in FITLER_MATCHERS
        }
        for filter_type in FILTER_TYPES
    }


def sqlalchemy_filter_from_include_exclude_conf(conf: ConfigType) -> Filters | None:
    """Build a sql filter from config."""
    filters = Filters()
    if exclude := conf.get(CONF_EXCLUDE):
        filters.excluded_entities = exclude.get(CONF_ENTITIES, [])
        filters.excluded_domains = exclude.get(CONF_DOMAINS, [])
        filters.excluded_entity_globs = exclude.get(CONF_ENTITY_GLOBS, [])
    if include := conf.get(CONF_INCLUDE):
        filters.included_entities = include.get(CONF_ENTITIES, [])
        filters.included_domains = include.get(CONF_DOMAINS, [])
        filters.included_entity_globs = include.get(CONF_ENTITY_GLOBS, [])

    return filters if filters.has_config else None


class Filters:
    """Container for the configured include and exclude filters."""

    def __init__(self) -> None:
        """Initialise the include and exclude filters."""
        self.excluded_entities: Iterable[str] = []
        self.excluded_domains: Iterable[str] = []
        self.excluded_entity_globs: Iterable[str] = []

        self.included_entities: Iterable[str] = []
        self.included_domains: Iterable[str] = []
        self.included_entity_globs: Iterable[str] = []

    @property
    def has_config(self) -> bool:
        """Determine if there is any filter configuration."""
        return bool(
            self.excluded_entities
            or self.excluded_domains
            or self.excluded_entity_globs
            or self.included_entities
            or self.included_domains
            or self.included_entity_globs
        )

    def _generate_filter_for_columns(
        self, columns: Iterable[Column], encoder: Callable[[Any], Any]
    ) -> ClauseList:
        """Generate a filter from pre-comuted sets and pattern lists.

        This must match exactly how homeassistant.helpers.entityfilter works.
        """
        have_exclude = bool(
            self.excluded_entities
            or self.excluded_domains
            or self.excluded_entity_globs
        )
        have_include = bool(
            self.included_entities
            or self.included_domains
            or self.included_entity_globs
        )

        # Case 1 - no includes or excludes - pass all entities
        if not have_include and not have_exclude:
            return None

        includes = []
        included_domains_matcher = _domain_matcher(
            self.included_domains, columns, encoder
        )
        included_entities_matcher = _entity_matcher(
            self.included_entities, columns, encoder
        )
        included_entity_globs_matcher = _globs_to_like(
            self.included_entity_globs, columns, encoder
        )
        if self.included_domains:
            includes.append(included_domains_matcher)
        if self.included_entities:
            includes.append(included_entities_matcher)
        if self.included_entity_globs:
            includes.append(included_entity_globs_matcher)

        # Case 2 - includes, no excludes - only include specified entities
        if have_include and not have_exclude:

            return or_(*includes).self_group()

        excludes = []
        excluded_domains_matcher = _domain_matcher(
            self.excluded_domains, columns, encoder
        )
        excluded_entities_matcher = _entity_matcher(
            self.excluded_entities, columns, encoder
        )
        excluded_entity_globs_matcher = _globs_to_like(
            self.excluded_entity_globs, columns, encoder
        )
        if self.excluded_domains:
            excludes.append(excluded_domains_matcher)
        if self.excluded_entities:
            excludes.append(excluded_entities_matcher)
        if self.excluded_entity_globs:
            excludes.append(excluded_entity_globs_matcher)

        # Case 3 - excludes, no includes - only exclude specified entities
        if not have_include and have_exclude:
            return not_(or_(*excludes).self_group())

        # Case 4 - both includes and excludes specified
        # Case 4a - include domain or glob specified
        #  - if domain is included, pass if entity not excluded
        #  - if glob is included, pass if entity and domain not excluded
        #  - if domain and glob are not included, pass if entity is included
        # note: if both include domain matches then exclude domains ignored.
        #   If glob matches then exclude domains and glob checked
        if self.included_domains or self.included_entity_globs:

            return or_(
                (
                    included_domains_matcher
                    & ~(excluded_entities_matcher | excluded_entity_globs_matcher)
                ),
                (
                    ~included_domains_matcher
                    & or_(
                        (included_entity_globs_matcher & ~(or_(*excludes))),
                        (~included_entity_globs_matcher & included_entities_matcher),
                    )
                ),
            ).self_group()

        # Case 4b - exclude domain or glob specified, include has no domain or glob
        # In this one case the traditional include logic is inverted. Even though an
        # include is specified since its only a list of entity IDs its used only to
        # expose specific entities excluded by domain or glob. Any entities not
        # excluded are then presumed included. Logic is as follows
        #  - if domain or glob is excluded, pass if entity is included
        #  - if domain is not excluded, pass if entity not excluded by ID
        if self.excluded_domains or self.excluded_entity_globs:
            matcher = not_(or_(*excludes))
            if self.included_entities:
                matcher |= _entity_matcher(self.included_entities, columns, encoder)
            return matcher.self_group()

        # Case 4c - neither include or exclude domain specified
        #  - Only pass if entity is included.  Ignore entity excludes.
        return _entity_matcher(self.included_entities, columns, encoder)

    def states_entity_filter(self) -> ClauseList:
        """Generate the entity filter query."""

        def _encoder(data: Any) -> Any:
            """Nothing to encode for states since there is no json."""
            return data

        return self._generate_filter_for_columns((States.entity_id,), _encoder)

    def events_entity_filter(self) -> ClauseList:
        """Generate the entity filter query."""
        _encoder = json.dumps
        return or_(
            (ENTITY_ID_IN_EVENT == JSON.NULL) & (OLD_ENTITY_ID_IN_EVENT == JSON.NULL),
            self._generate_filter_for_columns(
                (ENTITY_ID_IN_EVENT, OLD_ENTITY_ID_IN_EVENT), _encoder
            ).self_group(),
        )


def _globs_to_like(
    glob_strs: Iterable[str], columns: Iterable[Column], encoder: Callable[[Any], Any]
) -> ClauseList:
    """Translate glob to sql."""
    return or_(
        cast(column, Text()).like(
            encoder(glob_str).translate(GLOB_TO_SQL_CHARS), escape="\\"
        )
        for glob_str in glob_strs
        for column in columns
    )


def _entity_matcher(
    entity_ids: Iterable[str], columns: Iterable[Column], encoder: Callable[[Any], Any]
) -> ClauseList:
    return or_(
        cast(column, Text()).in_([encoder(entity_id) for entity_id in entity_ids])
        for column in columns
    )


def _domain_matcher(
    domains: Iterable[str], columns: Iterable[Column], encoder: Callable[[Any], Any]
) -> ClauseList:
    return or_(
        cast(column, Text()).like(encoder(f"{domain}.%"))
        for domain in domains
        for column in columns
    )
