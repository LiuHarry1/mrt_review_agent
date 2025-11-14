from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from ..checklist import resolve_checklist
from ..llm import ChatbotClient
from ..schemas import (
    ChatRequest,
    ChatResponse,
    ChatTurn,
    ChecklistItem,
    ConversationState,
)


class MRTEntry:
    """Represents a single MRT entry with its content and optional name."""

    def __init__(self, content: str, name: Optional[str] = None):
        self.id = uuid.uuid4().hex[:8]
        self.name = name or f"MRT-{self.id}"
        self.content = content


class SessionStore:
    def __init__(self):
        self._sessions: Dict[str, Dict] = {}

    def create(self) -> str:
        session_id = uuid.uuid4().hex
        self._sessions[session_id] = {
            "state": ConversationState.READY,
            "history": [],
            "mrts": {},  # Dict[str, MRTEntry] - multiple MRTs
            "current_mrt_id": None,  # Current active MRT ID
            "checklist": None,  # None means using default checklist
        }
        return session_id

    def get(self, session_id: str) -> Optional[Dict]:
        return self._sessions.get(session_id)

    def append_history(self, session_id: str, role: str, content: str) -> None:
        if session_id not in self._sessions:
            raise KeyError("Session not found")
        self._sessions[session_id]["history"].append({"role": role, "content": content})

    def add_mrt(self, session_id: str, content: str, name: Optional[str] = None) -> str:
        """Add a new MRT to the session and return its ID."""
        if session_id not in self._sessions:
            raise KeyError("Session not found")
        mrt_entry = MRTEntry(content, name)
        self._sessions[session_id]["mrts"][mrt_entry.id] = mrt_entry
        self._sessions[session_id]["current_mrt_id"] = mrt_entry.id
        return mrt_entry.id

    def get_current_mrt(self, session_id: str) -> Optional[MRTEntry]:
        """Get the current active MRT."""
        if session_id not in self._sessions:
            return None
        session = self._sessions[session_id]
        current_id = session.get("current_mrt_id")
        if not current_id:
            return None
        return session["mrts"].get(current_id)


class MRTReviewAgent:
    def __init__(self, chatbot_client: Optional[ChatbotClient] = None, session_store: Optional[SessionStore] = None):
        self.chatbot_client = chatbot_client or ChatbotClient()
        self.sessions = session_store or SessionStore()

    def _build_system_prompt(self, checklist: List[ChecklistItem]) -> str:
        """Build system prompt with current checklist context."""
        checklist_text = "\n".join([f"- {item.id}: {item.description}" for item in checklist])
        return f"""你是一个专业的软件测试审查助手。你的任务是根据提供的checklist来review用户的MRT（手动回归测试）内容。

当前的checklist包括：
{checklist_text}

你的职责：
1. 根据checklist对MRT内容进行审查
2. 发现MRT中缺失或不符合checklist要求的内容
3. 给出具体、可操作的建议
4. 回答格式可以灵活，根据用户的需求调整（可以是列表、段落、表格等）
5. 如果用户要求特定格式的回复，请按照用户要求回复

请以友好、专业的方式与用户交流，帮助用户改进MRT质量。"""

    def chat(self, request: ChatRequest) -> ChatResponse:
        session_id = request.session_id or self.sessions.create()
        session = self.sessions.get(session_id)
        if session is None:
            session_id = self.sessions.create()
            session = self.sessions.get(session_id)
            assert session is not None

        # Get current checklist (default if not set)
        checklist = resolve_checklist(session.get("checklist"))
        
        # Handle files (multiple files supported)
        user_message = request.message or ""
        mrt_content_parts = []
        
        # Maximum content size (in characters) to avoid timeout
        MAX_CONTENT_SIZE = 50000  # ~50KB of text
        
        # Collect file contents as MRT content
        if request.files:
            total_size = 0
            for file_info in request.files:
                file_name = file_info.get("name", "未命名文件")
                file_content = file_info.get("content", "")
                if file_content:
                    file_size = len(file_content)
                    # Limit individual file content size
                    if file_size > MAX_CONTENT_SIZE:
                        file_content = file_content[:MAX_CONTENT_SIZE] + f"\n\n[注意：文件内容过长，已截断。原始大小: {file_size} 字符]"
                        file_size = MAX_CONTENT_SIZE
                    
                    # Check total size
                    if total_size + file_size > MAX_CONTENT_SIZE:
                        mrt_content_parts.append(f"[文件: {file_name}]\n{file_content[:MAX_CONTENT_SIZE - total_size]}\n\n[注意：剩余文件因总大小限制未包含]")
                        break
                    
                    mrt_content_parts.append(f"[文件: {file_name}]\n{file_content}")
                    total_size += file_size
                    if not user_message:
                        user_message = "请帮我review这些文件"
        
        # Combine all file contents as MRT content
        if mrt_content_parts:
            combined_mrt = "\n\n".join(mrt_content_parts)
            self.sessions.add_mrt(session_id, combined_mrt.strip())
        
        # Handle MRT content from request
        if request.mrt_content:
            self.sessions.add_mrt(session_id, request.mrt_content.strip())
        
        # Handle checklist from request (direct assignment)
        if request.checklist:
            session["checklist"] = request.checklist
            checklist = request.checklist
        
        # Get current MRT for review context
        current_mrt = self.sessions.get_current_mrt(session_id)
        
        # Build context for chatbot
        review_context = ""
        if current_mrt:
            review_context = f"\n\n当前正在review的MRT内容：\n{current_mrt.content}\n"
        
        replies: List[str] = []

        # Build messages for chatbot
        messages = []
        # Add conversation history (limit to last 6 turns = 3 pairs)
        history = session["history"][-6:] if len(session["history"]) > 6 else session["history"]
        for turn in history:
            messages.append({"role": turn["role"], "content": turn["content"]})
        
        # Add current user message with context
        if user_message:
            full_user_message = user_message
            if review_context and current_mrt:
                full_user_message = f"{user_message}{review_context}"
            
            messages.append({"role": "user", "content": full_user_message})
            self.sessions.append_history(session_id, role="user", content=user_message)
        
        # Get response from chatbot
        system_prompt = self._build_system_prompt(checklist)
        try:
            chatbot_response = self.chatbot_client.chat(messages, system_prompt=system_prompt)
            replies.append(chatbot_response)
            self.sessions.append_history(session_id, role="assistant", content=chatbot_response)
        except Exception as exc:
            # Provide more user-friendly error messages
            error_str = str(exc)
            if "Connection reset" in error_str or "Connection reset by peer" in error_str:
                error_msg = "连接被重置：可能是文件太大或网络不稳定。请尝试：1) 上传较小的文件 2) 检查网络连接 3) 稍后重试"
            elif "timeout" in error_str.lower() or "timed out" in error_str.lower():
                error_msg = "请求超时：处理时间过长。请尝试上传较小的文件或分批上传。"
            elif "Connection" in error_str:
                error_msg = "连接错误：无法连接到AI服务。请检查网络连接或稍后重试。"
            else:
                error_msg = f"处理请求时出错：{error_str}"
            replies.append(error_msg)
            self.sessions.append_history(session_id, role="assistant", content=error_msg)

        if not replies:
            replies.append("您好！我可以帮您review MRT内容。请上传文件或输入内容开始审查。")

        return self._build_response(session_id, session, replies)

    def _build_response(
        self,
        session_id: str,
        session: Dict,
        replies: List[str],
        suggestions: Optional[List] = None,
        summary: Optional[str] = None,
    ) -> ChatResponse:
        history = [ChatTurn(role=entry["role"], content=entry["content"]) for entry in session["history"]]
        return ChatResponse(
            session_id=session_id,
            state=session["state"],
            replies=replies,
            suggestions=suggestions,
            summary=summary,
            history=history,
        )

