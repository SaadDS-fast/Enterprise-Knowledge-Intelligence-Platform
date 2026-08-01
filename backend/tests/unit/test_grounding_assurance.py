from app.core.config import settings
from app.rag.abstention import abstention_message


def test_refusal_is_neutral_and_does_not_disclose_internal_cause():
    message = abstention_message("Why is evidence unavailable?")
    assert message == (
        "The available documents do not provide enough verified evidence to answer this question."
    )
    assert "retry" not in message.lower()
    assert "score" not in message.lower()
    assert "diagnos" not in message.lower()


def test_agent_retrieval_retry_is_disabled_by_configuration():
    assert settings.agent_max_retrieval_retries == 0
