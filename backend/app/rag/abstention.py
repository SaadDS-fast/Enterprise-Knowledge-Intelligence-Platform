def abstention_message(query: str) -> str:
    del query
    return (
        "I could not find sufficient evidence in the documents available to this "
        "workspace. Try adding a relevant document or asking a more specific question."
    )
