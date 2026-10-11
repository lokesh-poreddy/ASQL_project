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

## 📊 Benchmarking & Experimental Evaluation

NEXUS-SQL includes a comprehensive evaluation and ablation suite evaluating retrieval accuracy, latency percentiles, error recovery, quantization, and resource allocation.

### Running Benchmarks
```bash
# Run the complete experimental evaluation suite
PYTHONPATH=.:backend python3 -m evaluation.run_benchmarks

# Run the CLI baseline runner
cd backend && PYTHONPATH=. python3 -m experiments.runner --experiment all --top-k 10
```

Results and comparison tables are saved to:
- Markdown Report: [`evaluation/results/BENCHMARK_RESULTS.md`](evaluation/results/BENCHMARK_RESULTS.md)
- JSON Artifact: [`evaluation/results/benchmark_results.json`](evaluation/results/benchmark_results.json)
- Benchmark Queries: [`data/benchmark_queries.json`](data/benchmark_queries.json)

### Summary of Results ($k=10$)
| Retrieval Method | P@10 | R@10 | NDCG@10 | MRR | P50 Latency |
|---|---|---|---|---|---|
| **SQL-Only** | 0.2294 | 0.4489 | 0.4468 | 0.3737 | 0.021 ms |
| **Vector-Only** | 0.1325 | 0.3842 | 0.4700 | 0.3712 | 0.026 ms |
| **Static Hybrid ($\alpha=0.5$)** | 0.1875 | 0.4821 | 0.4899 | 0.4349 | 0.111 ms |
| **Adaptive Hybrid (Full)** | **0.2300** | **0.4828** | **0.5212** | **0.4435** | 0.127 ms |

- **Error Recovery Decision Accuracy**: 100.0% (5/5 recovered, 5/5 safely halted)
- **Quantization (INT8 vs FP32)**: 75% storage savings, 31.5% lower latency

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

