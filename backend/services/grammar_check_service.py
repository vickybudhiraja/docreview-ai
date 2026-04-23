import json
import re
from backend.services.supabase_client import get_supabase_client
from backend.services.bedrock_client import BedrockClient


class GrammarCheckService:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.bedrock = BedrockClient()

    def get_chunks(self, document_id: str):
        result = (
            self.supabase
            .table("document_chunks")
            .select("*")
            .eq("document_id", document_id)
            .order("chunk_index")
            .execute()
        )
        return result.data or []

    def save_findings(self, job_id: str, chunk, issues):
        rows = []

        # TODO: add support for exact offsets and bounding boxes
        for issue in issues:
            rows.append({
                "review_job_id": job_id,
                "finding_type": "grammar",
                "severity": issue.get("severity", "low"),
                "confidence": 0.9,
                "page_number": chunk["page_number"],
                "anchor_text": issue.get("text"),
                "bbox_json": {},
                "suggested_comment": issue.get("suggestion"),
                "evidence_json": {
                    "explanation": issue.get("explanation"),
                    "issue_type": issue.get("issue_type", "grammar")
                }
            })

        if rows:
            self.supabase.table("findings").insert(rows).execute()

    def build_prompt(self, text: str) -> str:
        return f"""
You are a strict grammar reviewer.

Return ONLY valid JSON.
Do not use markdown.
Do not use code fences.
Do not write any text before or after the JSON.

If there are no grammar or spelling issues, return exactly:
{{"issues":[]}}

Return this schema exactly:
{{
  "issues": [
    {{
      "text": "exact problematic text",
      "issue_type": "grammar",
      "severity": "low",
      "suggestion": "improved text",
      "explanation": "short reason"
    }}
  ]
}}

Review this text:
{text}
"""

    def extract_json_object(self, response_text: str):
        response_text = response_text.strip()

        # 1. direct parse
        try:
            return json.loads(response_text)
        except Exception:
            pass

        # 2. remove markdown fences if present
        fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", response_text, re.DOTALL)
        if fenced:
            try:
                return json.loads(fenced.group(1))
            except Exception:
                pass

        # 3. first JSON object fallback
        obj_match = re.search(r"(\{.*\})", response_text, re.DOTALL)
        if obj_match:
            try:
                return json.loads(obj_match.group(1))
            except Exception:
                pass

        return None

    def run_on_chunk(self, text: str):
        raw_response = self.bedrock.converse_text(
            user_text=self.build_prompt(text),
            system_text="You output strict JSON only."
        )

        parsed = self.extract_json_object(raw_response)

        return {
            "raw_response": raw_response,
            "parsed": parsed,
            "issues": parsed.get("issues", []) if isinstance(parsed, dict) else []
        }

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

    def run_grammar_check(self, job_id: str, document_id: str):
        chunks = self.get_chunks(document_id)

        # optional: clear old grammar findings before rerun
        (
            self.supabase
            .table("findings")
            .delete()
            .eq("review_job_id", job_id)
            .eq("finding_type", "grammar")
            .execute()
        )

        total_issues = 0
        chunk_debug = []

        for chunk in chunks:
            run_result = self.run_on_chunk(chunk["text"])
            issues = run_result["issues"]
            total_issues += len(issues)

            self.save_findings(job_id, chunk, issues)

            chunk_debug.append({
                "page_number": chunk["page_number"],
                "chunk_index": chunk["chunk_index"],
                "issue_count": len(issues),
                "raw_response": run_result["raw_response"]
            })

        self.log_audit_event(
            entity_type="review_job",
            entity_id=job_id,
            action="grammar_checked",
            actor_id=None,
            metadata_json={
                "document_id": document_id,
                "chunk_count": len(chunks),
                "total_issues": total_issues,
                "chunk_debug": chunk_debug
            }
        )

        return {
            "chunk_count": len(chunks),
            "total_issues": total_issues,
            "chunk_debug": chunk_debug
        }