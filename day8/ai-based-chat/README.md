# 🛒 E-Commerce Knowledge Base Chatbot

An AI-powered customer service chatbot that connects a natural language chat interface to your e-commerce database using **OpenAI GPT** as the intelligence layer.

## Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│                  │     │                  │     │                  │
│   Chat UI        │────▶│   Flask API      │────▶│   SQLite DB      │
│   (React)        │     │   + OpenAI       │     │   (ecommerce)    │
│                  │◀────│                  │◀────│                  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
      :3000                    :5000

Flow:
1. Agent types a question in the chat UI
2. Flask API sends the question + DB schema to OpenAI
3. OpenAI generates a SQL SELECT query
4. Flask executes the query on SQLite (read-only)
5. Results are sent back to OpenAI for a human-friendly answer
6. Answer is streamed back to the chat UI
```

## Database Schema

The SQLite database contains 6 tables with realistic Saudi Arabian e-commerce data:

| Table | Records | Description |
|-------|---------|-------------|
| `customers` | 12 | Customer profiles with loyalty tiers |
| `products` | 15 | Products across 5 categories |
| `orders` | 35 | Orders with status tracking |
| `order_items` | ~90 | Line items per order |
| `support_tickets` | 15 | Customer support cases |
| `returns` | 8 | Return requests |

## Quick Start

### 1. Prerequisites
- Python 3.9+
- Node.js 18+ (for the UI)
- An OpenAI API key

### 2. Backend Setup

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Seed the database (only needed once)
python seed_db.py

# Set your OpenAI API key
export OPENAI_API_KEY=sk-your-key-here

# Start the API server
python server.py
```

The API will start at `http://localhost:5000`.

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm start
```

The UI will open at `http://localhost:3000`.

### 4. Start Chatting!

Try these example questions:
- "Show me all orders for Ahmed Al-Rashid"
- "What is the status of order ORD-1005?"
- "Which customers have Gold loyalty tier?"
- "What are the top-selling products?"
- "Show me all open support tickets"
- "How many orders were cancelled last month?"
- "What is the total revenue from Electronics category?"
- "Find the customer with email sara.m@email.com"
- "Which orders have tracking numbers?"
- "Show me all pending returns"

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send a question, get an AI answer |
| GET | `/api/schema` | View the database schema |
| GET | `/api/stats` | Get record counts per table |
| GET | `/api/health` | Health check |

### POST /api/chat

```json
// Request
{ "message": "Show me Ahmed's recent orders" }

// Response
{
  "answer": "Ahmed Al-Rashid has 3 recent orders...",
  "sql": "SELECT ... FROM orders JOIN customers ...",
  "data": { "columns": [...], "rows": [...], "row_count": 3 }
}
```

## Customization

### Use Your Own Database
1. Replace `ecommerce.db` with your SQLite database
2. Update `DB_SCHEMA` in `server.py` to match your schema
3. Restart the server

### Switch to PostgreSQL / MySQL
Replace the `query_db()` function with your preferred database driver. The rest of the code remains the same.

### Use a Different LLM
Replace the OpenAI calls in `generate_sql()` and `generate_answer()` with your preferred LLM (Anthropic Claude, local models via Ollama, etc.)

## Security Notes

- Only `SELECT` queries are allowed — the API rejects all write operations
- The OpenAI API key is stored as an environment variable, never in code
- The database connection is read-only at the application level
- Input is sanitized through OpenAI's structured output

## Tech Stack

- **Frontend**: React + Tailwind-inspired CSS
- **Backend**: Python Flask + Flask-CORS
- **Database**: SQLite3
- **AI**: OpenAI GPT-4o-mini
- **Transport**: REST API (JSON)


