export type User = { id: string; email: string; full_name: string; is_active: boolean; is_superuser: boolean; created_at: string };
export type AuthResponse = { access_token: string; token_type: string; expires_in: number; user: User; workspace_id: string };
export type DocumentItem = { id: string; workspace_id: string; title: string; status: string; description?: string | null; created_by: string; created_at: string; updated_at: string };
export type Job = { id: string; workspace_id: string; document_version_id: string; status: string; stage: string; error_message?: string | null; result_json: Record<string, unknown>; created_at: string; updated_at: string };
export type Evidence = { chunk_id: string; document_id: string; document_title: string; content: string; score: number; metadata: Record<string, unknown> };
export type SearchResult = { answer: string; evidence: Evidence[]; sufficient_evidence: boolean; abstained: boolean; request_id?: string | null };
export type ResearchJob = { id: string; question: string; status: string; report_markdown?: string | null; result_json: Record<string, unknown>; error_message?: string | null; created_at: string; updated_at: string };
export type EvaluationRun = { id: string; name: string; status: string; metrics_json: Record<string, number>; config_json: Record<string, unknown>; created_at: string; updated_at: string };
