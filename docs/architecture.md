# Architecture

## System Overview

This is a multimodal, evidence-grounded RAG system that processes research papers to answer questions using text, tables, and images. The system preserves page numbers, sections, captions, and relationships between content elements.

## Why Multimodal RAG?

A text-only RAG loses critical information from research papers:
- **Tables** contain numerical results that plain text search misses
- **Figures/diagrams** communicate concepts that text alone cannot capture
- **Captions** link visual elements to their meaning
- **Structure** (sections, headings) provides essential context for retrieval

## Data Flow

```
PDF → Parser → Normalizer → Classifier → Chunker
                                           ├── Text Chunks → Text Embeddings (768d) → PostgreSQL
                                           ├── Table Chunks → Text Embeddings (768d) → PostgreSQL  
                                           └── Image Chunks → CLIP Embeddings (512d) → PostgreSQL
```

## Ingestion Pipeline

1. **Parser** (`app/ingestion/parser.py`): Uses `pymupdf4llm` for layout-aware markdown extraction and raw `PyMuPDF` for image/bbox extraction
2. **Normalizer** (`app/ingestion/normalizer.py`): Converts parser output into `ParsedElement` schema, classifying content as text/heading/table/image/caption/list
3. **Chunker** (`app/ingestion/chunker.py`): Structure-aware chunking (~500 tokens, 10% overlap). Tables and images remain atomic.
4. **Table Processor** (`app/ingestion/table_processor.py`): Parses markdown tables into structured JSONB data and generates text representations
5. **Image Processor** (`app/ingestion/image_processor.py`): Extracts images, saves to disk, links captions, builds text representations

## Why Separate Embedding Spaces

Text embeddings (768d) and image embeddings (512d) live in **different vector spaces**:
- Text embeddings use `all-mpnet-base-v2` trained on text similarity
- Image embeddings use CLIP ViT-B/32 trained on image-text alignment

These are **never directly compared**. Instead, each branch searches its own space independently, and results are fused at the ranking level using Reciprocal Rank Fusion (RRF).

## Retrieval Architecture

Four parallel retrieval branches:
1. **Dense Text Search**: Query → text embedding → pgvector cosine similarity on `text_chunks`
2. **BM25 Keyword Search**: Query → tokenize → BM25 scoring over all text chunks
3. **Table Search**: Query → text embedding → pgvector cosine similarity on `table_chunks`
4. **Image Search**: Query → CLIP text encoding → pgvector cosine similarity on `image_chunks`

## RRF Fusion

Reciprocal Rank Fusion combines rankings (not raw scores) from all branches:

```
RRF(d) = Σ 1 / (k + rank(d))    where k=60
```

This allows fair combination of results from incompatible scoring systems.

## Reranking

After RRF, the top 10-15 candidates are reranked using `cross-encoder/ms-marco-MiniLM-L-6-v2` for maximum precision. Only text-based candidates are reranked; images pass through by position since cross-encoders are text-only.

## LangGraph Workflow

The query pipeline is implemented as a LangGraph StateGraph:

```
Input Guardrail → Query Analyzer → Retrieve (Text + BM25 + Table + Image)
→ RRF Fusion → Reranker → Evidence Validator
→ (sufficient) Context Builder → LLM → Output Guardrail → Answer
→ (insufficient) Query Rewriter → retry retrieval
```

## Guardrails

- **Input**: PII detection/anonymization before processing
- **Output**: Grounding validation ensuring answers match evidence, citation verification, PII check

## Technology Stack

| Component | Technology |
|:---|:---|
| PDF Parser | pymupdf4llm + PyMuPDF |
| Text Embeddings | sentence-transformers/all-mpnet-base-v2 (768d) |
| Image Embeddings | openai/clip-vit-base-patch32 (512d) |
| Reranker | cross-encoder/ms-marco-MiniLM-L-6-v2 |
| LLM | Ollama (configurable model) |
| Database | PostgreSQL + pgvector (Neon) |
| BM25 | rank-bm25 |
| Workflow | LangGraph |
| Backend | FastAPI |
| Frontend | Streamlit |
