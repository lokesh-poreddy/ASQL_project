# NEXUS-SQL: Adaptive Hybrid Retrieval System

NEXUS-SQL is a high-performance, self-expanding scholarly retrieval system. It fuses the precision of structured SQL queries with the semantic depth of Vector Search, designed to run against Oracle 23ai's advanced vector capabilities. 

## 🚀 Key Features

- **Hybrid Retrieval Engine**: Intelligently routes queries to SQL, Vector Search, or a fused Hybrid mode based on an algorithmic confidence score.
- **Global Data Layer**: Automatically detects when local repository confidence is low and dispatches concurrent queries to external APIs (OpenAlex, Semantic Scholar, Crossref).
- **Self-Expanding Cache**: Fetched papers from global APIs are dynamically normalized, deduplicated, and ingested. Vector embeddings are generated on-the-fly, expanding the local Oracle/In-Memory database seamlessly.
- **QueryIR & Safe SQL**: Analyzes natural language to extract structured intents (e.g., year, citation counts) and generates robust, parameterised SQL (preventing injection).
- **Glassmorphic UI**: A premium, responsive interface featuring interactive status indicators, dynamic origin tracking (`🌐 Source: Semantic Scholar`), and detailed query explanations.
- **Ambiguity Detection**: Employs heuristic-based detection to intercept vague queries and ask users for clarification before hitting the database.

## 🏗️ Architecture & Workflow

The NEXUS-SQL pipeline consists of 19 tightly integrated layers:

1. **User Input** (`frontend/app.js`): User submits a natural language query via the React-inspired Glassmorphism UI.
2. **Ambiguity Detector** (`ambiguity/detector.py`): Scans for unresolved references. Prompts for clarification if needed.
3. **Intent Extractor** (`planning/planner.py`): Extracts filters (e.g., `year > 2020`, `limit 5`) and semantic intents.
4. **Query Router** (`planning/planner.py`): Determines the optimal `RetrievalMode` (SQL, VECTOR, HYBRID). Calculates a `needs_global_lookup` flag based on confidence thresholds.
5. **SQL Generator & Validator** (`sql/generator.py`): Synthesizes safe, bounded SQL statements.
6. **Error Recovery Engine** (`recovery/recovery.py`): Automatically handles SQL execution failures and retries with modified syntax.
7. **Vector Search** (`vector/oracle_search.py`): Executes similarity searches (Cosine/HNSW) against local embeddings.
8. **Hybrid Fusion** (`hybrid/retriever.py`): Merges SQL and Vector results using rank-normalization and configurable `alpha` weights.
9. **Global Orchestrator Fallback** (`external/orchestrator.py`): Triggers concurrent searches against OpenAlex, Semantic Scholar, and Crossref if local results are insufficient.
10. **Ingestion Pipeline** (`ingestion/pipeline.py`): Deduplicates, normalizes, and embeds external results, inserting them into the database cache for immediate re-retrieval.
11. **Explanation Engine** (`explanation/explainer.py`): Compiles latency, SQL text, and routing decisions into a transparent context object for the UI.

## 📦 Getting Started

### Prerequisites
- Python 3.9+
- Oracle 23ai Database (Optional: System runs in In-Memory Test Mode by default)

### Installation
```bash
git clone https://github.com/lokesh-poreddy/ASQL_project.git
cd ASQL_project
pip install -r requirements.txt
```

### Environment Variables
Configure your `.env` file or export the following variables:
```bash
# Optional: Semantic Scholar API Key for higher rate limits
export SEMANTIC_SCHOLAR_API_KEY="your_api_key_here"

# Toggle Oracle 23ai usage
export APP_ENV="test" # 'test' for in-memory, 'prod' for Oracle
```

### Running the Server
```bash
PYTHONPATH=backend python3 backend/app/main.py
```
Access the UI at `http://localhost:8000/`.

## 🧪 Testing
The project includes a robust 120+ test suite covering retrieval algorithms, API integrations, and query routing.
```bash
PYTHONPATH=backend pytest tests/ -v
```

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
