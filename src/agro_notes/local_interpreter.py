"""Deterministic JSON proposal interpreter for local core exercises."""

from .domain import InterpretationProposal


class JsonProposalInterpreter:
    def interpret(self, text: str) -> InterpretationProposal:
        return InterpretationProposal.model_validate_json(text)
