# Multimodal RAG — Agent-as-a-Judge

A multimodal, evidence-grounded Retrieval-Augmented Generation system built over the research paper "Agent-as-a-Judge: Evaluating Agents with Agents". The system retrieves text, tables, and images with full page/section citations.

## Problem

Research papers contain more than just text — they include tables with numerical results, figures with visual explanations, and structured sections. A text-only RAG system loses this critical information and fails to answer questions about specific tables, figures, or numerical comparisons.

## Why Text-Only RAG Is Insufficient

| Limitation | Impact |
|:---|:---|
| Tables flattened to text | Numerical queries fail to find exact values |
| Figures/diagrams ignored | Visual questions go unanswered |
| Captions lost | No link between images and their descriptions |
| Page numbers dropped | Citations become fabricated |
| Section structure lost | Context for retrieved chunks is missing |

This system solves these problems with a **multimodal pipeline** that preserves all content types.

## Architecture

```
PDF → Layout-Aware Parser → Normalized Elements → Structure-Aware Chunking
    ├── Text Chunks → Text Embeddings (768d) → PostgreSQL + pgvector
    ├── Table Chunks → Text Embeddings (768d) → PostgreSQL + pgvector
    └── Image Chunks → CLIP Embeddings (512d) → PostgreSQL + pgvector

Query → Input Guardrail → Query Analyzer → Modality Router
    ├── Dense Text Search (pgvector)
    ├── BM25 Keyword Search
    ├── Table Search (pgvector)
    └── Image Search (CLIP text→image)
        → RRF Fusion → Cross-Encoder Reranker → Evidence Validator
        → Context Builder → LLM (Ollama) → Output Guardrail
        → Answer + Citations + Evidence
```

See [docs/architecture.md](docs/architecture.md) for detailed documentation.

## Multimodal Retrieval

The system uses four parallel retrieval branches:

1. **Dense Text Search**: Embeds query with `all-mpnet-base-v2`, searches text chunks via pgvector cosine similarity
2. **BM25 Keyword Search**: Exact term/number matching using `rank_bm25`
3. **Table Search**: Embeds query, searches table chunks embedded from text representations
4. **Image Search**: Encodes query with CLIP text encoder, searches image embeddings in CLIP space

Results are **never compared by raw score** across modalities. They are fused using Reciprocal Rank Fusion.

## Database Schema

Three separate tables for three content types:

- `text_chunks` — embedding VECTOR(768) for text semantic search
- `table_chunks` — embedding VECTOR(768) for table semantic search
- `image_chunks` — image_embedding VECTOR(512) for CLIP image retrieval

Text and image embeddings are stored separately because they come from different models with different dimensions and incompatible vector spaces.

See [docs/database_schema.md](docs/database_schema.md) for full schema.

## Chunking Strategy

- **Text**: Structure-aware chunking (~500 tokens, 10% overlap), respects heading boundaries
- **Tables**: Remain atomic — never split across chunks
- **Images**: Remain atomic — linked to captions and surrounding context
- **Captions**: Linked to their figures for hybrid text+image retrieval

## CLIP Usage

CLIP ViT-B/32 (`openai/clip-vit-base-patch32`) provides:
- **Image Embedding** (512d): Visual features of extracted figures
- **Text-to-Image Search**: Query text encoded by CLIP text encoder, compared against image embeddings

This enables answering questions like "What does Figure 1 show?" by retrieving the actual figure.

## Hybrid Retrieval + RRF

Reciprocal Rank Fusion combines rankings from all retrieval branches:

```
RRF(d) = Σ 1 / (k + rank(d))    where k=60 (configurable)
```

This allows fair fusion of results from incompatible scoring systems (cosine similarity, BM25, CLIP scores).

## Reranking

After RRF fusion, top candidates are reranked using `cross-encoder/ms-marco-MiniLM-L-6-v2` for maximum precision. Only text-based candidates are reranked (cross-encoders are text-only).

## LangGraph Workflow

The query pipeline is a LangGraph StateGraph:

```
Input Guardrail → Query Analyzer → Retrieve (Text + BM25 + Table + Image)
→ RRF Fusion → Reranker → Evidence Validator
    ├── (sufficient) → Context Builder → LLM → Output Guardrail → Answer
    └── (insufficient) → Query Rewriter → Retry Retrieval
```

## Guardrails

- **Input**: PII detection/redaction (emails, phones, SSNs) before query processing
- **Output**: Grounding validation, citation verification, PII leak prevention
- If evidence is insufficient, the system says so instead of hallucinating

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL with pgvector (Neon recommended)
- Ollama (for local LLM)
- NVIDIA GPU (RTX 4060 or similar) for CLIP/embeddings

### Installation

```bash
git clone <repo-url>
cd Enverus-RAG
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Environment Variables

```bash
cp .env.example .env
# Edit .env with your database URL and model preferences
```

Key variables:

| Variable | Default | Description |
|:---|:---|:---|
| DATABASE_URL | - | Neon PostgreSQL connection string |
| OLLAMA_BASE_URL | http://localhost:11434 | Ollama server URL |
| LLM_MODEL | llama3.1:8b | Ollama model name |
| TEXT_EMBEDDING_MODEL | sentence-transformers/all-mpnet-base-v2 | Text embedding model |
| CLIP_MODEL | openai/clip-vit-base-patch32 | CLIP model |
| RERANKER_MODEL | cross-encoder/ms-marco-MiniLM-L-6-v2 | Reranker model |

See [.env.example](.env.example) for all variables.

## Running Locally

### 1. Start Ollama

```bash
ollama serve
ollama pull llama3.1:8b
```

### 2. Start Backend

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Ingest PDF

```bash
python scripts/ingest.py --pdf data/documents/agent_as_judge.pdf
```

### 4. Start Frontend

```bash
streamlit run frontend/streamlit_app.py
```

## Running with Docker

```bash
docker-compose up --build
```

This starts: backend (port 8000), frontend (port 8501), Ollama (port 11434).

## API Endpoints

### POST /api/documents/upload

Upload and ingest a PDF.

```bash
curl -X POST -F "file=@paper.pdf" http://localhost:8000/api/documents/upload
```

### GET /api/documents/{document_id}

Get document status and chunk counts.

### POST /api/chat

Query the RAG system.

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"document_id": "...", "query": "What is the DevAI dataset?"}'
```

## Example Queries

| Query | Expected Behavior |
|:---|:---|
| "What is the DevAI dataset?" | Text retrieval → factual answer with page citation |
| "What was the cost of OpenHands?" | Table + text retrieval → numerical answer |
| "What does Figure 1 show?" | CLIP image retrieval → figure display + explanation |
| "What is the alignment rate with human judges?" | Table retrieval → numerical answer with table citation |
| "Which system was most expensive?" | Table retrieval → comparison from table data |

## Evaluation

```bash
python scripts/evaluate.py --document-id <your-document-id>
```

Measures: retrieval success, evidence relevance, citation correctness, answer quality, modality routing accuracy.

## Limitations

- BM25 index is rebuilt in-memory per query (could be cached for production)
- CLIP ViT-B/32 provides basic visual understanding (SigLIP would improve accuracy)
- Single document at a time (multi-document support would need cross-document retrieval)
- Reranker only handles text candidates (image reranking would need a multimodal reranker)
- Evidence validation uses heuristic grounding check (could use NLI model)

## Future Improvements

- Replace CLIP with SigLIP for better visual understanding
- Add ColPali for direct visual document retrieval
- Multi-document support with cross-document linking
- NLI-based evidence grounding instead of keyword overlap
- Streaming LLM responses in the frontend
- Production task queue (Celery) for async ingestion
- Caching BM25 indexes and embedding results
- Fine-tuned embedding models for research paper domain
#   E n v e r u s  
 