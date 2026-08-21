"""
Seed CognoDB with realistic fraud detection data (~140 nodes).

Usage (from backend/):
    python -m scripts.seed

Requires COGNO_URI, COGNO_USER, COGNO_PASSWORD in .env or environment.
"""

import hashlib
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Allow running as module from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.database import close_driver, get_session, run_write  # noqa: E402

# ── Deterministic seed for reproducible demo ──────────────────────────────────
random.seed(42)

FIRST_NAMES = [
    "Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Henry",
    "Iris", "Jack", "Karen", "Leo", "Maria", "Nathan", "Olivia", "Paul",
    "Quinn", "Rachel", "Sam", "Tina", "Uma", "Victor", "Wendy", "Xavier",
    "Yuki", "Zara", "Aaron", "Beth", "Chris", "Diana", "Ethan", "Fiona",
    "George", "Hannah", "Ivan", "Julia", "Kevin", "Laura", "Mike", "Nina",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Wilson", "Anderson", "Taylor",
    "Thomas", "Moore", "Jackson", "Martin", "Lee", "Thompson", "White",
]

BANKS = ["Chase", "Wells Fargo", "Bank of America", "Citibank", "US Bank", "PNC"]
MERCHANT_CATEGORIES = [
    ("Amazon", "E-commerce"), ("Best Buy", "Electronics"), ("Shell Gas", "Fuel"),
    ("Walmart", "Retail"), ("Starbucks", "Food"), ("Netflix", "Subscription"),
    ("Apple Store", "Electronics"), ("Target", "Retail"), ("CVS Pharmacy", "Health"),
    ("Home Depot", "Home Improvement"), ("CryptoExchange", "Crypto"),
    ("Offshore Holdings", "Finance"), ("Luxury Watches Inc", "Luxury"),
    ("QuickCash ATM", "ATM"), ("Global Remittance", "Transfer"),
]

LOCATIONS = [
    "New York, US", "Los Angeles, US", "Chicago, US", "London, UK",
    "Toronto, CA", "Sydney, AU", "Berlin, DE", "Singapore, SG",
    "Dubai, AE", "Moscow, RU", "Lagos, NG", "Panama City, PA",
]

OS_LIST = ["Windows 11", "macOS 14", "Ubuntu 22.04", "iOS 17", "Android 14"]
BROWSERS = ["Chrome 120", "Firefox 121", "Safari 17", "Edge 120"]


def ssn_hash(ssn: str) -> str:
    return hashlib.sha256(ssn.encode()).hexdigest()[:16]


def ts(days_ago: int, hour: int = 12) -> str:
    dt = datetime.now(UTC) - timedelta(days=days_ago, hours=random.randint(0, 8))
    dt = dt.replace(hour=hour, minute=random.randint(0, 59))
    return dt.isoformat() + "Z"


def clear_database():
    print("Clearing existing data...")
    run_write("MATCH (n) DETACH DELETE n")


def create_constraints():
    """Create uniqueness constraints for id properties."""
    constraints = [
        "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
        "CREATE CONSTRAINT account_id IF NOT EXISTS FOR (a:BankAccount) REQUIRE a.id IS UNIQUE",
        "CREATE CONSTRAINT tx_id IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE",
        "CREATE CONSTRAINT merchant_id IF NOT EXISTS FOR (m:Merchant) REQUIRE m.id IS UNIQUE",
        "CREATE CONSTRAINT device_id IF NOT EXISTS FOR (d:Device) REQUIRE d.id IS UNIQUE",
        "CREATE CONSTRAINT ip_id IF NOT EXISTS FOR (ip:IPAddress) REQUIRE ip.id IS UNIQUE",
    ]
    with get_session() as session:
        for c in constraints:
            try:
                session.run(c)
            except Exception:
                pass  # constraint may already exist


def seed_data():
    persons = []
    accounts = []
    devices = []
    ips = []
    merchants = []
    transactions = []

    # ── Normal population (10 persons) ────────────────────────────────────────
    # Kept deliberately compact so the complete dataset remains within the
    # assignment's requested 100–200 node range while still feeling realistic.
    normal_person_count = 10
    for i in range(normal_person_count):
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        pid = f"P-{1000 + i:04d}"
        risk = random.randint(5, 35)
        persons.append({
            "id": pid, "name": f"{fname} {lname}",
            "email": f"{fname.lower()}.{lname.lower()}{i}@email.com",
            "ssn_hash": ssn_hash(f"{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(1000,9999)}"),
            "phone": f"+1-555-{random.randint(100,999):03d}-{random.randint(1000,9999):04d}",
            "risk_score": risk, "created_at": ts(random.randint(365, 1000)),
        })
        aid = f"A-{1000 + i:04d}"
        accounts.append({
            "id": aid, "account_number": f"****{random.randint(1000,9999)}",
            "bank_name": random.choice(BANKS), "account_type": random.choice(["checking", "savings"]),
            "balance": round(random.uniform(1000, 50000), 2),
            "opened_date": ts(random.randint(200, 800)),
            "owner_id": pid,
        })
        did = f"D-{1000 + i:04d}"
        devices.append({
            "id": did, "device_fingerprint": hashlib.md5(f"device-{i}".encode()).hexdigest(),
            "os": random.choice(OS_LIST), "browser": random.choice(BROWSERS),
            "owner_id": pid,
        })
        iid = f"IP-{1000 + i:04d}"
        ips.append({
            "id": iid, "ip": f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            "geolocation": random.choice(LOCATIONS[:6]),
            "is_proxy": False, "owner_id": pid,
        })

    # ── Merchants (15) ──────────────────────────────────────────────────────
    for i, (name, cat) in enumerate(MERCHANT_CATEGORIES):
        mid = f"M-{1000 + i:04d}"
        risk = 80 if cat in ("Crypto", "Finance", "Luxury") else random.randint(10, 40)
        merchants.append({
            "id": mid, "name": name, "category": cat,
            "location": random.choice(LOCATIONS),
            "risk_score": risk,
        })

    # ── Fraud Ring A: Money laundering (4 persons, circular transfers) ────────
    ring_a_persons = []
    ring_a_accounts = []
    for i in range(4):
        pid = f"P-RING-A-{i}"
        ring_a_persons.append({
            "id": pid, "name": f"Ring Member Alpha-{i}",
            "email": f"ringa{i}@shadowmail.net",
            "ssn_hash": ssn_hash(f"ring-a-{i}"),
            "phone": f"+1-555-900{i}-0000",
            "risk_score": random.randint(75, 95),
            "created_at": ts(random.randint(30, 90)),
        })
        aid = f"A-RING-A-{i}"
        ring_a_accounts.append({
            "id": aid, "account_number": f"****RING{i}",
            "bank_name": "Offshore Bank Ltd", "account_type": "business",
            "balance": round(random.uniform(100000, 500000), 2),
            "opened_date": ts(random.randint(30, 60)),
            "owner_id": pid,
        })
    persons.extend(ring_a_persons)
    accounts.extend(ring_a_accounts)

    # Circular transactions for ring A
    ring_txs = []
    for i in range(4):
        from_acc = ring_a_accounts[i]
        to_acc = ring_a_accounts[(i + 1) % 4]
        tid = f"TX-RING-A-{i}"
        ring_txs.append({
            "id": tid, "amount": round(random.uniform(15000, 50000), 2),
            "timestamp": ts(random.randint(1, 14), hour=3),
            "transaction_type": "wire_transfer",
            "ip_address": "185.220.101.42",
            "device_id": "D-RING-SHARED",
            "performer_id": ring_a_persons[i]["id"],
            "from_account_id": from_acc["id"],
            "to_account_id": to_acc["id"],
            "merchant_id": merchants[-2]["id"],  # Global Remittance
        })
    transactions.extend(ring_txs)

    # ── Fraud Ring B: Shared device identity fraud (5 persons, 1 device) ────
    shared_device_id = "D-FRAUD-SHARED"
    shared_device = {
        "id": shared_device_id,
        "device_fingerprint": hashlib.md5(b"fraud-device-shared").hexdigest(),
        "os": "Windows 11", "browser": "Chrome 120",
    }
    devices.append(shared_device)

    ring_b_persons = []
    for i in range(5):
        pid = f"P-RING-B-{i}"
        ring_b_persons.append({
            "id": pid, "name": f"Alias Identity {i}",
            "email": f"alias{i}@tempmail.io",
            "ssn_hash": ssn_hash(f"different-ssn-{i}"),
            "phone": f"+1-555-800{i}-0000",
            "risk_score": random.randint(70, 90),
            "created_at": ts(random.randint(10, 45)),
        })
        aid = f"A-RING-B-{i}"
        accounts.append({
            "id": aid, "account_number": f"****ALIAS{i}",
            "bank_name": random.choice(BANKS), "account_type": "checking",
            "balance": round(random.uniform(500, 15000), 2),
            "opened_date": ts(random.randint(10, 40)),
            "owner_id": pid,
        })
        # Each alias has the shared fraud device plus a distinct device. This
        # intentionally meets the multi-device criterion in the connected
        # fraud-pattern query and makes the scenario demonstrable in the UI.
        devices.append({**shared_device, "owner_id": pid})
        devices.append({
            "id": f"D-RING-B-{i}",
            "device_fingerprint": hashlib.md5(f"ring-b-device-{i}".encode()).hexdigest(),
            "os": random.choice(OS_LIST), "browser": random.choice(BROWSERS),
            "owner_id": pid,
        })

    persons.extend(ring_b_persons)

    # Multiple IPs for ring B persons (identity fraud pattern)
    proxy_ips = []
    for i in range(6):
        iid = f"IP-PROXY-{i}"
        proxy_ips.append({
            "id": iid,
            "ip": f"45.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,254)}",
            "geolocation": random.choice(LOCATIONS[6:]),
            "is_proxy": True,
        })
    ips.extend(proxy_ips)

    for person in ring_b_persons:
        for ip in random.sample(proxy_ips, k=min(4, len(proxy_ips))):
            ips.append({**ip, "owner_id": person["id"]})

    # Large transactions for ring B
    for i, person in enumerate(ring_b_persons):
        acc = next(a for a in accounts if a.get("owner_id") == person["id"])
        for j in range(random.randint(2, 4)):
            transactions.append({
                "id": f"TX-RING-B-{i}-{j}",
                "amount": round(random.uniform(6000, 25000), 2),
                "timestamp": ts(random.randint(1, 20)),
                "transaction_type": "purchase",
                "ip_address": proxy_ips[i % len(proxy_ips)]["ip"],
                "device_id": shared_device_id,
                "performer_id": person["id"],
                "from_account_id": acc["id"],
                "to_account_id": None,
                "merchant_id": random.choice([merchants[10]["id"], merchants[12]["id"]]),
            })

    # ── Fraud Ring C: Suspicious transaction links ──────────────────────────
    sus_person = {
        "id": "P-SUSPECT-01", "name": "Marcus Webb",
        "email": "m.webb@protonmail.com",
        "ssn_hash": ssn_hash("suspect-01"),
        "phone": "+1-555-777-0001",
        "risk_score": 88, "created_at": ts(60),
    }
    persons.append(sus_person)
    sus_account = {
        "id": "A-SUSPECT-01", "account_number": "****9999",
        "bank_name": "Chase", "account_type": "checking",
        "balance": 75000.0, "opened_date": ts(90),
        "owner_id": sus_person["id"],
    }
    accounts.append(sus_account)
    sus_device = {
        "id": "D-SUSPECT-01",
        "device_fingerprint": hashlib.md5(b"suspect-device").hexdigest(),
        "os": "Ubuntu 22.04", "browser": "Firefox 121",
        "owner_id": sus_person["id"],
    }
    devices.append(sus_device)

    sus_txs = []
    for i in range(5):
        sus_txs.append({
            "id": f"TX-SUS-{i:02d}",
            "amount": round(random.uniform(8000, 45000), 2),
            "timestamp": ts(random.randint(1, 10), hour=2),
            "transaction_type": "wire_transfer",
            "ip_address": "185.220.101.42",
            "device_id": "D-SUSPECT-01",
            "performer_id": sus_person["id"],
            "from_account_id": sus_account["id"],
            "to_account_id": ring_a_accounts[0]["id"] if i % 2 == 0 else None,
            "merchant_id": merchants[10]["id"] if i % 2 == 1 else None,
        })
    transactions.extend(sus_txs)

    # ── Normal transactions for regular persons ─────────────────────────────
    for i in range(normal_person_count):
        pid = f"P-{1000 + i:04d}"
        acc = next(a for a in accounts if a.get("owner_id") == pid)
        for j in range(random.randint(3, 4)):
            transactions.append({
                "id": f"TX-{1000 + i:04d}-{j}",
                "amount": round(random.uniform(10, 2000), 2),
                "timestamp": ts(random.randint(1, 90)),
                "transaction_type": random.choice(["purchase", "transfer", "withdrawal"]),
                "ip_address": ips[i]["ip"] if i < len(ips) else "127.0.0.1",
                "device_id": devices[i]["id"] if i < len(devices) else None,
                "performer_id": pid,
                "from_account_id": acc["id"],
                "to_account_id": None,
                "merchant_id": random.choice(merchants[:8])["id"],
            })

    return persons, accounts, devices, ips, merchants, transactions


def write_to_db(persons, accounts, devices, ips, merchants, transactions):
    """Batch write all nodes and relationships."""
    with get_session() as session:
        def tx_fn(tx):
            # Persons
            for p in persons:
                tx.run("""
                    MERGE (p:Person {id: $id})
                    SET p.name = $name, p.email = $email, p.ssn_hash = $ssn_hash,
                        p.phone = $phone, p.risk_score = $risk_score, p.created_at = $created_at
                """, **p)

            # Bank accounts + OWNS
            for a in accounts:
                tx.run("""
                    MERGE (a:BankAccount {id: $id})
                    SET a.account_number = $account_number, a.bank_name = $bank_name,
                        a.account_type = $account_type, a.balance = $balance,
                        a.opened_date = $opened_date
                    WITH a
                    MATCH (p:Person {id: $owner_id})
                    MERGE (p)-[:OWNS]->(a)
                """, **a)

            # Merchants
            for m in merchants:
                tx.run("""
                    MERGE (m:Merchant {id: $id})
                    SET m.name = $name, m.category = $category,
                        m.location = $location, m.risk_score = $risk_score
                """, **m)

            # Devices + HAS_DEVICE
            seen_devices = set()
            for d in devices:
                if d["id"] not in seen_devices:
                    tx.run("""
                        MERGE (d:Device {id: $id})
                        SET d.device_fingerprint = $device_fingerprint,
                            d.os = $os, d.browser = $browser
                    """, id=d["id"], device_fingerprint=d["device_fingerprint"],
                        os=d["os"], browser=d["browser"])
                    seen_devices.add(d["id"])
                if d.get("owner_id"):
                    tx.run("""
                        MATCH (p:Person {id: $owner_id}), (d:Device {id: $id})
                        MERGE (p)-[:HAS_DEVICE]->(d)
                    """, owner_id=d["owner_id"], id=d["id"])

            # IPs + USES_IP
            seen_ips = set()
            for ip in ips:
                if ip["id"] not in seen_ips:
                    tx.run("""
                        MERGE (ip:IPAddress {id: $id})
                        SET ip.ip = $ip_addr, ip.geolocation = $geolocation,
                            ip.is_proxy = $is_proxy
                    """, id=ip["id"], ip_addr=ip["ip"],
                        geolocation=ip["geolocation"], is_proxy=ip["is_proxy"])
                    seen_ips.add(ip["id"])
                if ip.get("owner_id"):
                    tx.run("""
                        MATCH (p:Person {id: $owner_id}), (ip:IPAddress {id: $id})
                        MERGE (p)-[:USES_IP]->(ip)
                    """, owner_id=ip["owner_id"], id=ip["id"])

            # Transactions
            for t in transactions:
                tx.run("""
                    MERGE (t:Transaction {id: $id})
                    SET t.amount = $amount, t.timestamp = $timestamp,
                        t.transaction_type = $transaction_type,
                        t.ip_address = $ip_address, t.device_id = $device_id
                """, id=t["id"], amount=t["amount"], timestamp=t["timestamp"],
                    transaction_type=t["transaction_type"],
                    ip_address=t.get("ip_address"), device_id=t.get("device_id"))

                tx.run("""
                    MATCH (p:Person {id: $performer_id}), (t:Transaction {id: $id})
                    MERGE (p)-[:PERFORMS]->(t)
                """, performer_id=t["performer_id"], id=t["id"])

                if t.get("from_account_id"):
                    tx.run("""
                        MATCH (t:Transaction {id: $id}), (a:BankAccount {id: $from_id})
                        MERGE (t)-[:FROM]->(a)
                    """, id=t["id"], from_id=t["from_account_id"])

                if t.get("to_account_id"):
                    tx.run("""
                        MATCH (t:Transaction {id: $id}), (a:BankAccount {id: $to_id})
                        MERGE (t)-[:TO]->(a)
                    """, id=t["id"], to_id=t["to_account_id"])

                if t.get("merchant_id"):
                    tx.run("""
                        MATCH (t:Transaction {id: $id}), (m:Merchant {id: $merchant_id})
                        MERGE (t)-[:AT]->(m)
                    """, id=t["id"], merchant_id=t["merchant_id"])

        session.execute_write(tx_fn)

    # Post-process: detect and create pattern relationships
    print("Detecting fraud patterns...")
    pattern_queries = [
        # SHARES_DEVICE_WITH
        """
        MATCH (p1:Person)-[:HAS_DEVICE]->(d:Device)<-[:HAS_DEVICE]-(p2:Person)
        WHERE p1.id < p2.id
        MERGE (p1)-[:SHARES_DEVICE_WITH]->(p2)
        """,
        # SHARES_IP_WITH
        """
        MATCH (p1:Person)-[:USES_IP]->(ip:IPAddress)<-[:USES_IP]-(p2:Person)
        WHERE p1.id < p2.id
        MERGE (p1)-[:SHARES_IP_WITH]->(p2)
        """,
        # SUSPICIOUS_RELATION between high-value txs from same person within 24h
        """
        MATCH (p:Person)-[:PERFORMS]->(t1:Transaction), (p)-[:PERFORMS]->(t2:Transaction)
        WHERE t1.id < t2.id AND t1.amount > 5000 AND t2.amount > 5000
          AND t1.ip_address = t2.ip_address
        MERGE (t1)-[:SUSPICIOUS_RELATION]->(t2)
        """,
    ]
    with get_session() as session:
        for q in pattern_queries:
            session.run(q)


def print_stats():
    from app.database import run_query
    stats = run_query("""
        MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY label
    """)
    print("\n── Node counts ──")
    total = 0
    for row in stats:
        print(f"  {row['label']}: {row['count']}")
        total += row["count"]
    print(f"  TOTAL: {total}")

    rel_stats = run_query("""
        MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count ORDER BY type
    """)
    print("\n── Relationship counts ──")
    for row in rel_stats:
        print(f"  {row['type']}: {row['count']}")


def main():
    print("FraudLens — CognoDB Seed Script")
    print("=" * 40)
    clear_database()
    create_constraints()
    persons, accounts, devices, ips, merchants, transactions = seed_data()
    print(f"Seeding {len(persons)} persons, {len(accounts)} accounts, "
          f"{len(transactions)} transactions...")
    write_to_db(persons, accounts, devices, ips, merchants, transactions)
    print_stats()
    close_driver()
    print("\nDone! Start the API with: uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
