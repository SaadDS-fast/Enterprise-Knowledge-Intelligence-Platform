from app.agents.enums import AgentErrorCode


class AgentError(Exception):
    def __init__(self, code: AgentErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class AgentPolicyError(AgentError):
    pass


class AgentBudgetError(AgentError):
    pass


class AgentCancelledError(AgentError):
    def __init__(self) -> None:
        super().__init__(AgentErrorCode.CANCELLED, "Agent run was cancelled")
