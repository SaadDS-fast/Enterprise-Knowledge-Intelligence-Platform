from collections.abc import Callable


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable] = {}

    def register(self, name: str, tool: Callable) -> None:
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        self._tools[name] = tool

    def get(self, name: str) -> Callable:
        return self._tools[name]

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))
