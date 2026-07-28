export type User = {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
  workspace_id: string;
};

export type DocumentItem = {
  id: string;
  workspace_id: string;
  title: string;
  status: string;
  description?: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
  filename?: string | null;
  extraction_quality?: string | null;
  page_count?: number | null;
  chunk_count: number;
  pipeline_version: Record<string, string | null>;
  latest_pipeline_version: Record<string, string>;
  reprocessing_recommended: boolean;
  processing_progress?: string | null;
  error_category?: string | null;
};

export type Job = {
  id: string;
  workspace_id: string;
  document_version_id: string;
  status: string;
  stage: string;
  error_message?: string | null;
  result_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type Evidence = {
  chunk_id: string;
  document_id: string;
  document_title: string;
  content: string;
  score: number;
  metadata: Record<string, unknown>;
};

export type RetrievalDiagnosis = {
  status: string;
  initial_evidence_sufficient: boolean;
  retry_performed: boolean;
  retry_strategy: string[];
  initial_support_score: number;
  final_support_score: number;
  evidence_count: number;
  reason_code: string;
};

export type SearchResult = {
  answer: string;
  evidence: Evidence[];
  sufficient_evidence: boolean;
  abstained: boolean;
  request_id?: string | null;
  retrieval_diagnosis?: RetrievalDiagnosis;
  outcome?: string;
  answer_value?: string | null;
  support_status?: string;
  confidence_category?: string;
  citations?: AgentCitation[];
  conflicts?: AgentConflict[];
  abstention_reason?: string | null;
  topic_items?: TopicItem[];
  active_document_scope?: SearchScopeItem[];
};

export type TopicItem = {
  label: string;
  confidence: string;
  support_status: string;
  chunk_id: string;
  document_id: string;
  document_title: string;
  excerpt: string;
  section?: string | null;
};

export type SearchScopeItem = {
  document_id: string;
  title: string;
};

export type AgentOutcome =
  | "ANSWER_SUPPORTED"
  | "ANSWER_PARTIALLY_SUPPORTED"
  | "CONFLICTING_EVIDENCE"
  | "INSUFFICIENT_EVIDENCE"
  | "KNOWLEDGE_ABSENT"
  | "CLARIFICATION_REQUIRED"
  | "SAFETY_BLOCKED"
  | "FAILED"
  | string;

export type ExternalSource = {
  source_id: string;
  provider: string;
  title: string;
  canonical_url: string;
  excerpt: string;
  source_type: string;
  retrieval_timestamp: string;
  trust_category: string;
  rank: number;
  publication_date?: string | null;
  authors: string[];
};

export type AgentCitation = {
  citation_label?: string;
  external_source_label?: string;
  document_title?: string;
  document_version_id?: string;
  page?: number;
  section?: string;
  chunk_id?: string;
  excerpt?: string;
  topic?: string;
  provider?: string;
  title?: string;
  canonical_url?: string;
  retrieval_timestamp?: string;
  source_type?: string;
};

export type AgentConflict = {
  claim?: string;
  summary?: string;
  field?: string;
  values?: string[];
  citations?: string[];
};

export type AgentClaim = {
  claim_text: string;
  verification_status: string;
  support_score?: number;
  citations?: string[];
};

export type AgentQueryRequest = {
  query: string;
  top_k?: number | null;
  document_ids?: string[] | null;
  allow_external_sources: boolean;
};

export type AgentQueryResponse = {
  run_id: string;
  status: string;
  current_state: string;
  answer?: string | null;
  abstained: boolean;
  citations: AgentCitation[];
  evidence: Evidence[];
  internal_evidence: Evidence[];
  external_evidence: ExternalSource[];
  external_sources_used: boolean;
  providers_used: string[];
  external_access_allowed: boolean;
  external_access_performed: boolean;
  tools_used: string[];
  safe_step_summaries: string[];
  safe_plan_summary?: string | null;
  total_duration_ms?: number | null;
  fallback_used: boolean;
  request_id?: string | null;
  retrieval_diagnosis: Partial<RetrievalDiagnosis>;
  outcome: AgentOutcome;
  claims: AgentClaim[];
  conflicts: AgentConflict[];
  unsupported_claims_removed: string[];
  confidence_category: string;
  unified_evidence: Record<string, unknown>[];
};

export type AgentRunStep = {
  id: string;
  run_id: string;
  step_number: number;
  state: string;
  summary: string;
  status: string;
  error_code?: string | null;
  duration_ms?: number | null;
  created_at: string;
  updated_at: string;
};

export type AgentToolCall = {
  id: string;
  run_id: string;
  step_id?: string | null;
  tool_name: string;
  status: string;
  summary?: string | null;
  error_code?: string | null;
  duration_ms?: number | null;
  created_at: string;
  updated_at: string;
};

export type AgentRunDetail = {
  id: string;
  workspace_id: string;
  user_id: string;
  request_id?: string | null;
  status: string;
  current_state: string;
  input_query: string;
  safe_plan_summary?: string | null;
  result_json: Record<string, unknown>;
  error_code?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  steps: AgentRunStep[];
  tool_calls: AgentToolCall[];
};

export type ResearchFormat = "markdown" | "pdf" | "docx";

export type ResearchCreateRequest = {
  question: string;
  document_ids?: string[] | null;
  allow_external_sources: boolean;
  requested_formats: ResearchFormat[];
  max_depth_preset?: string | null;
  idempotency_key?: string | null;
};

export type ResearchCreateResponse = {
  job_id: string;
  status: string;
  current_state: string;
  idempotent_replay: boolean;
};

export type ResearchArtifact = {
  artifact_id?: string;
  id?: string;
  format: ResearchFormat | string;
  filename: string;
  mime_type: string;
  checksum_sha256: string;
  size_bytes: number;
  signed_url_expires?: number;
  download_url?: string;
  created_at?: string;
};

export type ResearchJob = {
  id: string;
  workspace_id?: string;
  user_id?: string;
  agent_run_id?: string | null;
  request_id?: string | null;
  question: string;
  status: string;
  current_state?: string;
  stage?: string;
  progress_percent?: number;
  external_sources_allowed?: boolean;
  requested_formats?: string[];
  source_count?: number;
  verified_citation_count?: number;
  artifact_refs?: ResearchArtifact[];
  report_markdown?: string | null;
  result_json: Record<string, unknown>;
  error_code?: string | null;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  cancelled_at?: string | null;
  updated_at: string;
};

export type EvaluationRun = {
  id: string;
  name: string;
  status: string;
  metrics_json: Record<string, number>;
  config_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};
