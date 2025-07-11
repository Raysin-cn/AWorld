from abc import abstractmethod, ABC
from pydantic import BaseModel, ConfigDict, Field
from aworld.core.memory import MemoryItem
from typing import Any, Dict, List, Optional, Literal, Union

from aworld.models.model_response import ToolCall

class MessageMetadata(BaseModel):
    """
    Metadata for memory messages, including user, session, task, and agent information.
    Args:
        user_id (str): The ID of the user.
        session_id (str): The ID of the session.
        task_id (str): The ID of the task.
        agent_id (str): The ID of the agent.
    """
    agent_id: str = Field(description="The ID of the agent")
    agent_name: str = Field(description="The name of the agent")
    session_id: Optional[str] = Field(default=None,description="The ID of the session")
    task_id: Optional[str] = Field(default=None,description="The ID of the task")
    user_id: Optional[str] = Field(default=None, description="The ID of the user")
    is_use_tool_prompt: Optional[bool] = Field(default=False, description="Whether the agent uses tool prompt")

    model_config = ConfigDict(extra="allow")

    @property
    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

class AgentExperienceItem(BaseModel):
    skill: str = Field(description="The skill demonstrated in the experience")
    actions: List[str] = Field(description="The actions taken by the agent")

class LongTermEmbedding(ABC):
    """
    Abstract class for long-term embedding.
    """

    @abstractmethod
    def get_embedding_text(self):
        pass

class AgentExperience(MemoryItem, LongTermEmbedding):
    """
    Represents an agent's experience, including skills and actions.
    All custom attributes are stored in content and metadata.
    Args:
        agent_id (str): The ID of the agent.
        skill (str): The skill demonstrated in the experience.
        actions (List[str]): The actions taken by the agent.
        metadata (Optional[Dict[str, Any]]): Additional metadata.
    """
    def __init__(self, agent_id: str, skill: str, actions: List[str], metadata: Optional[Dict[str, Any]] = None) -> None:
        meta = metadata.copy() if metadata else {}
        meta['agent_id'] = agent_id
        agent_experience = AgentExperienceItem(skill=skill, actions=actions)
        super().__init__(content=agent_experience, metadata=meta, memory_type="agent_experience")

    @property
    def agent_id(self) -> str:
        return self.metadata['agent_id']

    @property
    def skill(self) -> str:
        return self.content.skill

    @property
    def actions(self) -> List[str]:
        return self.content.actions

    def get_embedding_text(self):
        return f"agent_id:{self.agent_id} skill:{self.skill} actions:{self.actions}"

class UserProfileItem(BaseModel):
    key: str = Field(description="The key of the profile")
    value: Any = Field(description="The value of the profile")

class UserProfile(MemoryItem, LongTermEmbedding):
    """
    Represents a user profile key-value pair.
    All custom attributes are stored in content and metadata.
    Args:
        user_id (str): The ID of the user.
        key (str): The profile key.
        value (Any): The profile value.
        metadata (Optional[Dict[str, Any]]): Additional metadata.
    """
    def __init__(self, user_id: str, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        meta = metadata.copy() if metadata else {}
        meta['user_id'] = user_id
        user_profile = UserProfileItem(key=key, value=value)
        super().__init__(content=user_profile, metadata=meta, memory_type="user_profile")

    @property
    def user_id(self) -> str:
        return self.metadata['user_id']

    @property
    def key(self) -> str:
        return self.content.key

    @property
    def value(self) -> Any:
        return self.content.value

    def get_embedding_text(self):
        return f"user_id:{self.user_id} key:{self.key} value:{self.value}"


class MemoryMessage(MemoryItem):
    """
    Represents a memory message with role, user, session, task, and agent information.
    Args:
        role (str): The role of the message sender.
        metadata (MessageMetadata): Metadata object containing user, session, task, and agent IDs.
        content (Optional[Any]): Content of the message.
    """
    def __init__(self, role: str, metadata: MessageMetadata, content: Optional[Any] = None, memory_type="message") -> None:
        meta = metadata.to_dict
        meta['role'] = role
        super().__init__(content=content, metadata=meta, memory_type=memory_type)

    @property
    def role(self) -> str:
        return self.metadata['role']

    @property
    def user_id(self) -> str:
        return self.metadata['user_id']

    @property
    def session_id(self) -> str:
        return self.metadata['session_id']

    @property
    def task_id(self) -> str:
        return self.metadata['task_id']

    @property
    def agent_id(self) -> str:
        return self.metadata['agent_id']
    
    @abstractmethod
    def to_openai_message(self) -> dict:
        pass

class MemorySystemMessage(MemoryMessage):
    """
    Represents a system message with role and content.
    Args:
        metadata (MessageMetadata): Metadata object containing user, session, task, and agent IDs.
        content (str): The content of the message.
    """
    def __init__(self, content: str, metadata: MessageMetadata) -> None:
        super().__init__(role="system", metadata=metadata, content=content, memory_type="init")

    def to_openai_message(self) -> dict:
        return {
            "role": self.role,
            "content": self.content
        }

class MemoryHumanMessage(MemoryMessage):
    """
    Represents a human message with role and content.
    Args:
        metadata (MessageMetadata): Metadata object containing user, session, task, and agent IDs.
        content (str): The content of the message.
    """
    def __init__(self, metadata: MessageMetadata, content: str) -> None:
        super().__init__(role="user", metadata=metadata, content=content)
    
    def to_openai_message(self) -> dict:
        return {
            "role": self.role,
            "content": self.content
        }

class MemoryAIMessage(MemoryMessage):
    """
    Represents an AI message with role and content.
    Args:
        metadata (MessageMetadata): Metadata object containing user, session, task, and agent IDs.
        content (str): The content of the message.
    """
    def __init__(self, content: str, tool_calls: Optional[List[ToolCall]] = [], metadata: MessageMetadata = None) -> None:
        meta = metadata.to_dict
        if tool_calls:
            meta['tool_calls'] = [tool_call.to_dict() for tool_call in tool_calls]
        super().__init__(role="assistant", metadata=MessageMetadata(**meta), content=content)

    @property
    def tool_calls(self) -> List[ToolCall]:
        if "tool_calls" not in self.metadata or not self.metadata['tool_calls']:
            return []
        return [ToolCall(**tool_call) for tool_call in self.metadata['tool_calls']]
    
    def to_openai_message(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "tool_calls": [tool_call.to_dict() for tool_call in self.tool_calls]
        }

class MemoryToolMessage(MemoryMessage):
    """
    Represents a tool message with role, content, tool_call_id, and status.
    Args:
        metadata (MessageMetadata): Metadata object containing user, session, task, and agent IDs.
        tool_call_id (str): The ID of the tool call.
        status (Literal["success", "error"]): The status of the tool call.
        content (str): The content of the message.
    """
    def __init__(self, tool_call_id: str, content: Any, status: Literal["success", "error"] = "success", metadata: MessageMetadata = None) -> None:
        metadata.tool_call_id = tool_call_id
        metadata.status = status
        super().__init__(role="tool", metadata=metadata, content=content)

    @property
    def tool_call_id(self) -> str:
        return self.metadata['tool_call_id']

    @property
    def status(self) -> str:
        return self.metadata['status']

    
    def to_openai_message(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "tool_call_id": self.tool_call_id,
        }


class LongTermExtractParams(BaseModel):
    session_id: str = Field(description="The ID of the session")
    task_id: Optional[str] = Field(description="The ID of the task")
    memories: List[MemoryItem] = Field(default_factory=list, description="The list of memories to process")

    application_id: Optional[str] = Field(default=None, description="The ID of the application")
    extract_type: Literal["user_profile", "agent_experience"] = Field(description="The type of long-term extract")

    def to_openai_messages(self) -> List[dict]:
        return [memory.to_openai_message() for memory in self.memories]

class UserProfileExtractParams(LongTermExtractParams):
    user_id: Optional[str] = Field(description="The ID of the user")

    def __init__(self, user_id: str, session_id: str, task_id: str, memories: List[MemoryItem] = None, application_id: str = None) -> None:
        kwargs = {
            "user_id": user_id,
            "session_id": session_id,
            "task_id": task_id,
            "memories": memories or [],
            "application_id": application_id,
            "extract_type": "user_profile"
        }
        super().__init__(**kwargs)

    model_config = ConfigDict(extra="allow")

class AgentExperienceExtractParams(LongTermExtractParams):
    agent_id: str = Field(default=None, description="The ID of the agent")

    def __init__(self, agent_id: str, session_id: str, task_id: str, memories: List[MemoryItem] = None,
                 application_id: str = None) -> None:
        super().__init__(session_id=session_id,
                         task_id=task_id,
                         memories=memories,
                         application_id=application_id,
                         extract_type="agent_experience")
        self.agent_id = agent_id

    model_config = ConfigDict(extra="allow")

