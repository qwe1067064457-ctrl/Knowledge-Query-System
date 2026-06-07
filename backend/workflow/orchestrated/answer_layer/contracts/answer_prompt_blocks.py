from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AnswerPromptBlockSet:
    question_block: str = ""
    execution_summary_block: str = ""
    main_findings_block: str = ""
    evidence_anchors_block: str = ""
    cautions_block: str = ""
    constraints_block: str = ""
    extra_blocks: tuple[str, ...] = field(default_factory=tuple)

    def as_ordered_blocks(self) -> tuple[str, ...]:
        blocks = [
            self.question_block,
            self.execution_summary_block,
            self.main_findings_block,
            self.evidence_anchors_block,
            self.cautions_block,
            self.constraints_block,
            *self.extra_blocks,
        ]
        return tuple(block for block in blocks if block.strip())
