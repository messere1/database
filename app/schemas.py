from typing import Any, Literal

from pydantic import BaseModel, Field

ChartType = Literal["line", "bar", "pie", "heatmap"]


class HealthResponse(BaseModel):
    status: str
    database: str


class FieldDefinition(BaseModel):
    field_name: str
    source_type: str
    clean_type: str
    description: str


class DatasetMetaResponse(BaseModel):
    dataset_name: str
    source_table: str
    analysis_table: str
    field_count: int
    fields: list[FieldDefinition]


class DatasetOverviewResponse(BaseModel):
    total_rows: int
    min_occurrence_time: str | None
    max_occurrence_time: str | None
    distinct_crime_types: int
    distinct_districts: int
    distinct_community_areas: int


class DataQualityResponse(BaseModel):
    total_rows: int
    missing_counts: dict[str, int]


class AnalysisResponse(BaseModel):
    analysis_id: str
    title: str
    description: str
    chart_type: ChartType
    dimensions: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    data: list[dict[str, Any]] = Field(default_factory=list)
    insight: str


class ConclusionItem(BaseModel):
    rank: int
    title: str
    conclusion: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class ConclusionResponse(BaseModel):
    total: int
    conclusions: list[ConclusionItem]
