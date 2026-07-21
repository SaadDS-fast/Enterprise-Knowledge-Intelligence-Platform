from enum import StrEnum


class AgentRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStateName(StrEnum):
    RECEIVE_REQUEST = "receive_request"
    AUTHORIZE = "authorize"
    CLASSIFY_INTENT = "classify_intent"
    CREATE_PLAN = "create_plan"
    SELECT_TOOL = "select_tool"
    EXECUTE_TOOL = "execute_tool"
    ASSEMBLE_EVIDENCE = "assemble_evidence"
    VERIFY_EVIDENCE = "verify_evidence"
    REPLAN = "replan"
    SYNTHESIZE = "synthesize"
    SAFETY_REVIEW = "safety_review"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentIntent(StrEnum):
    DOCUMENT_QUESTION = "document_question"
    UNSUPPORTED = "unsupported"


class AgentToolStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentErrorCode(StrEnum):
    FEATURE_DISABLED = "AGENT_FEATURE_DISABLED"
    INVALID_TRANSITION = "AGENT_INVALID_TRANSITION"
    INVALID_PLAN = "AGENT_INVALID_PLAN"
    UNKNOWN_TOOL = "AGENT_UNKNOWN_TOOL"
    TOOL_DISABLED = "AGENT_TOOL_DISABLED"
    BUDGET_EXCEEDED = "AGENT_BUDGET_EXCEEDED"
    TIMEOUT = "AGENT_TIMEOUT"
    CANCELLED = "AGENT_CANCELLED"
    UNSAFE_INPUT = "AGENT_UNSAFE_INPUT"
