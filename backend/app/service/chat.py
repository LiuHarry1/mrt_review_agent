"""Chat service for conversational MRT review with state management."""
from __future__ import annotations

import uuid
from typing import Dict, Generator, List, Optional

from ..config import get_config
from ..llm import LLMClient
from ..models import (
    ChatRequest,
    ConversationState,
)


class MRTEntry:
    """Represents a single MRT entry."""

    def __init__(self, content: str, name: Optional[str] = None):
        self.id = uuid.uuid4().hex[:8]
        self.name = name or f"MRT-{self.id}"
        self.content = content


class SessionStore:
    """In-memory session storage. Only stores MRT, requirement, and state (not conversation history)."""

    def __init__(self):
        self._sessions: Dict[str, Dict] = {}

    def create(self) -> str:
        """Create a new session."""
        session_id = uuid.uuid4().hex
        self._sessions[session_id] = {
            "state": ConversationState.INITIAL,
            "mrts": {},
            "current_mrt_id": None,
            "software_requirement": None,
        }
        return session_id

    def get(self, session_id: str) -> Optional[Dict]:
        """Get session by ID."""
        return self._sessions.get(session_id)

    def has_mrt(self, session_id: str) -> bool:
        """Check if session has MRT content."""
        mrt = self.get_current_mrt(session_id)
        return mrt is not None and bool(mrt.content.strip())

    def has_requirement(self, session_id: str) -> bool:
        """Check if session has software requirement."""
        session = self.get(session_id)
        if not session:
            return False
        req = session.get("software_requirement")
        return req is not None and bool(req.strip())

    def can_start_review(self, session_id: str) -> bool:
        """Check if can start review (at least needs MRT)."""
        return self.has_mrt(session_id)

    def add_mrt(self, session_id: str, content: str, name: Optional[str] = None) -> str:
        """Add MRT content to session."""
        if session_id not in self._sessions:
            raise KeyError("Session not found")
        mrt_entry = MRTEntry(content, name)
        self._sessions[session_id]["mrts"][mrt_entry.id] = mrt_entry
        self._sessions[session_id]["current_mrt_id"] = mrt_entry.id
        return mrt_entry.id

    def clear_mrt(self, session_id: str) -> None:
        """Clear current MRT content."""
        if session_id not in self._sessions:
            raise KeyError("Session not found")
        self._sessions[session_id]["mrts"] = {}
        self._sessions[session_id]["current_mrt_id"] = None

    def get_current_mrt(self, session_id: str) -> Optional[MRTEntry]:
        """Get current active MRT for session."""
        if session_id not in self._sessions:
            return None
        session = self._sessions[session_id]
        current_id = session.get("current_mrt_id")
        if not current_id:
            return None
        return session["mrts"].get(current_id)

    def set_state(self, session_id: str, state: ConversationState) -> None:
        """Set session state."""
        if session_id not in self._sessions:
            raise KeyError("Session not found")
        self._sessions[session_id]["state"] = state


class ChatService:
    """Service for conversational MRT review with state-based guidance."""

    def __init__(self, llm_client: Optional[LLMClient] = None, session_store: Optional[SessionStore] = None):
        """Initialize chat service."""
        self.llm_client = llm_client or LLMClient()
        self.sessions = session_store or SessionStore()

    def _determine_next_state(
        self, session: Dict, has_mrt: bool, has_req: bool, detected_new_mrt: bool = False
    ) -> ConversationState:
        """Determine next state based on current state and data."""
        current_state = session["state"]

        # Detect new MRT - clear old content and reset state
        if detected_new_mrt and current_state != ConversationState.INITIAL:
            # New MRT detected, start fresh
            return ConversationState.AWAITING_REQUIREMENT if not has_req else ConversationState.REVIEWING

        if current_state == ConversationState.INITIAL:
            return ConversationState.AWAITING_MRT if not has_mrt else ConversationState.REVIEWING

        if current_state == ConversationState.AWAITING_MRT:
            if has_mrt:
                # MRT provided, ask about requirement
                return ConversationState.AWAITING_REQUIREMENT
            return ConversationState.AWAITING_MRT

        if current_state == ConversationState.AWAITING_REQUIREMENT:
            if has_mrt:
                # Can start review if MRT is available
                return ConversationState.REVIEWING
            return ConversationState.AWAITING_MRT

        if current_state == ConversationState.REVIEWING:
            # Stay in reviewing until explicitly changed
            return ConversationState.REVIEWING

        if current_state == ConversationState.COMPLETED:
            # If new data comes, restart
            if has_mrt:
                return ConversationState.REVIEWING
            return ConversationState.AWAITING_MRT

        return current_state

    def _get_welcome_message(self) -> str:
        """Get welcome message for INITIAL state."""
        return """您好！我是专业的MRT（手动回归测试）审查助手。

我可以帮助您：
1. 审查MRT测试用例是否符合checklist要求
2. 对照软件需求文档，确保测试用例的完整覆盖
3. 提供具体的改进建议

请上传您的MRT文件（支持PDF、Word、TXT格式）或直接粘贴测试用例内容。"""

    def _get_guidance_message(self, state: ConversationState) -> Optional[str]:
        """Get guidance message based on current state."""
        if state == ConversationState.AWAITING_MRT:
            return "请上传MRT文件（PDF、Word、TXT）或直接粘贴测试用例内容。"
        elif state == ConversationState.AWAITING_REQUIREMENT:
            return "MRT内容已收到。是否需要提供软件需求文档？(可选，如果不需要可以回复'跳过'或'开始review')"
        elif state == ConversationState.COMPLETED:
            return "Review已完成。如需review新的MRT内容，请上传新文件或粘贴内容。"
        return None

    def _build_system_prompt(self, state: ConversationState, software_requirement: Optional[str] = None) -> str:
        """Build system prompt based on state."""
        config = get_config()
        checklist = config.default_checklist
        checklist_string = "\n".join([f"- {item.id}: {item.description}" for item in checklist])

        has_requirement = software_requirement is not None and software_requirement.strip() != ""
        requirement_section = ""
        if has_requirement:
            requirement_section = f"""

当前有软件需求文档，请确保：
1. 每个软件需求都被一个或多个测试用例覆盖
2. 测试用例覆盖软件需求中描述的所有场景、条件、数据等
3. 测试用例编号、标题、前置条件、测试步骤和验证点（预期结果）都有清晰描述
"""

        base_prompt = f"""你是一个专业的软件测试审查助手。你的任务是根据提供的checklist来review用户的MRT（手动回归测试）内容。

当前的checklist包括：
{checklist_string}{requirement_section}"""

        if state == ConversationState.INITIAL or state == ConversationState.AWAITING_MRT:
            return base_prompt + """

你的职责：
1. 友好地引导用户提供MRT内容
2. 说明可以上传文件或直接粘贴内容
3. 耐心等待用户提供测试用例

请以友好、专业的方式与用户交流。"""
        elif state == ConversationState.AWAITING_REQUIREMENT:
            return base_prompt + """

你的职责：
1. 询问用户是否需要提供软件需求文档（可选）
2. 如果用户不需要，引导进入review阶段
3. 如果用户需要，等待用户提供需求文档

请以友好、专业的方式与用户交流。"""
        elif state == ConversationState.REVIEWING:
            return base_prompt + """

你的职责：
1. 根据checklist对MRT内容进行审查
2. 发现MRT中缺失或不符合checklist要求的内容
3. 给出具体、可操作的建议
4. 回答格式可以灵活，根据用户的需求调整（可以是列表、段落、表格等）
5. 如果用户要求特定格式的回复，请按照用户要求回复
6. 可以在对话中继续讨论和改进

请以友好、专业的方式与用户交流，帮助用户改进MRT质量。"""
        else:  # COMPLETED
            return base_prompt + """

Review已完成。如果用户需要review新的MRT，请引导用户上传新文件或粘贴新内容。"""

    def _build_context_message(self, state: ConversationState, mrt: Optional[MRTEntry], requirement: Optional[str]) -> str:
        """Build context message with MRT and requirement."""
        # Only add full context in REVIEWING state
        if state != ConversationState.REVIEWING:
            return ""

        context_parts = []
        if mrt:
            context_parts.append(f"\n\n当前正在review的MRT内容：\n{mrt.content}")
        if requirement:
            context_parts.append(f"\n\n软件需求文档：\n{requirement}")

        return "".join(context_parts)

    def _trim_history(self, messages: List[Dict[str, str]], max_turns: int = 10) -> List[Dict[str, str]]:
        """Trim history to keep only recent messages."""
        if len(messages) <= max_turns:
            return messages
        # Keep system message if exists, then recent messages
        if messages and messages[0].get("role") == "system":
            return [messages[0]] + messages[-(max_turns - 1):]
        return messages[-max_turns:]

    def _handle_files(self, files: Optional[List[Dict[str, str]]]) -> tuple[str, bool]:
        """Handle file uploads and extract MRT content. Returns (combined_content, has_new_mrt)."""
        if not files:
            return "", False

        mrt_content_parts = []
        MAX_CONTENT_SIZE = 200000  # Increased to 200KB for base64 encoded files
        total_size = 0

        for file_info in files:
            file_name = file_info.get("name", "未命名文件")
            file_content = file_info.get("content", "")
            if not file_content:
                continue
                
            # Check if this is a binary file (PDF/Word) encoded as base64
            if file_content.startswith("[BINARY_FILE:"):
                # Extract file extension and base64 content
                try:
                    parts = file_content[len("[BINARY_FILE:"):].split(":", 1)
                    file_ext = parts[0] if parts else ""
                    # Note: base64_content is available but not used yet (for future PDF/Word parsing)
                    # base64_content = parts[1].rstrip("]") if len(parts) > 1 else ""
                    
                    # For binary files, we can't extract text directly
                    # Return a message indicating the file was received
                    mrt_content_parts.append(
                        f"[文件: {file_name}]\n"
                        f"[注意: 这是一个{file_ext}格式的文件。"
                        f"由于二进制文件无法直接解析，请手动复制文件内容并粘贴到对话框中，"
                        f"或使用文本格式(.txt)的文件。]\n"
                    )
                    total_size += 100  # Approximate size for the message
                except Exception:
                    # If parsing fails, just note the file
                    mrt_content_parts.append(
                        f"[文件: {file_name}]\n"
                        f"[注意: 无法解析此文件。请使用文本格式(.txt)的文件或手动粘贴内容。]\n"
                    )
                    total_size += 100
                continue
                
            # Handle text files
            file_size = len(file_content)
            if file_size > MAX_CONTENT_SIZE:
                file_content = file_content[:MAX_CONTENT_SIZE] + f"\n\n[注意：文件内容过长，已截断。原始大小: {file_size} 字符]"
                file_size = MAX_CONTENT_SIZE

            if total_size + file_size > MAX_CONTENT_SIZE:
                remaining = MAX_CONTENT_SIZE - total_size
                if remaining > 0:
                    mrt_content_parts.append(
                        f"[文件: {file_name}]\n{file_content[:remaining]}\n\n[注意：剩余文件因总大小限制未包含]"
                    )
                break

            mrt_content_parts.append(f"[文件: {file_name}]\n{file_content}")
            total_size += file_size

        if mrt_content_parts:
            return "\n\n".join(mrt_content_parts).strip(), True
        return "", False

    def chat_stream(self, request: ChatRequest) -> Generator[str, None, None]:
        """Handle chat request with streaming response."""
        # Get or create session (same logic as chat())
        session_id = request.session_id or self.sessions.create()
        session = self.sessions.get(session_id)
        if session is None:
            session_id = self.sessions.create()
            session = self.sessions.get(session_id)
            assert session is not None

        current_state = session["state"]
        detected_new_mrt = False

        # Handle files and MRT content (same logic as chat())
        file_content, has_file_mrt = self._handle_files(request.files)
        if has_file_mrt:
            current_mrt = self.sessions.get_current_mrt(session_id)
            if not current_mrt or current_mrt.content != file_content:
                if current_mrt:
                    self.sessions.clear_mrt(session_id)
                self.sessions.add_mrt(session_id, file_content)
                detected_new_mrt = True

        if request.mrt_content:
            content = request.mrt_content.strip()
            current_mrt = self.sessions.get_current_mrt(session_id)
            if not current_mrt or current_mrt.content != content:
                if current_mrt:
                    self.sessions.clear_mrt(session_id)
                self.sessions.add_mrt(session_id, content)
                detected_new_mrt = True

        if request.software_requirement:
            session["software_requirement"] = request.software_requirement.strip()

        # Get current data
        has_mrt = self.sessions.has_mrt(session_id)
        has_req = self.sessions.has_requirement(session_id)
        current_mrt = self.sessions.get_current_mrt(session_id)
        requirement = session.get("software_requirement")

        # Determine and update state
        next_state = self._determine_next_state(session, has_mrt, has_req, detected_new_mrt)
        if next_state != current_state:
            self.sessions.set_state(session_id, next_state)
            session["state"] = next_state

        # Build messages
        messages = request.messages or []
        user_message = request.message or ""
        messages = self._trim_history(messages, max_turns=10)

        # Build context message
        context_message = self._build_context_message(next_state, current_mrt, requirement)

        # Handle initial state
        if next_state == ConversationState.INITIAL and not user_message and not has_file_mrt and not request.mrt_content:
            welcome_msg = self._get_welcome_message()
            yield welcome_msg
            return

        # Handle guidance messages
        guidance = self._get_guidance_message(next_state)
        if guidance and (detected_new_mrt or next_state != current_state):
            if next_state in [ConversationState.AWAITING_MRT, ConversationState.AWAITING_REQUIREMENT]:
                yield guidance + "\n"

        # Add user message
        if user_message:
            full_user_message = f"{user_message}{context_message}" if context_message else user_message
            messages.append({"role": "user", "content": full_user_message})
        elif has_file_mrt and not user_message:
            default_msg = "请帮我review这些文件"
            full_user_message = f"{default_msg}{context_message}" if context_message else default_msg
            messages.append({"role": "user", "content": full_user_message})

        # Build system prompt
        system_prompt = self._build_system_prompt(next_state, requirement)

        # Stream LLM response
        if messages and next_state in [ConversationState.REVIEWING, ConversationState.AWAITING_REQUIREMENT]:
            try:
                for chunk in self.llm_client.chat_stream(messages, system_prompt=system_prompt):
                    yield chunk
            except Exception as exc:
                error_str = str(exc)
                if "Connection reset" in error_str or "Connection reset by peer" in error_str:
                    error_msg = "连接被重置：可能是文件太大或网络不稳定。请尝试：1) 上传较小的文件 2) 检查网络连接 3) 稍后重试"
                elif "timeout" in error_str.lower() or "timed out" in error_str.lower():
                    error_msg = "请求超时：处理时间过长。请尝试上传较小的文件或分批上传。"
                elif "Connection" in error_str:
                    error_msg = "连接错误：无法连接到AI服务。请检查网络连接或稍后重试。"
                else:
                    error_msg = f"处理请求时出错：{error_str}"
                yield error_msg
        elif not messages and not guidance:
            yield "您好！我可以帮您review MRT内容。请上传文件或输入内容开始审查。"
