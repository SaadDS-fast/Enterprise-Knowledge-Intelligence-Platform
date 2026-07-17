def workspace_key(workspace_id: object, namespace: str, identity: str) -> str:
    return f"ekip:{workspace_id}:{namespace}:{identity}"
