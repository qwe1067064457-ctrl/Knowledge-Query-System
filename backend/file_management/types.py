from typing import Literal, Optional, TypedDict

class FileEvent(TypedDict):
    event_id: str
    event_type: Literal['added', 'modified', 'deleted']
    file_path: str
    timestamp: float
    user_id: Optional[str]
    agent_id: Optional[str]
    content_hash: Optional[str]

class AiModificationProposal(TypedDict):
    proposal_id: str
    file_path: str
    original_content: str
    proposed_content: str
    diff: list[dict]
    status: Literal['pending', 'accepted', 'rejected', 'edited']
    timestamp: float
    agent_id: str
