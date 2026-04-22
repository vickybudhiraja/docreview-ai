import os
import uuid
import mimetypes
from backend.services.supabase_client import get_supabase_client


class DocumentService:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.bucket_name = "original-documents"

    def upload_document(
        self,
        org_id: str,
        created_by: str,
        file_name: str,
        file_bytes: bytes,
        source_type: str = "upload"
    ):
        safe_file_name = file_name.replace(" ", "_")
        object_path = f"{org_id}/{uuid.uuid4()}_{safe_file_name}"

        content_type, _ = mimetypes.guess_type(file_name)
        if not content_type:
            content_type = "application/octet-stream"

        self.supabase.storage.from_(self.bucket_name).upload(
            path=object_path,
            file=file_bytes,
            file_options={
                "content-type": content_type
            }
        )

        result = self.supabase.table("documents").insert({
            "org_id": org_id,
            "file_name": file_name,
            "file_path": object_path,
            "mime_type": content_type,
            "source_type": source_type,
            "created_by": created_by
        }).execute()

        document = result.data[0]

        self.supabase.table("audit_events").insert({
            "entity_type": "document",
            "entity_id": document["id"],
            "action": "uploaded",
            "actor_id": created_by,
            "metadata_json": {
                "bucket": self.bucket_name,
                "file_path": object_path,
                "file_name": file_name
            }
        }).execute()

        return document