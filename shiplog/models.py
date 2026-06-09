"""Domain models. All frozen + extra-forbid (immutable, strict)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class CommitContext(BaseModel):
    """One commit shaped for LLM consumption."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sha: str
    author: str
    committed_at: datetime
    subject: str
    body: str = ""
    files_changed: list[str] = Field(default_factory=list)
    diff_summary: str = ""
    diff_truncated: bool = False


class DraftPayload(BaseModel):
    """Exactly what the LLM is asked to return."""

    model_config = ConfigDict(extra="forbid")

    body: str = Field(description="The post body, ready to publish.")
    variants: list[str] = Field(
        default_factory=list,
        max_length=2,
        description="Up to two alternative phrasings.",
    )


class PostDraft(BaseModel):
    """The engine's return value: a draft plus provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    body: str
    variants: list[str] = Field(default_factory=list)
    model_used: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def char_count(self) -> int:
        return len(self.body)
