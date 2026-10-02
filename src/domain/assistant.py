"""Bounded, read-only requests for explaining a single pricing scenario."""
from typing import Literal
from pydantic import Field, model_validator
from src.domain.models import Contract
from src.domain.retail_import import RetailAnalysis


class BackgroundDocument(Contract):
    title: str = Field(min_length=2, max_length=100)
    text: str = Field(min_length=10, max_length=6000)


class AssistantQuestion(Contract):
    question: str = Field(min_length=3, max_length=600)
    analysis: RetailAnalysis
    documents: list[BackgroundDocument] = Field(default_factory=list, max_length=3)
    mode: Literal["evidence", "rag"] = "evidence"

    @model_validator(mode="after")
    def versioned_context(self):
        if self.analysis.expected_version is None:
            raise ValueError("Reload the product so this question uses its current saved version")
        if sum(len(d.text) for d in self.documents) > 12000:
            raise ValueError("Keep background notes below 12,000 characters in total")
        return self


class ModelExplanation(Contract):
    """The model can explain evidence; it cannot supply or change price decisions."""
    explanation: str = Field(min_length=10, max_length=1800)
    source_ids: list[str] = Field(min_length=1, max_length=6)
