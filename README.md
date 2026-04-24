# AI Automation - Document Review Product

## Core capabilities
- Grammar and spelling checks
- Brand/style enforcement (using RAG)
- Verification against reference documents (using RAG)
- Checks for missing annotations, citations, & perform disclaimer checks
- Structured issue severity
- Reviewer comments on PDF
- Human review & approval flow
- Audit trail of who checked what, when, and why

## Core stack
- N8n
- Make
- Supabase
- FastAPI
- Lovable
  - Vite + TypeScript
- AWS Bedrock - Amazon Nova
- RAG
  - Amazon Bedrock Knowledge Bases
  - OpenSearch Serverless as vector store

## Screenshots

<img src="product_screenshots/home.png" width="600">

<img src="product_screenshots/dashboard.png" width="600">

<img src="product_screenshots/docreview.png" width="600">

<!-- PYTHONPATH=. uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload -->