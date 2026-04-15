"""
Knowledge Base Chatbot API Server
----------------------------------
Bridges a customer-service chat UI with an e-commerce SQLite database
using OpenAI's GPT model to translate natural language into SQL queries.

Flow:
  1. Customer service agent types a question
  2. This server sends the DB schema + question to OpenAI
  3. OpenAI returns a SQL query
  4. Server executes SQL safely (read-only) on the DB
  5. Results are sent back to OpenAI for a human-friendly answer
  6. Final answer is returned to the UI
"""

import os
import json
import sqlite3
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI

# ──────────────────── Config ────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "ecommerce.db")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

app = Flask(__name__)
CORS(app)

# ──────────────────── Database helpers ────────────────────

DB_SCHEMA = """
DATABASE SCHEMA:
================

TABLE: customers
  - id (INTEGER, PK)
  - first_name (TEXT)
  - last_name (TEXT)
  - email (TEXT, UNIQUE)
  - phone (TEXT)
  - address (TEXT)
  - city (TEXT)
  - country (TEXT, default 'Saudi Arabia')
  - created_at (TEXT, ISO date)
  - loyalty_tier (TEXT: Bronze/Silver/Gold/Platinum)

TABLE: products
  - id (INTEGER, PK)
  - name (TEXT)
  - sku (TEXT, UNIQUE)
  - category (TEXT: Electronics, Home & Kitchen, Beauty, Fashion, Food & Gifts)
  - price (REAL, in SAR)
  - stock_quantity (INTEGER)
  - description (TEXT)

TABLE: orders
  - id (INTEGER, PK)
  - order_number (TEXT, UNIQUE, format: ORD-XXXX)
  - customer_id (INTEGER, FK -> customers.id)
  - status (TEXT: pending/confirmed/shipped/delivered/cancelled)
  - total_amount (REAL, in SAR)
  - shipping_address (TEXT)
  - payment_method (TEXT)
  - created_at (TEXT, ISO datetime)
  - updated_at (TEXT, ISO datetime)
  - tracking_number (TEXT, nullable)
  - estimated_delivery (TEXT, ISO date, nullable)
  - notes (TEXT, nullable)

TABLE: order_items
  - id (INTEGER, PK)
  - order_id (INTEGER, FK -> orders.id)
  - product_id (INTEGER, FK -> products.id)
  - quantity (INTEGER)
  - unit_price (REAL)

TABLE: support_tickets
  - id (INTEGER, PK)
  - ticket_number (TEXT, UNIQUE, format: TKT-XXXX)
  - customer_id (INTEGER, FK -> customers.id)
  - order_id (INTEGER, FK -> orders.id, nullable)
  - subject (TEXT)
  - description (TEXT)
  - status (TEXT: open/in_progress/resolved/closed)
  - priority (TEXT: low/medium/high)
  - created_at (TEXT, ISO datetime)
  - resolved_at (TEXT, nullable)

TABLE: returns
  - id (INTEGER, PK)
  - return_number (TEXT, UNIQUE, format: RET-XXXX)
  - order_id (INTEGER, FK -> orders.id)
  - customer_id (INTEGER, FK -> customers.id)
  - reason (TEXT)
  - status (TEXT: requested/approved/completed/rejected)
  - refund_amount (REAL)
  - created_at (TEXT, ISO datetime)
  - processed_at (TEXT, nullable)

RELATIONSHIPS:
  orders.customer_id -> customers.id
  order_items.order_id -> orders.id
  order_items.product_id -> products.id
  support_tickets.customer_id -> customers.id
  support_tickets.order_id -> orders.id
  returns.order_id -> orders.id
  returns.customer_id -> customers.id
"""


def query_db(sql: str) -> dict:
    """Execute a read-only SQL query and return results."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        # Safety: only allow SELECT statements
        stripped = sql.strip().upper()
        if not stripped.startswith("SELECT"):
            return {"error": "Only SELECT queries are allowed for security."}
        cur.execute(sql)
        rows = [dict(r) for r in cur.fetchall()]
        columns = [desc[0] for desc in cur.description] if cur.description else []
        return {"columns": columns, "rows": rows, "row_count": len(rows)}
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


# ──────────────────── OpenAI integration ────────────────────

SYSTEM_PROMPT_SQL = f"""You are a SQL expert for an e-commerce customer service system.
Given a natural language question from a customer service agent, generate a SQLite query
to retrieve the relevant data.

{DB_SCHEMA}

RULES:
1. ONLY output a valid SQLite SELECT query — nothing else.
2. Never use INSERT, UPDATE, DELETE, DROP, ALTER, or any write operation.
3. Use JOINs when the question spans multiple tables.
4. Limit results to 20 rows unless the user asks for more.
5. For customer lookups, search by name (first_name, last_name), email, or phone.
6. For order lookups, search by order_number or customer details.
7. Use LIKE with % wildcards for partial text matching.
8. All monetary values are in SAR (Saudi Riyal).
9. Return only the raw SQL query, no markdown, no explanation.
"""

SYSTEM_PROMPT_ANSWER = """You are a friendly, professional customer service assistant
for a Saudi Arabian e-commerce company. Given the original question and the database
results, provide a clear, helpful answer.

RULES:
1. Be concise but thorough.
2. Format monetary values with SAR currency.
3. Format dates in a readable way.
4. If no results were found, say so politely and suggest alternatives.
5. Never reveal raw SQL or internal database details to the user.
6. Use bullet points or tables for listing multiple items.
7. Be warm and courteous — address the agent professionally.
8. If the data seems incomplete, mention it transparently.
"""


def get_openai_client():
    """Create OpenAI client. Raises if no API key configured."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")
    return OpenAI(api_key=OPENAI_API_KEY)


def generate_sql(question: str) -> str:
    """Ask OpenAI to convert a natural-language question to SQL."""
    client = get_openai_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_SQL},
            {"role": "user", "content": question},
        ],
    )
    sql = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    sql = re.sub(r"^```(?:sql)?\s*", "", sql)
    sql = re.sub(r"\s*```$", "", sql)
    return sql


def generate_answer(question: str, sql: str, db_result: dict) -> str:
    """Ask OpenAI to create a human-friendly answer from DB results."""
    client = get_openai_client()
    context = json.dumps(db_result, indent=2, default=str)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_ANSWER},
            {
                "role": "user",
                "content": (
                    f"QUESTION: {question}\n\n"
                    f"DATABASE RESULTS:\n{context}\n\n"
                    "Please provide a helpful answer based on these results."
                ),
            },
        ],
    )
    return response.choices[0].message.content.strip()


# ──────────────────── API Routes ────────────────────

@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint.
    Body: { "message": "natural language question" }
    Returns: { "answer": "...", "sql": "...", "data": {...} }
    """
    body = request.get_json(force=True)
    question = body.get("message", "").strip()
    if not question:
        return jsonify({"error": "Message is required."}), 400

    try:
        # Step 1: Convert question to SQL
        sql = generate_sql(question)

        # Step 2: Execute SQL on database
        db_result = query_db(sql)

        # Step 3: Generate human-friendly answer
        if "error" in db_result:
            answer = generate_answer(question, sql, db_result)
        else:
            answer = generate_answer(question, sql, db_result)

        return jsonify({
            "answer": answer,
            "sql": sql,
            "data": db_result,
        })

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 500
    except Exception as e:
        return jsonify({"error": f"Something went wrong: {str(e)}"}), 500


@app.route("/api/schema", methods=["GET"])
def schema():
    """Return the database schema for reference."""
    return jsonify({"schema": DB_SCHEMA})


@app.route("/api/stats", methods=["GET"])
def stats():
    """Return quick database stats."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    result = {}
    for table in ["customers", "products", "orders", "order_items", "support_tickets", "returns"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        result[table] = cur.fetchone()[0]
    conn.close()
    return jsonify(result)


@app.route("/api/health", methods=["GET"])
def health():
    """Health check."""
    has_key = bool(OPENAI_API_KEY)
    db_ok = os.path.exists(DB_PATH)
    return jsonify({
        "status": "ok" if (has_key and db_ok) else "degraded",
        "openai_configured": has_key,
        "database_exists": db_ok,
    })


# ──────────────────── Startup ────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  E-Commerce Knowledge Base Chatbot API")
    print("=" * 60)
    print(f"  Database  : {DB_PATH}")
    print(f"  OpenAI Key: {'configured' if OPENAI_API_KEY else '⚠ NOT SET'}")
    print()
    if not OPENAI_API_KEY:
        print("  ⚠  Set OPENAI_API_KEY env variable before using /api/chat")
        print("     export OPENAI_API_KEY=sk-...")
    print()
    app.run(host="0.0.0.0", port=8001, debug=True)
