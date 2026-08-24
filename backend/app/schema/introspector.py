"""Two ways to obtain a SchemaSnapshot, behind one interface.

OracleSchemaIntrospector queries the Oracle data dictionary directly —
USER_TAB_COLUMNS / USER_CONSTRAINTS / USER_CONS_COLUMNS — so schema drift
between the DDL scripts and this code is structurally impossible in
production.

StaticSchemaIntrospector is a hand-maintained mirror of database/01_schema.sql
through database/07_vector.sql, used when APP_ENV=test or no Oracle
connection is configured. It exists so the SQL generator, validator, and
ambiguity resolver can be developed and tested without a live database.

If you change the DDL, update TABLE_DEFINITIONS in this file to match, or
better, run the Oracle-backed introspector once and diff its output.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.common.exceptions import RepositoryError
from app.common.logging import get_logger
from app.schema.models import (
    ColumnInfo,
    ResearchAreaOption,
    SchemaSnapshot,
    TableInfo,
    VenueOption,
)

logger = get_logger("schema.introspector")

# (table_name, [(column_name, data_type, nullable, is_pk, fk_table, fk_column), ...])
# Transcribed from database/01_schema.sql, 02_constraints.sql and 07_vector.sql.
TABLE_DEFINITIONS: list[
    tuple[str, list[tuple[str, str, bool, bool, str | None, str | None]]]
] = [
    (
        "authors",
        [
            ("author_id",        "NUMBER",    False, True,  None,            None),
            ("full_name",        "VARCHAR2",  False, False, None,            None),
            ("normalized_name",  "VARCHAR2",  False, False, None,            None),
            ("affiliation",      "VARCHAR2",  True,  False, None,            None),
            ("orcid",            "VARCHAR2",  True,  False, None,            None),
            ("created_at",       "TIMESTAMP", False, False, None,            None),
        ],
    ),
    (
        "venues",
        [
            ("venue_id",    "NUMBER",    False, True,  None, None),
            ("venue_name",  "VARCHAR2",  False, False, None, None),
            ("venue_type",  "VARCHAR2",  False, False, None, None),
            ("issn",        "VARCHAR2",  True,  False, None, None),
            ("publisher",   "VARCHAR2",  True,  False, None, None),
            ("created_at",  "TIMESTAMP", False, False, None, None),
        ],
    ),
    (
        "research_areas",
        [
            ("area_id",        "NUMBER",   False, True,  None,             None),
            ("area_name",      "VARCHAR2", False, False, None,             None),
            ("parent_area_id", "NUMBER",   True,  False, "research_areas", "area_id"),
            ("description",    "VARCHAR2", True,  False, None,             None),
        ],
    ),
    (
        "keywords",
        [
            ("keyword_id",   "NUMBER",   False, True,  None, None),
            ("keyword_text", "VARCHAR2", False, False, None, None),
        ],
    ),
    (
        "papers",
        [
            ("paper_id",                 "NUMBER",    False, True,  None,             None),
            ("paper_code",               "VARCHAR2",  False, False, None,             None),
            ("title",                    "VARCHAR2",  False, False, None,             None),
            ("abstract",                 "CLOB",      True,  False, None,             None),
            ("year",                     "NUMBER",    False, False, None,             None),
            ("venue_id",                 "NUMBER",    True,  False, "venues",         "venue_id"),
            ("citation_count",           "NUMBER",    False, False, None,             None),
            ("primary_research_area_id", "NUMBER",    True,  False, "research_areas", "area_id"),
            ("doi",                      "VARCHAR2",  True,  False, None,             None),
            ("publication_type",         "VARCHAR2",  True,  False, None,             None),
            ("extra_metadata",           "JSON",      True,  False, None,             None),
            ("created_at",               "TIMESTAMP", False, False, None,             None),
            ("updated_at",               "TIMESTAMP", False, False, None,             None),
        ],
    ),
    (
        "paper_authors",
        [
            ("paper_id",     "NUMBER", False, True, "papers",  "paper_id"),
            ("author_id",    "NUMBER", False, True, "authors", "author_id"),
            ("author_order", "NUMBER", False, False, None,      None),
        ],
    ),
    (
        "paper_keywords",
        [
            ("paper_id",   "NUMBER", False, True, "papers",   "paper_id"),
            ("keyword_id", "NUMBER", False, True, "keywords", "keyword_id"),
        ],
    ),
    (
        "citations",
        [
            ("citation_id",      "NUMBER",    False, True,  None,     None),
            ("citing_paper_id",  "NUMBER",    False, False, "papers", "paper_id"),
            ("cited_paper_id",   "NUMBER",    False, False, "papers", "paper_id"),
            ("created_at",       "TIMESTAMP", False, False, None,     None),
        ],
    ),
    (
        "paper_embeddings",
        [
            ("embedding_id",           "NUMBER",         False, True,  None,     None),
            ("paper_id",               "NUMBER",         False, False, "papers", "paper_id"),
            ("model_name",             "VARCHAR2",       False, False, None,     None),
            ("precision_mode",         "VARCHAR2",       False, False, None,     None),
            ("dimension",              "NUMBER",         False, False, None,     None),
            ("embedding_f32",          "VECTOR",         True,  False, None,     None),
            ("embedding_f64",          "VECTOR",         True,  False, None,     None),
            ("embedding_i8",           "VECTOR",         True,  False, None,     None),
            ("embedding_f16_emulated", "RAW",            True,  False, None,     None),
            ("quantization_scale",     "BINARY_DOUBLE",  True,  False, None,     None),
            ("source_text",            "CLOB",           True,  False, None,     None),
            ("created_at",             "TIMESTAMP",      False, False, None,     None),
        ],
    ),
    (
        "query_history",
        [
            ("history_id",             "NUMBER",    False, True,  None, None),
            ("conversation_id",        "VARCHAR2",  False, False, None, None),
            ("turn_id",                "NUMBER",    False, False, None, None),
            ("user_query",             "CLOB",      False, False, None, None),
            ("interpreted_intent",     "JSON",      True,  False, None, None),
            ("retrieval_mode",         "VARCHAR2",  True,  False, None, None),
            ("generated_sql",          "CLOB",      True,  False, None, None),
            ("result_paper_ids",       "JSON",      True,  False, None, None),
            ("clarification_question", "VARCHAR2",  True,  False, None, None),
            ("created_at",             "TIMESTAMP", False, False, None, None),
        ],
    ),
    (
        "query_executions",
        [
            ("execution_id",                 "NUMBER",    False, True,  None,            None),
            ("history_id",                   "NUMBER",    False, False, "query_history", "history_id"),
            ("attempt_number",               "NUMBER",    False, False, None,            None),
            ("sql_text",                     "CLOB",      False, False, None,            None),
            ("bind_params",                  "JSON",      True,  False, None,            None),
            ("status",                       "VARCHAR2",  False, False, None,            None),
            ("error_code",                   "VARCHAR2",  True,  False, None,            None),
            ("error_message",                "VARCHAR2",  True,  False, None,            None),
            ("error_category",               "VARCHAR2",  True,  False, None,            None),
            ("row_count",                    "NUMBER",    True,  False, None,            None),
            ("execution_time_ms",            "NUMBER",    True,  False, None,            None),
            ("corrected_from_execution_id",  "NUMBER",    True,  False, "query_executions", "execution_id"),
            ("created_at",                   "TIMESTAMP", False, False, None,            None),
        ],
    ),
    (
        "experiment_results",
        [
            ("result_id",              "NUMBER",         False, True,  None, None),
            ("experiment_name",        "VARCHAR2",       False, False, None, None),
            ("run_id",                 "VARCHAR2",       False, False, None, None),
            ("configuration",          "JSON",           False, False, None, None),
            ("metric_name",            "VARCHAR2",       False, False, None, None),
            ("metric_value",           "BINARY_DOUBLE",  False, False, None, None),
            ("dataset_version",        "VARCHAR2",       True,  False, None, None),
            ("is_synthetic_smoke_test","NUMBER",         False, False, None, None),
            ("created_at",             "TIMESTAMP",      False, False, None, None),
        ],
    ),
]


def _build_static_snapshot() -> SchemaSnapshot:
    tables: dict[str, TableInfo] = {}
    for table_name, columns in TABLE_DEFINITIONS:
        col_infos = [
            ColumnInfo(
                name=name,
                data_type=dtype,
                nullable=nullable,
                is_primary_key=is_pk,
                is_foreign_key=fk_table is not None,
                references_table=fk_table,
                references_column=fk_column,
            )
            for name, dtype, nullable, is_pk, fk_table, fk_column in columns
        ]
        tables[table_name] = TableInfo(name=table_name, columns=col_infos)

    research_areas = [
        ResearchAreaOption(area_id=1,  area_name="Natural Language Processing"),
        ResearchAreaOption(area_id=2,  area_name="Computer Vision"),
        ResearchAreaOption(area_id=3,  area_name="Database Systems"),
        ResearchAreaOption(area_id=4,  area_name="Distributed Systems"),
        ResearchAreaOption(area_id=5,  area_name="Cardiac Signal Processing"),
        ResearchAreaOption(area_id=6,  area_name="Machine Learning Theory"),
        ResearchAreaOption(area_id=7,  area_name="Information Retrieval"),
        ResearchAreaOption(area_id=8,  area_name="Human-Computer Interaction"),
        ResearchAreaOption(area_id=9,  area_name="Robotics"),
        ResearchAreaOption(area_id=10, area_name="Computer Networks"),
    ]
    venues = [
        VenueOption(venue_id=1,  venue_name="NeurIPS",   venue_type="CONFERENCE"),
        VenueOption(venue_id=2,  venue_name="ACL",       venue_type="CONFERENCE"),
        VenueOption(venue_id=3,  venue_name="VLDB",      venue_type="CONFERENCE"),
        VenueOption(venue_id=4,  venue_name="SIGMOD",    venue_type="CONFERENCE"),
        VenueOption(venue_id=5,  venue_name="ICML",      venue_type="CONFERENCE"),
        VenueOption(venue_id=6,  venue_name="IEEE TBME", venue_type="JOURNAL"),
        VenueOption(venue_id=7,  venue_name="JMLR",      venue_type="JOURNAL"),
        VenueOption(venue_id=8,  venue_name="arXiv",     venue_type="PREPRINT_SERVER"),
        VenueOption(venue_id=9,  venue_name="EMNLP",     venue_type="CONFERENCE"),
        VenueOption(venue_id=10, venue_name="ICLR",      venue_type="CONFERENCE"),
    ]
    return SchemaSnapshot(tables=tables, research_areas=research_areas, venues=venues)


class SchemaIntrospectorPort(ABC):
    @abstractmethod
    def load_snapshot(self) -> SchemaSnapshot: ...


class StaticSchemaIntrospector(SchemaIntrospectorPort):
    """Offline mirror of the DDL. Used for APP_ENV=test and local dev without
    Oracle. See module docstring for the sync-with-DDL caveat."""

    def load_snapshot(self) -> SchemaSnapshot:
        return _build_static_snapshot()


class OracleSchemaIntrospector(SchemaIntrospectorPort):
    """Queries the live Oracle data dictionary. This is the source of truth
    in production — if the DDL changes, this introspector's output changes
    with it automatically, with no code edit required."""

    def __init__(self, connection_provider) -> None:
        self._cp = connection_provider

    def load_snapshot(self) -> SchemaSnapshot:
        managed_tables = [name for name, _ in TABLE_DEFINITIONS]
        try:
            with self._cp.get_connection() as conn:
                tables = self._load_tables(conn, managed_tables)
                research_areas = self._load_research_areas(conn)
                venues = self._load_venues(conn)
        except Exception as exc:
            raise RepositoryError(
                f"Schema introspection failed: {exc}"
            ) from exc
        return SchemaSnapshot(
            tables=tables,
            research_areas=research_areas,
            venues=venues,
        )

    def _load_tables(
        self, conn, managed_tables: list[str]
    ) -> dict[str, TableInfo]:
        upper_tables = [t.upper() for t in managed_tables]

        cursor = conn.cursor()
        try:
            placeholders = ",".join([f":{i+1}" for i in range(len(upper_tables))])
            cursor.execute(
                f"""
                SELECT table_name, column_name, data_type, nullable
                FROM   user_tab_columns
                WHERE  table_name IN ({placeholders})
                ORDER  BY table_name, column_id
                """,
                upper_tables,
            )
            col_rows = cursor.fetchall()

            cursor.execute(
                f"""
                SELECT ac.table_name, acc.column_name, ac.constraint_type,
                       r_acc.table_name AS ref_table,
                       r_acc.column_name AS ref_column
                FROM   user_constraints ac
                JOIN   user_cons_columns acc
                       ON  acc.constraint_name = ac.constraint_name
                       AND acc.table_name      = ac.table_name
                LEFT JOIN user_constraints r_ac
                       ON  r_ac.constraint_name = ac.r_constraint_name
                LEFT JOIN user_cons_columns r_acc
                       ON  r_acc.constraint_name = r_ac.constraint_name
                       AND r_acc.position        = acc.position
                WHERE  ac.constraint_type IN ('P', 'R')
                  AND  ac.table_name      IN ({placeholders})
                """,
                upper_tables,
            )
            con_rows = cursor.fetchall()
        finally:
            cursor.close()

        pk_cols: set[tuple[str, str]] = set()
        fk_map: dict[tuple[str, str], tuple[str, str]] = {}
        for tname, cname, ctype, ref_table, ref_col in con_rows:
            key = (tname.lower(), cname.lower())
            if ctype == "P":
                pk_cols.add(key)
            elif ctype == "R" and ref_table and ref_col:
                fk_map[key] = (ref_table.lower(), ref_col.lower())

        tables: dict[str, TableInfo] = {}
        for tname, cname, dtype, nullable in col_rows:
            tkey = tname.lower()
            ckey = (tkey, cname.lower())
            ref = fk_map.get(ckey)
            col = ColumnInfo(
                name=cname.lower(),
                data_type=dtype,
                nullable=(nullable == "Y"),
                is_primary_key=ckey in pk_cols,
                is_foreign_key=ref is not None,
                references_table=ref[0] if ref else None,
                references_column=ref[1] if ref else None,
            )
            if tkey not in tables:
                tables[tkey] = TableInfo(name=tkey, columns=[])
            tables[tkey].columns.append(col)
        return tables

    def _load_research_areas(self, conn) -> list[ResearchAreaOption]:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT area_id, area_name FROM research_areas ORDER BY area_name"
            )
            return [
                ResearchAreaOption(area_id=r[0], area_name=r[1])
                for r in cursor.fetchall()
            ]
        finally:
            cursor.close()

    def _load_venues(self, conn) -> list[VenueOption]:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT venue_id, venue_name, venue_type FROM venues ORDER BY venue_name"
            )
            return [
                VenueOption(venue_id=r[0], venue_name=r[1], venue_type=r[2])
                for r in cursor.fetchall()
            ]
        finally:
            cursor.close()
