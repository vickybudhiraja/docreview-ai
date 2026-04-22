import os
from dotenv import load_dotenv
from fastapi import FastAPI

from backend.services.supabase_client import get_supabase_client
from backend.services.bedrock_client import BedrockClient
from pydantic import BaseModel
from backend.services.supabase_client import get_supabase_client
from fastapi import UploadFile, File, Form
from backend.services.document_service import DocumentService
from backend.services.job_service import JobService

load_dotenv()

app = FastAPI(title="docreview-ai backend")

class CreateJobRequest(BaseModel):
    org_id: str
    document_id: str
    reference_document_id: str | None = None
    brand_rule_set_id: str | None = None
    created_by: str | None = None

# @app.get("/health")
# def health():
#     return {
#         "ok": True,
#         "service": "docreview-ai-backend"
#     }


# @app.get("/supabase/test")
# def supabase_test():
#     supabase = get_supabase_client()

#     result = (
#         supabase
#         .table("organizations")
#         .select("id, name, created_at")
#         .limit(5)
#         .execute()
#     )

#     return {
#         "ok": True,
#         "count": len(result.data),
#         "organizations": result.data
#     }


# @app.get("/bedrock/test")
# def bedrock_test():
#     bedrock = BedrockClient()

#     text = bedrock.converse_text(
#         user_text="Reply with exactly BEDROCK_OK",
#         system_text="You are a precise assistant."
#     )

#     return {
#         "ok": True,
#         "model_id": os.getenv("BEDROCK_MODEL_ID"),
#         "response": text
#     }

@app.post("/jobs/create")
def create_job(payload: CreateJobRequest):
    supabase = get_supabase_client()

    result = supabase.table("review_jobs").insert({
        "org_id": payload.org_id,
        "document_id": payload.document_id,
        "reference_document_id": payload.reference_document_id,
        "brand_rule_set_id": payload.brand_rule_set_id,
        "created_by": payload.created_by,
        "status": "uploaded",
        "current_stage": "intake"
    }).execute()

    job = result.data[0]

    supabase.table("audit_events").insert({
        "entity_type": "review_job",
        "entity_id": job["id"],
        "action": "created",
        "actor_id": payload.created_by,
        "metadata_json": {
            "source": "api",
            "stage": "intake"
        }
    }).execute()

    return {
        "ok": True,
        "job": job
    }

# @app.post("/documents/upload")
# async def upload_document(
#     org_id: str = Form(...),
#     created_by: str = Form(...),
#     file: UploadFile = File(...)
# ):
#     file_bytes = await file.read()

#     document_service = DocumentService()
#     document = document_service.upload_document(
#         org_id=org_id,
#         created_by=created_by,
#         file_name=file.filename,
#         file_bytes=file_bytes,
#         source_type="upload"
#     )

#     return {
#         "ok": True,
#         "document": document
#     }
@app.post("/intake/upload-and-create-job")
async def upload_and_create_job(
    org_id: str = Form(...),
    created_by: str = Form(...),
    file: UploadFile = File(...),
    reference_document_id: str | None = Form(None),
    brand_rule_set_id: str | None = Form(None)
):
    file_bytes = await file.read()

    document_service = DocumentService()
    job_service = JobService()

    document = document_service.upload_document(
        org_id=org_id,
        created_by=created_by,
        file_name=file.filename,
        file_bytes=file_bytes,
        source_type="upload"
    )

    job = job_service.create_review_job(
        org_id=org_id,
        document_id=document["id"],
        created_by=created_by,
        reference_document_id=reference_document_id,
        brand_rule_set_id=brand_rule_set_id
    )

    return {
        "ok": True,
        "document": document,
        "job": job
    }