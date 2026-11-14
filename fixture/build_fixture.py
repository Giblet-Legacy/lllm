"""
fixture/build_fixture.py — LLLM test fixture builder

Function:
    Creates a minimal P9-schema SQLite database at fixture/forge.db.
    Seeds it with the specific edge cases required by SPEC.md §13.

Tier:    Tier 1 — LLLM
Licence: MSL-1.0
"""
import os
import json
import sqlite3
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "forge.db")

def _now(offset_days=0):
    dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=offset_days)
    return dt.isoformat()

def build():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    
    # Real P9 schema
    conn.execute("""
        CREATE TABLE claims (
            claim_id TEXT PRIMARY KEY,
            signer TEXT NOT NULL,
            capsule TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            superseded_by TEXT,
            created_at TEXT NOT NULL
        )
    """)

    def insert(cid, capsule, created_days_ago=0, is_active=1, superseded_by=None, signer="did:key:test"):
        conn.execute(
            "INSERT INTO claims (claim_id, signer, capsule, is_active, superseded_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (cid, signer, json.dumps(capsule), is_active, superseded_by, _now(created_days_ago))
        )

    # 1. Standard active claims
    insert("active-sky", {"subject": "sky", "object": "blue", "predicate": "is", "polarity": "affirm"}, 1)
    insert("active-grass", {"subject": "grass", "object": "green", "predicate": "is", "polarity": "affirm"}, 2)

    # 2. Superseded pair
    insert("superseded-old", {"subject": "moon", "object": "cheese", "predicate": "is", "polarity": "affirm"}, 10, is_active=0, superseded_by="superseded-new")
    insert("superseded-new", {"subject": "moon", "object": "rock", "predicate": "is", "polarity": "affirm"}, 5)

    # 3. Inactive (withdrawn)
    insert("inactive-claim", {"subject": "earth", "object": "flat", "predicate": "is", "polarity": "affirm"}, 5, is_active=0)

    # 4. No polarity (must be excluded)
    insert("no-polarity", {"subject": "water", "object": "wet", "predicate": "is"}, 1)

    # 5. Competing claims (Disagree) - both about "apple", different objects
    insert("compete-red", {"subject": "apple", "object": "red", "predicate": "is", "polarity": "affirm"}, 3)
    insert("compete-green", {"subject": "apple", "object": "green", "predicate": "is", "polarity": "affirm"}, 3)

    # 6. Competing claims (Agree) - both about "sun", same object, same polarity
    insert("agree-hot-1", {"subject": "sun", "object": "hot", "predicate": "is", "polarity": "affirm"}, 4)
    insert("agree-hot-2", {"subject": "sun", "object": "hot", "predicate": "is", "polarity": "affirm"}, 2)

    # 7. Self-model claims (for explain_self)
    insert("self-identity", {"subject": "agent://lllm", "object": "low level language model", "predicate": "is", "polarity": "affirm"}, 1)

    conn.commit()
    conn.close()
    print(f"Fixture built at {DB_PATH}")

if __name__ == "__main__":
    build()
