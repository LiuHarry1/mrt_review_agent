"""File handling utilities for chat service."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .file_parser import parse_file_content

logger = logging.getLogger(__name__)


def format_files_for_message(files: Optional[List[Dict[str, str]]]) -> str:
    """
    Handle file uploads and format them for user message in conversation history.
    
    Args:
        files: List of file dictionaries with 'name' and 'content' keys
        
    Returns:
        Formatted file content string to be added to user message.
        Format: "[File: filename]\n{content}" for each file.
    """
    if not files:
        return ""

    file_parts = []
    MAX_CONTENT_SIZE = 50000  # Limit file content size per file
    MAX_TOTAL_SIZE = 100000  # Limit total size for all files

    for file_info in files:
        file_name = file_info.get("name", "untitled")
        file_content = file_info.get("content", "")
        if not file_content:
            continue

        # Parse file content
        parsed_content = None
        if file_content.startswith("[BINARY_FILE:"):
            # Try to parse binary file
            try:
                parts = file_content[len("[BINARY_FILE:"):].split(":", 1)
                file_ext = parts[0] if parts else ""
                
                if file_ext in [".pdf", ".doc", ".docx"]:
                    parsed_content = parse_file_content(file_name, file_content)
            except Exception as e:
                logger.warning(f"Failed to parse binary file {file_name}: {e}")

        if parsed_content is None:
            # Handle text files or failed binary parsing
            if not file_content.startswith("[BINARY_FILE:"):
                parsed_content = file_content
            else:
                # Binary file that couldn't be parsed
                file_parts.append(
                    f"[File: {file_name}]\n"
                    f"[Note: This is a binary file that could not be parsed. "
                    f"Please paste the file content as text or use a text format file.]\n"
                )
                continue

        # Truncate if too long
        if len(parsed_content) > MAX_CONTENT_SIZE:
            parsed_content = (
                parsed_content[:MAX_CONTENT_SIZE] + 
                f"\n\n[Note: File content truncated. Original size: {len(parsed_content)} characters]"
            )

        # Check total size
        current_total = sum(len(part) for part in file_parts)
        if current_total + len(parsed_content) > MAX_TOTAL_SIZE:
            remaining = MAX_TOTAL_SIZE - current_total
            if remaining > 0:
                file_parts.append(
                    f"[File: {file_name}]\n{parsed_content[:remaining]}\n\n"
                    f"[Note: Remaining file content omitted due to size limit]"
                )
            break

        file_parts.append(f"[File: {file_name}]\n{parsed_content}")

    if file_parts:
        return "\n\n".join(file_parts)
    return ""

