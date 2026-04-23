import io
from typing import List, Dict
from pypdf import PdfReader

from backend.services.supabase_client import get_supabase_client


class ExtractionService:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.bucket_name = "original-documents"

    def get_job_with_document(self, job_id: str) -> Dict:
        job_result = (
            self.supabase
            .table("review_jobs")
            .select("*")
            .eq("id", job_id)
            .limit(1)
            .execute()
        )

        if not job_result.data:
            raise ValueError(f"review job not found: {job_id}")

        job = job_result.data[0]

        doc_result = (
            self.supabase
            .table("documents")
            .select("*")
            .eq("id", job["document_id"])
            .limit(1)
            .execute()
        )

        if not doc_result.data:
            raise ValueError(f"document not found for job: {job_id}")

        document = doc_result.data[0]

        return {
            "job": job,
            "document": document
        }

    def update_job_stage(self, job_id: str, status: str, current_stage: str, error_message: str | None = None):
        payload = {
            "status": status,
            "current_stage": current_stage,
            "error_message": error_message
        }

        (
            self.supabase
            .table("review_jobs")
            .update(payload)
            .eq("id", job_id)
            .execute()
        )

    def download_document_bytes(self, file_path: str) -> bytes:
        file_bytes = (
            self.supabase
            .storage
            .from_(self.bucket_name)
            .download(file_path)
        )

        return file_bytes

    def extract_pages(self, pdf_bytes: bytes) -> List[Dict]:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        chunks = []

        for page_index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            cleaned_text = text.strip()

            ## saving the entire page as 1 chunk here
            chunks.append({
                "page_number": page_index + 1,
                "chunk_index": page_index,
                "text": cleaned_text,
                "metadata_json": {
                    "source": "pypdf",
                    "extraction_level": "page"
                }
            })

        return chunks

    def clear_existing_chunks(self, document_id: str):
        (
            self.supabase
            .table("document_chunks")
            .delete()
            .eq("document_id", document_id)
            .execute()
        )

    def save_chunks(self, document_id: str, chunks: List[Dict]):
        if not chunks:
            return []

        rows = []
        for chunk in chunks:
            rows.append({
                "document_id": document_id,
                "page_number": chunk["page_number"],
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"],
                "metadata_json": chunk["metadata_json"]
            })

        result = (
            self.supabase
            .table("document_chunks")
            .insert(rows)
            .execute()
        )

        return result.data

    def log_audit_event(self, entity_type: str, entity_id: str, action: str, actor_id: str | None, metadata_json: dict):
        (
            self.supabase
            .table("audit_events")
            .insert({
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action,
                "actor_id": actor_id,
                "metadata_json": metadata_json
            })
            .execute()
        )

    def extract_document_for_job(self, job_id: str) -> Dict:
        context = self.get_job_with_document(job_id)
        job = context["job"]
        document = context["document"]

        try:
            self.update_job_stage(
                job_id=job_id,
                status="extracting",
                current_stage="extract"
            )

            pdf_bytes = self.download_document_bytes(document["file_path"])
            chunks = self.extract_pages(pdf_bytes)

            self.clear_existing_chunks(document["id"])
            saved_chunks = self.save_chunks(document["id"], chunks)

            self.update_job_stage(
                job_id=job_id,
                status="analyzing",
                current_stage="grammar_check"
            )

            self.log_audit_event(
                entity_type="review_job",
                entity_id=job_id,
                action="extracted",
                actor_id=job.get("created_by"),
                metadata_json={
                    "document_id": document["id"],
                    "chunk_count": len(saved_chunks)
                }
            )

            return {
                "job_id": job_id,
                "document_id": document["id"],
                "chunk_count": len(saved_chunks),
                "status": "analyzing",
                "current_stage": "grammar_check"
            }

        except Exception as e:
            self.update_job_stage(
                job_id=job_id,
                status="failed",
                current_stage="extract",
                error_message=str(e)
            )

            self.log_audit_event(
                entity_type="review_job",
                entity_id=job_id,
                action="extract_failed",
                actor_id=job.get("created_by"),
                metadata_json={
                    "document_id": document["id"],
                    "error": str(e)
                }
            )

            raise