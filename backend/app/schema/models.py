"""Typed models for what the SchemaManager knows about the database.

Nothing downstream (SQL generator, validator, ambiguity resolver) is allowed
to reference a table or column name that didn't come from one of these
objects.
"""
from __future__ import annotations

from pydantic import BaseModel


class ColumnInfo(BaseModel):
    name: str
    data_type: str
    nullable: bool
    is_primary_key: bool = False
    is_foreign_key: bool = False
    references_table: str | None = None
    references_column: str | None = None


class TableInfo(BaseModel):
    name: str
    columns: list[ColumnInfo]

    def column_names(self) -> set[str]:
        return {c.name.lower() for c in self.columns}

    def has_column(self, name: str) -> bool:
        return name.lower() in self.column_names()

    def get_column(self, name: str) -> ColumnInfo | None:
        for col in self.columns:
            if col.name.lower() == name.lower():
                return col
        return None


class SchemaSnapshot(BaseModel):
    """The full set of tables/columns/relationships the SQL generator and
    validator are allowed to reference, plus the known categorical values
    the ambiguity resolver matches free-text terms against."""

    tables: dict[str, TableInfo]
    research_areas: list["ResearchAreaOption"]
    venues: list["VenueOption"]

    def has_table(self, name: str) -> bool:
        return name.lower() in {t.lower() for t in self.tables}

    def get_table(self, name: str) -> TableInfo | None:
        for key, table in self.tables.items():
            if key.lower() == name.lower():
                return table
        return None

    def all_table_names(self) -> list[str]:
        return list(self.tables.keys())

    def research_area_names(self) -> list[str]:
        return [r.area_name for r in self.research_areas]

    def venue_names(self) -> list[str]:
        return [v.venue_name for v in self.venues]


class ResearchAreaOption(BaseModel):
    area_id: int
    area_name: str


class VenueOption(BaseModel):
    venue_id: int
    venue_name: str
    venue_type: str


SchemaSnapshot.model_rebuild()
