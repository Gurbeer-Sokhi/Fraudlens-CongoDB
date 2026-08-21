"""FastAPI route handlers."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    AlertItem,
    DashboardStats,
    FraudPattern,
    GraphData,
    MoneyLaunderingRing,
    PersonDetail,
    RiskBucket,
    SearchResult,
    TimelineEvent,
    TransactionDetail,
)
from app.services.fraud_detection import fraud_service

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard():
    stats = fraud_service.get_dashboard_stats()
    return DashboardStats(
        total_persons=stats.get("total_persons", 0),
        total_transactions=stats.get("total_transactions", 0),
        high_risk_persons=stats.get("high_risk_persons", 0),
        suspicious_alerts=stats.get("suspicious_alerts", 0),
        total_volume=stats.get("total_volume", 0),
        risk_distribution=[RiskBucket(**b) for b in stats.get("risk_distribution", [])],
    )


@router.get("/alerts", response_model=list[AlertItem])
def get_alerts(limit: int = Query(50, ge=1, le=200)):
    return [AlertItem(**a) for a in fraud_service.get_alerts(limit)]


@router.get("/search", response_model=list[SearchResult])
def search(q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)):
    return [SearchResult(**r) for r in fraud_service.search(q, limit)]


@router.get("/persons/{person_id}", response_model=PersonDetail)
def get_person(person_id: str):
    detail = fraud_service.get_person_detail(person_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Person not found")
    return PersonDetail(**detail)


@router.get("/transactions/{tx_id}", response_model=TransactionDetail)
def get_transaction(tx_id: str):
    detail = fraud_service.get_transaction_detail(tx_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionDetail(**detail)


@router.get("/persons/{person_id}/timeline", response_model=list[TimelineEvent])
def get_timeline(person_id: str, limit: int = Query(50, ge=1, le=200)):
    return [TimelineEvent(**e) for e in fraud_service.get_timeline(person_id, limit)]


@router.get("/graph/network", response_model=GraphData)
def get_network_graph(node_limit: int = Query(150, ge=10, le=500)):
    data = fraud_service.build_network_graph(node_limit)
    return GraphData(**data)


@router.get("/graph/person/{person_id}", response_model=GraphData)
def get_person_graph(person_id: str, limit: int = Query(50, ge=5, le=200)):
    data = fraud_service.build_person_graph(person_id, limit)
    if not data["nodes"]:
        raise HTTPException(status_code=404, detail="Person not found or no connections")
    return GraphData(**data)


@router.get("/fraud/rings", response_model=list[MoneyLaunderingRing])
def get_money_laundering_rings(limit: int = Query(10, ge=1, le=50)):
    rows = fraud_service.get_money_laundering_rings(limit)
    rings = []
    for i, row in enumerate(rows):
        rings.append(MoneyLaunderingRing(
            ring_id=f"ring-{i}",
            persons=[row["p1_name"], row["p2_name"]],
            transactions=[
                {"id": row["t1_id"], "amount": row["t1_amount"]},
                {"id": row["t2_id"], "amount": row["t2_amount"]},
            ],
            total_amount=row["t1_amount"] + row["t2_amount"],
        ))
    return rings


@router.get("/fraud/patterns", response_model=list[FraudPattern])
def get_fraud_patterns(limit: int = Query(20, ge=1, le=100)):
    return [FraudPattern(**r) for r in fraud_service.get_fraud_patterns(limit)]
