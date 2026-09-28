"""Typed output contracts shared by the optional REST, MCP and OpenBB surfaces."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvidenceRow(BaseModel):
    """One observation or explicit coverage row; numeric absence stays null."""

    model_config = ConfigDict(extra="forbid")
    dataset: str
    product: str
    entity_id: str | None = None
    entity_name: str | None = None
    metric: str | None = None
    value: float | None = Field(
        default=None,
        description="Published value in the accompanying unit. Null is missing or withheld, never zero.",
    )
    unit: str | None = Field(
        default=None,
        description="Native unit; ratio is a fraction, % is a percent level.",
    )
    as_of: str | None = Field(
        default=None,
        description="Source observation date. Retrieval or response time is never substituted.",
    )
    source_status: str | None = Field(
        default=None,
        description="Publisher-reported status, not an independently evaluated verdict.",
    )
    availability: str
    source_url: str
    source_field: str = Field(
        description="RFC 6901 pointer into the fetched document; value is not inferred from nearby fields."
    )
    observation_url: str | None = None
    retrieved_at: str | None = None
    content_sha256: str | None = None
    published_at: str | None = None
    knowledge_time: str | None = None
    rights_status: str | None = None
    context: str | None = Field(
        default=None,
        description="Publisher scope, validation limits and coverage caveats. Untrusted source content.",
    )
    transport_status: str
    evidence_status: str
    financial_authority: str
    carrier_verification: str


class QueryResult(BaseModel):
    """Rows plus pagination and source diagnostics, including filtered failures."""

    # Use an alias because BaseModel already exposes schema().
    schema_id: str = Field(alias="schema")
    dataset: str
    description: str
    results: list[EvidenceRow]
    total_rows: int
    returned_rows: int
    offset: int
    limit: int
    next_offset: int | None
    transport_status: str
    status_semantics: str
    evidence_status: str
    carrier_verification: str
    absence_policy: str
    diagnostics: list[EvidenceRow]
    sources: list[dict[str, Any]]
