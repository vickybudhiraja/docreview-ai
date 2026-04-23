from collections import Counter
from backend.services.supabase_client import get_supabase_client


class ReviewReadService:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.bucket_name = "original-documents"

    def list_review_jobs(self, limit: int = 50):
        jobs_result = (
            self.supabase
            .table("review_jobs")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        jobs = jobs_result.data or []
        if not jobs:
            return []

        document_ids = list({job["document_id"] for job in jobs if job.get("document_id")})
        created_by_ids = list({job["created_by"] for job in jobs if job.get("created_by")})
        job_ids = [job["id"] for job in jobs]

        documents_map = {}
        if document_ids:
            docs_result = (
                self.supabase
                .table("documents")
                .select("*")
                .in_("id", document_ids)
                .execute()
            )
            documents_map = {doc["id"]: doc for doc in (docs_result.data or [])}

        users_map = {}
        if created_by_ids:
            users_result = (
                self.supabase
                .table("users")
                .select("id, email, role")
                .in_("id", created_by_ids)
                .execute()
            )
            users_map = {user["id"]: user for user in (users_result.data or [])}

        findings_counts_map = {}
        findings_types_map = {}
        if job_ids:
            findings_result = (
                self.supabase
                .table("findings")
                .select("review_job_id, finding_type")
                .in_("review_job_id", job_ids)
                .execute()
            )

            findings_counts_map = Counter()
            findings_types_map = {}

            for row in (findings_result.data or []):
                rid = row["review_job_id"]
                findings_counts_map[rid] += 1
                findings_types_map.setdefault(rid, Counter())
                findings_types_map[rid][row["finding_type"]] += 1

        items = []
        for job in jobs:
            document = documents_map.get(job["document_id"])
            created_by = users_map.get(job.get("created_by"))

            items.append({
                "job": job,
                "document": document,
                "created_by_user": created_by,
                "findings_count": findings_counts_map.get(job["id"], 0),
                "findings_by_type": dict(findings_types_map.get(job["id"], {}))
            })

        return items

    def get_dashboard_summary(self):
        jobs_result = (
            self.supabase
            .table("review_jobs")
            .select("id, status, created_at")
            .execute()
        )
        jobs = jobs_result.data or []

        findings_result = (
            self.supabase
            .table("findings")
            .select("id, finding_type")
            .execute()
        )
        findings = findings_result.data or []

        status_counter = Counter(job["status"] for job in jobs)
        finding_type_counter = Counter(f["finding_type"] for f in findings)

        return {
            "total_jobs": len(jobs),
            "in_progress": status_counter.get("extracting", 0) + status_counter.get("analyzing", 0) + status_counter.get("annotating", 0) + status_counter.get("uploaded", 0) + status_counter.get("queued", 0),
            "review_ready": status_counter.get("review_ready", 0),
            "failed": status_counter.get("failed", 0),
            "findings_summary": {
                "grammar": finding_type_counter.get("grammar", 0),
                "style": finding_type_counter.get("style", 0),
                "claims": finding_type_counter.get("claims", 0),
                "missing_annotations": finding_type_counter.get("missing_annotations", 0)
            },
            "jobs_by_status": dict(status_counter)
        }

    def get_review_job_detail(self, job_id: str):
        job_result = (
            self.supabase
            .table("review_jobs")
            .select("*")
            .eq("id", job_id)
            .limit(1)
            .execute()
        )

        if not job_result.data:
            raise ValueError("review job not found")

        job = job_result.data[0]

        document_result = (
            self.supabase
            .table("documents")
            .select("*")
            .eq("id", job["document_id"])
            .limit(1)
            .execute()
        )

        if not document_result.data:
            raise ValueError("document not found")

        document = document_result.data[0]

        findings_result = (
            self.supabase
            .table("findings")
            .select("finding_type, severity")
            .eq("review_job_id", job_id)
            .execute()
        )

        findings = findings_result.data or []
        type_counter = Counter(f["finding_type"] for f in findings)
        severity_counter = Counter(f["severity"] for f in findings)

        return {
            "job": job,
            "document": document,
            "finding_counts": {
                "total": len(findings),
                "by_type": dict(type_counter),
                "by_severity": dict(severity_counter)
            }
        }

    def get_job_findings(self, job_id: str):
        result = (
            self.supabase
            .table("findings")
            .select("*")
            .eq("review_job_id", job_id)
            .order("page_number")
            .order("created_at")
            .execute()
        )

        return result.data or []

    def create_signed_document_url(self, document_id: str, expires_in: int = 3600):
        doc_result = (
            self.supabase
            .table("documents")
            .select("*")
            .eq("id", document_id)
            .limit(1)
            .execute()
        )

        if not doc_result.data:
            raise ValueError("document not found")

        document = doc_result.data[0]
        file_path = document["file_path"]

        signed = (
            self.supabase
            .storage
            .from_(self.bucket_name)
            .create_signed_url(file_path, expires_in)
        )

        # supabase-py may return dict with signedURL or signedUrl depending on version
        signed_url = signed.get("signedURL") or signed.get("signedUrl")

        return {
            "document": document,
            "url": signed_url,
            "expires_in": expires_in
        }