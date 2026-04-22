from backend.services.supabase_client import get_supabase_client


class JobService:
    def __init__(self):
        self.supabase = get_supabase_client()

    def create_review_job(
        self,
        org_id: str,
        document_id: str,
        created_by: str | None = None,
        reference_document_id: str | None = None,
        brand_rule_set_id: str | None = None,
    ):
        result = self.supabase.table("review_jobs").insert({
            "org_id": org_id,
            "document_id": document_id,
            "reference_document_id": reference_document_id,
            "brand_rule_set_id": brand_rule_set_id,
            "created_by": created_by,
            "status": "uploaded",
            "current_stage": "intake"
        }).execute()

        job = result.data[0]

        self.supabase.table("audit_events").insert({
            "entity_type": "review_job",
            "entity_id": job["id"],
            "action": "created",
            "actor_id": created_by,
            "metadata_json": {
                "source": "api",
                "stage": "intake",
                "document_id": document_id
            }
        }).execute()

        return job