"""Pydantic response models for API endpoints."""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    database: str


class RiskBucket(BaseModel):
    label: str
    min_score: int
    max_score: int
    count: int
    color: str


class DashboardStats(BaseModel):
    total_persons: int
    total_transactions: int
    high_risk_persons: int
    suspicious_alerts: int
    total_volume: float
    risk_distribution: list[RiskBucket]


class AlertItem(BaseModel):
    id: str
    alert_type: str
    severity: str
    title: str
    description: str
    entity_id: str
    entity_type: str
    risk_score: int
    timestamp: Optional[str] = None


class GraphNode(BaseModel):
    id: str
    label: str
    group: str
    title: str = ""
    risk_score: Optional[int] = None
    color: Optional[str] = None


class GraphEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_: str = Field(alias="from", serialization_alias="from")
    to: str
    label: str = ""
    dashes: bool = False


class GraphData(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class SearchResult(BaseModel):
    entity_type: str
    id: str
    label: str
    subtitle: str
    risk_score: Optional[int] = None


class PersonDetail(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    risk_score: int
    created_at: str
    accounts: list[dict[str, Any]]
    devices: list[dict[str, Any]]
    ips: list[dict[str, Any]]
    recent_transactions: list[dict[str, Any]]


class TransactionDetail(BaseModel):
    id: str
    amount: float
    timestamp: str
    transaction_type: str
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    from_account: Optional[dict[str, Any]] = None
    to_account: Optional[dict[str, Any]] = None
    merchant: Optional[dict[str, Any]] = None
    performer: Optional[dict[str, Any]] = None


class TimelineEvent(BaseModel):
    id: str
    timestamp: str
    amount: float
    transaction_type: str
    merchant_name: Optional[str] = None
    risk_indicator: str


class MoneyLaunderingRing(BaseModel):
    ring_id: str
    persons: list[str]
    transactions: list[dict[str, Any]]
    total_amount: float


class FraudPattern(BaseModel):
    person_id: str
    person_name: str
    risk_score: int
    device_count: int
    ip_count: int
    suspicious_transactions: int
