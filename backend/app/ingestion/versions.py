from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PipelineVersions:
    extraction: str = "3.0"
    normalization: str = "3.0"
    chunking: str = "3.0"
    indexing: str = "1.0"

    def as_dict(self) -> dict[str, str]:
        return {
            "extraction_version": self.extraction,
            "normalization_version": self.normalization,
            "chunking_version": self.chunking,
            "indexing_version": self.indexing,
        }


LATEST_PIPELINE = PipelineVersions()


def is_current(metadata: dict | None) -> bool:
    values = metadata or {}
    return all(values.get(key) == value for key, value in LATEST_PIPELINE.as_dict().items())
