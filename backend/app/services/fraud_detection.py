"""Fraud detection Cypher queries and business logic."""

import logging
from typing import Any, Optional

from app.database import run_query, run_write

logger = logging.getLogger(__name__)

# ── Risk score helpers ──────────────────────────────────────────────────────

def risk_color(score: int) -> str:
    """Map risk score to UI color (green/yellow/red)."""
    if score < 30:
        return "#22c55e"
    if score < 60:
        return "#eab308"
    if score < 80:
        return "#f97316"
    return "#ef4444"


def risk_label(score: int) -> str:
    if score < 30:
        return "low"
    if score < 60:
        return "medium"
    if score < 80:
        return "high"
    return "critical"


# ── Dashboard queries ───────────────────────────────────────────────────────

DASHBOARD_STATS = """
MATCH (p:Person)
WITH count(p) AS total_persons
MATCH (t:Transaction)
WITH total_persons, count(t) AS total_transactions, coalesce(sum(t.amount), 0) AS total_volume
MATCH (hp:Person) WHERE hp.risk_score >= 60
WITH total_persons, total_transactions, total_volume, count(hp) AS high_risk_persons
OPTIONAL MATCH (alert:Alert)
RETURN total_persons, total_transactions, total_volume, high_risk_persons,
       coalesce(count(alert), 0) AS suspicious_alerts
"""

RISK_DISTRIBUTION = """
MATCH (p:Person)
RETURN
  CASE
    WHEN p.risk_score < 30 THEN 'Low (0-29)'
    WHEN p.risk_score < 60 THEN 'Medium (30-59)'
    WHEN p.risk_score < 80 THEN 'High (60-79)'
    ELSE 'Critical (80-100)'
  END AS label,
  CASE
    WHEN p.risk_score < 30 THEN 0
    WHEN p.risk_score < 60 THEN 30
    WHEN p.risk_score < 80 THEN 60
    ELSE 80
  END AS min_score,
  CASE
    WHEN p.risk_score < 30 THEN 29
    WHEN p.risk_score < 60 THEN 59
    WHEN p.risk_score < 80 THEN 79
    ELSE 100
  END AS max_score,
  count(p) AS count
ORDER BY min_score
"""

# ── Key fraud detection queries (from spec) ─────────────────────────────────

MONEY_LAUNDERING_RINGS = """
MATCH (p1:Person)-[:OWNS]->(a1:BankAccount)<-[:FROM]-(t1:Transaction)-[:TO]->(a2:BankAccount)<-[:OWNS]-(p2:Person)
WHERE t1.amount > $min_amount
  AND p1 <> p2
MATCH (p2)-[:OWNS]->(a3:BankAccount)<-[:FROM]-(t2:Transaction)-[:TO]->(a1)
WHERE t2.amount > $min_amount
RETURN p1.id AS p1_id, p1.name AS p1_name,
       p2.id AS p2_id, p2.name AS p2_name,
       t1.id AS t1_id, t1.amount AS t1_amount, t1.timestamp AS t1_timestamp,
       t2.id AS t2_id, t2.amount AS t2_amount
LIMIT $limit
"""

CONNECTED_FRAUD_PATTERNS = """
MATCH (p:Person)-[:HAS_DEVICE]->(d:Device)
WITH p, collect(d.device_fingerprint) AS devices
WHERE size(devices) > 1
MATCH (p)-[:USES_IP]->(ip:IPAddress)
WITH p, devices, collect(ip.ip) AS ips
WHERE size(ips) > 3
OPTIONAL MATCH (p)-[:PERFORMS]->(t:Transaction)-[:AT]->(m:Merchant)
WHERE t.amount > $min_tx_amount
RETURN p.id AS person_id, p.name AS person_name, p.risk_score AS risk_score,
       size(devices) AS device_count, size(ips) AS ip_count,
       count(t) AS suspicious_transactions
ORDER BY p.risk_score DESC
LIMIT $limit
"""

# ── Alert generation ────────────────────────────────────────────────────────

DETECT_SHARED_DEVICES = """
MATCH (p1:Person)-[:SHARES_DEVICE_WITH]->(p2:Person)
WHERE p1.id < p2.id
RETURN p1.id AS p1_id, p1.name AS p1_name, p1.risk_score AS p1_risk,
       p2.id AS p2_id, p2.name AS p2_name, p2.risk_score AS p2_risk
LIMIT $limit
"""

DETECT_SHARED_IPS = """
MATCH (p1:Person)-[:SHARES_IP_WITH]->(p2:Person)
WHERE p1.id < p2.id
RETURN p1.id AS p1_id, p1.name AS p1_name,
       p2.id AS p2_id, p2.name AS p2_name
LIMIT $limit
"""

DETECT_SUSPICIOUS_TX_LINKS = """
MATCH (t1:Transaction)-[:SUSPICIOUS_RELATION]->(t2:Transaction)
RETURN t1.id AS t1_id, t1.amount AS t1_amount,
       t2.id AS t2_id, t2.amount AS t2_amount
LIMIT $limit
"""

# ── Search queries ────────────────────────────────────────────────────────────

SEARCH_PERSONS = """
MATCH (p:Person)
WHERE toLower(p.name) CONTAINS toLower($query)
   OR toLower(p.email) CONTAINS toLower($query)
   OR p.id CONTAINS $query
RETURN p.id AS id, p.name AS name, p.email AS email, p.risk_score AS risk_score
LIMIT $limit
"""

SEARCH_ACCOUNTS = """
MATCH (a:BankAccount)
WHERE a.account_number CONTAINS $query OR a.id CONTAINS $query
RETURN a.id AS id, a.account_number AS account_number, a.bank_name AS bank_name,
       a.balance AS balance
LIMIT $limit
"""

SEARCH_TRANSACTIONS = """
MATCH (t:Transaction)
WHERE t.id CONTAINS $query
RETURN t.id AS id, t.amount AS amount, t.timestamp AS timestamp,
       t.transaction_type AS transaction_type
LIMIT $limit
"""

PERSON_DETAIL = """
MATCH (p:Person {id: $person_id})
OPTIONAL MATCH (p)-[:OWNS]->(a:BankAccount)
OPTIONAL MATCH (p)-[:HAS_DEVICE]->(d:Device)
OPTIONAL MATCH (p)-[:USES_IP]->(ip:IPAddress)
OPTIONAL MATCH (p)-[:PERFORMS]->(t:Transaction)
OPTIONAL MATCH (t)-[:AT]->(m:Merchant)
RETURN p,
       collect(DISTINCT a) AS accounts,
       collect(DISTINCT {id: d.id, fingerprint: d.device_fingerprint, os: d.os}) AS devices,
       collect(DISTINCT {id: ip.id, ip: ip.ip, geolocation: ip.geolocation, is_proxy: ip.is_proxy}) AS ips,
       collect(DISTINCT {
         id: t.id, amount: t.amount, timestamp: t.timestamp,
         type: t.transaction_type, merchant: m.name
       }) AS transactions
"""

TRANSACTION_DETAIL = """
MATCH (t:Transaction {id: $tx_id})
OPTIONAL MATCH (t)-[:FROM]->(from_acc:BankAccount)
OPTIONAL MATCH (t)-[:TO]->(to_acc:BankAccount)
OPTIONAL MATCH (t)-[:AT]->(m:Merchant)
OPTIONAL MATCH (p:Person)-[:PERFORMS]->(t)
RETURN t,
       from_acc, to_acc, m,
       p { .id, .name, .risk_score } AS performer
"""

TRANSACTION_TIMELINE = """
MATCH (p:Person {id: $person_id})-[:PERFORMS]->(t:Transaction)
OPTIONAL MATCH (t)-[:AT]->(m:Merchant)
RETURN t.id AS id, t.timestamp AS timestamp, t.amount AS amount,
       t.transaction_type AS transaction_type, m.name AS merchant_name
ORDER BY t.timestamp DESC
LIMIT $limit
"""

NETWORK_GRAPH = """
MATCH (n)
WHERE n:Person OR n:BankAccount OR n:Transaction OR n:Merchant OR n:Device OR n:IPAddress
WITH n LIMIT $node_limit
OPTIONAL MATCH (n)-[r]->(m)
WHERE m IS NULL OR (
  m:Person OR m:BankAccount OR m:Transaction OR m:Merchant OR m:Device OR m:IPAddress
)
RETURN n, r, m
"""

PERSON_NETWORK = """
MATCH (p:Person {id: $person_id})
CALL {
  WITH p
  MATCH path = (p)-[*1..2]-(connected)
  WHERE connected:Person OR connected:BankAccount OR connected:Transaction
     OR connected:Merchant OR connected:Device OR connected:IPAddress
  RETURN path
  LIMIT $limit
}
RETURN path
"""

CLEAR_DATABASE = """
MATCH (n) DETACH DELETE n
"""


class FraudDetectionService:
    """Service layer for fraud detection operations."""

    def get_dashboard_stats(self) -> dict[str, Any]:
        rows = run_query(DASHBOARD_STATS)
        stats = rows[0] if rows else {
            "total_persons": 0, "total_transactions": 0, "total_volume": 0,
            "high_risk_persons": 0, "suspicious_alerts": 0,
        }
        dist_rows = run_query(RISK_DISTRIBUTION)
        colors = {"Low (0-29)": "#22c55e", "Medium (30-59)": "#eab308",
                  "High (60-79)": "#f97316", "Critical (80-100)": "#ef4444"}
        stats["risk_distribution"] = [
            {**row, "color": colors.get(row["label"], "#64748b")}
            for row in dist_rows
        ]
        return stats

    def get_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []

        # Money laundering rings
        for i, row in enumerate(run_query(MONEY_LAUNDERING_RINGS, {"min_amount": 10000, "limit": 20})):
            alerts.append({
                "id": f"ml-{i}",
                "alert_type": "money_laundering_ring",
                "severity": "critical",
                "title": f"Circular transfer: {row['p1_name']} ↔ {row['p2_name']}",
                "description": f"Mutual high-value transfers (${row['t1_amount']:,.0f} / ${row['t2_amount']:,.0f}) detected between accounts.",
                "entity_id": row["p1_id"],
                "entity_type": "person",
                "risk_score": 95,
                "timestamp": row.get("t1_timestamp"),
            })

        # Connected fraud patterns
        for i, row in enumerate(run_query(CONNECTED_FRAUD_PATTERNS, {"min_tx_amount": 5000, "limit": 20})):
            alerts.append({
                "id": f"fp-{i}",
                "alert_type": "identity_fraud",
                "severity": risk_label(row["risk_score"]),
                "title": f"Multi-device/IP pattern: {row['person_name']}",
                "description": f"{row['device_count']} devices, {row['ip_count']} IPs, {row['suspicious_transactions']} large transactions.",
                "entity_id": row["person_id"],
                "entity_type": "person",
                "risk_score": row["risk_score"],
            })

        # Shared device alerts
        for i, row in enumerate(run_query(DETECT_SHARED_DEVICES, {"limit": 15})):
            alerts.append({
                "id": f"sd-{i}",
                "alert_type": "shared_device",
                "severity": "high",
                "title": f"Shared device: {row['p1_name']} & {row['p2_name']}",
                "description": "Two persons linked through the same device fingerprint.",
                "entity_id": row["p1_id"],
                "entity_type": "person",
                "risk_score": max(row["p1_risk"], row["p2_risk"]),
            })

        # Shared IP alerts
        for i, row in enumerate(run_query(DETECT_SHARED_IPS, {"limit": 15})):
            alerts.append({
                "id": f"si-{i}",
                "alert_type": "shared_ip",
                "severity": "medium",
                "title": f"Shared IP: {row['p1_name']} & {row['p2_name']}",
                "description": "Two persons using the same IP address.",
                "entity_id": row["p1_id"],
                "entity_type": "person",
                "risk_score": 55,
            })

        alerts.sort(key=lambda a: a["risk_score"], reverse=True)
        return alerts[:limit]

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        params = {"query": query.strip(), "limit": limit}
        results: list[dict[str, Any]] = []

        for row in run_query(SEARCH_PERSONS, params):
            results.append({
                "entity_type": "person",
                "id": row["id"],
                "label": row["name"],
                "subtitle": row["email"],
                "risk_score": row["risk_score"],
            })
        for row in run_query(SEARCH_ACCOUNTS, params):
            results.append({
                "entity_type": "account",
                "id": row["id"],
                "label": row["account_number"],
                "subtitle": f"{row['bank_name']} — ${row['balance']:,.2f}",
            })
        for row in run_query(SEARCH_TRANSACTIONS, params):
            results.append({
                "entity_type": "transaction",
                "id": row["id"],
                "label": row["id"],
                "subtitle": f"${row['amount']:,.2f} — {row['transaction_type']}",
            })
        return results

    def get_person_detail(self, person_id: str) -> Optional[dict[str, Any]]:
        rows = run_query(PERSON_DETAIL, {"person_id": person_id})
        if not rows:
            return None
        row = rows[0]
        p = row["p"]
        return {
            "id": p["id"],
            "name": p["name"],
            "email": p["email"],
            "phone": p["phone"],
            "risk_score": p["risk_score"],
            "created_at": p["created_at"],
            "accounts": [dict(a) for a in row["accounts"] if a],
            "devices": [d for d in row["devices"] if d.get("id")],
            "ips": [ip for ip in row["ips"] if ip.get("id")],
            "recent_transactions": sorted(
                [t for t in row["transactions"] if t.get("id")],
                key=lambda x: x.get("timestamp", ""),
                reverse=True,
            )[:20],
        }

    def get_transaction_detail(self, tx_id: str) -> Optional[dict[str, Any]]:
        rows = run_query(TRANSACTION_DETAIL, {"tx_id": tx_id})
        if not rows:
            return None
        row = rows[0]
        t = row["t"]
        return {
            "id": t["id"],
            "amount": t["amount"],
            "timestamp": t["timestamp"],
            "transaction_type": t["transaction_type"],
            "ip_address": t.get("ip_address"),
            "device_id": t.get("device_id"),
            "from_account": dict(row["from_acc"]) if row["from_acc"] else None,
            "to_account": dict(row["to_acc"]) if row["to_acc"] else None,
            "merchant": dict(row["m"]) if row["m"] else None,
            "performer": row["performer"],
        }

    def get_timeline(self, person_id: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = run_query(TRANSACTION_TIMELINE, {"person_id": person_id, "limit": limit})
        events = []
        for row in rows:
            indicator = "normal"
            if row["amount"] > 10000:
                indicator = "high_value"
            elif row["amount"] > 5000:
                indicator = "elevated"
            events.append({**row, "risk_indicator": indicator})
        return events

    def get_money_laundering_rings(self, limit: int = 10) -> list[dict[str, Any]]:
        return run_query(MONEY_LAUNDERING_RINGS, {"min_amount": 10000, "limit": limit})

    def get_fraud_patterns(self, limit: int = 20) -> list[dict[str, Any]]:
        return run_query(CONNECTED_FRAUD_PATTERNS, {"min_tx_amount": 5000, "limit": limit})

    def build_network_graph(self, node_limit: int = 150) -> dict[str, Any]:
        """Build vis.js compatible node/edge graph from database."""
        rows = run_query(NETWORK_GRAPH, {"node_limit": node_limit})
        nodes_map: dict[str, dict] = {}
        edges: list[dict] = []
        edge_set: set[str] = set()

        def add_node(n) -> None:
            if n is None:
                return
            nid = n.get("id")
            if not nid or nid in nodes_map:
                return
            labels = list(n.labels) if hasattr(n, "labels") else ["Unknown"]
            group = labels[0] if labels else "Unknown"
            label = n.get("name") or n.get("account_number") or n.get("id", nid)
            risk = n.get("risk_score")
            nodes_map[nid] = {
                "id": nid,
                "label": str(label)[:20],
                "group": group,
                "title": f"{group}: {label}",
                "risk_score": risk,
                "color": risk_color(risk) if risk is not None else _group_color(group),
            }

        for row in rows:
            add_node(row.get("n"))
            add_node(row.get("m"))
            rel = row.get("r")
            src = row.get("n")
            tgt = row.get("m")
            if rel is None or src is None or tgt is None:
                continue
            src_id = src.get("id")
            tgt_id = tgt.get("id")
            if not src_id or not tgt_id:
                continue
            rel_type = rel.type if hasattr(rel, "type") else "LINK"
            edge_id = f"{src_id}-{rel_type}-{tgt_id}"
            if edge_id in edge_set:
                continue
            edge_set.add(edge_id)
            edges.append({
                "id": edge_id,
                "from": src_id,
                "to": tgt_id,
                "label": rel_type,
                "dashes": rel_type in ("SHARES_DEVICE_WITH", "SHARES_IP_WITH", "SUSPICIOUS_RELATION"),
            })

        return {"nodes": list(nodes_map.values()), "edges": edges}

    def build_person_graph(self, person_id: str, limit: int = 50) -> dict[str, Any]:
        """Build subgraph centered on a person."""
        rows = run_query(PERSON_NETWORK, {"person_id": person_id, "limit": limit})
        nodes_map: dict[str, dict] = {}
        edges: list[dict] = []
        edge_set: set[str] = set()

        def add_node(node) -> None:
            nid = node.get("id")
            if not nid or nid in nodes_map:
                return
            labels = list(node.labels) if hasattr(node, "labels") else ["Unknown"]
            group = labels[0]
            label = node.get("name") or node.get("account_number") or node.get("id", nid)
            risk = node.get("risk_score")
            nodes_map[nid] = {
                "id": nid,
                "label": str(label)[:20],
                "group": group,
                "title": f"{group}: {label}",
                "risk_score": risk,
                "color": risk_color(risk) if risk is not None else _group_color(group),
            }

        for row in rows:
            path = row.get("path")
            if path is None:
                continue
            for node in path.nodes:
                add_node(node)
            for rel in path.relationships:
                add_node(rel.start_node)
                add_node(rel.end_node)
                src_id = rel.start_node.get("id")
                tgt_id = rel.end_node.get("id")
                if not src_id or not tgt_id:
                    continue
                edge_id = f"{src_id}-{rel.type}-{tgt_id}"
                if edge_id not in edge_set:
                    edge_set.add(edge_id)
                    edges.append({
                        "id": edge_id,
                        "from": src_id,
                        "to": tgt_id,
                        "label": rel.type,
                        "dashes": rel.type in ("SHARES_DEVICE_WITH", "SHARES_IP_WITH", "SUSPICIOUS_RELATION"),
                    })

        return {"nodes": list(nodes_map.values()), "edges": edges}


def _group_color(group: str) -> str:
    return {
        "Person": "#3b82f6",
        "BankAccount": "#8b5cf6",
        "Transaction": "#06b6d4",
        "Merchant": "#f59e0b",
        "Device": "#64748b",
        "IPAddress": "#94a3b8",
    }.get(group, "#64748b")


fraud_service = FraudDetectionService()
