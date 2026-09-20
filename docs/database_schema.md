# Database Schema

## Extension

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Tables

### documents

| Column | Type | Description |
|:---|:---|:---|
| id | UUID | Primary key |
| filename | VARCHAR(500) | Original filename |
| file_path | VARCHAR(1000) | Storage path |
| file_hash | VARCHAR(64) | SHA-256 hash |
| page_count | INTEGER | Total pages |
| status | VARCHAR(20) | PENDING / PROCESSING / COMPLETED / FAILED |
| created_at | TIMESTAMPTZ | Creation timestamp |
| updated_at | TIMESTAMPTZ | Last update |
| metadata | JSONB | Additional metadata |

### text_chunks

| Column | Type | Description |
|:---|:---|:---|
| id | UUID | Primary key |
| document_id | UUID | FK to documents |
| page_number | INTEGER | Source page |
| section | TEXT | Section hierarchy |
| parent_section | TEXT | Parent section |
| content | TEXT | Chunk text |
| chunk_type | VARCHAR(50) | text / heading / list |
| embedding | VECTOR(768) | Text embedding |
| created_at | TIMESTAMPTZ | Creation timestamp |
| metadata | JSONB | Additional metadata |

**Index**: HNSW on `embedding` with `vector_cosine_ops`

### table_chunks

| Column | Type | Description |
|:---|:---|:---|
| id | UUID | Primary key |
| document_id | UUID | FK to documents |
| page_number | INTEGER | Source page |
| section | TEXT | Section hierarchy |
| table_content | TEXT | Markdown table |
| table_data | JSONB | Structured {headers, rows} |
| embedding | VECTOR(768) | Text embedding of table representation |
| created_at | TIMESTAMPTZ | Creation timestamp |
| metadata | JSONB | Additional metadata |

**Index**: HNSW on `embedding` with `vector_cosine_ops`

### image_chunks

| Column | Type | Description |
|:---|:---|:---|
| id | UUID | Primary key |
| document_id | UUID | FK to documents |
| page_number | INTEGER | Source page |
| section | TEXT | Section hierarchy |
| caption | TEXT | Figure caption |
| image_path | VARCHAR(1000) | File path |
| image_width | INTEGER | Width in pixels |
| image_height | INTEGER | Height in pixels |
| image_embedding | VECTOR(512) | CLIP embedding |
| created_at | TIMESTAMPTZ | Creation timestamp |
| metadata | JSONB | Additional metadata |

**Index**: HNSW on `image_embedding` with `vector_cosine_ops`

## Why Separate Tables

Text (768d) and image (512d) embeddings use different models and dimensions. Storing them in separate tables with separate vector columns ensures:
1. No dimension mismatch errors
2. Independent HNSW indexes for each modality
3. Clean retrieval queries per content type
4. Results are fused at the ranking level (RRF), not the vector level
