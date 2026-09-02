"""Bailian adapter for source-grounded note drafting."""

from __future__ import annotations

import dashscope

from prompts import SYSTEM_INSTRUCTION


class NoteGenerationError(RuntimeError):
    """A user-facing note-generation failure."""


def generate_note(transcript: str, api_key: str) -> str:
    """Draft a note with Qwen through the Bailian DashScope API."""
    try:
        response = dashscope.Generation.call(
            model="qwen-plus",
            api_key=api_key,
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": f"以下是需要整理的问诊转录文本：\n\n{transcript}"},
            ],
            result_format="message",
            temperature=0.1,
            max_tokens=1800,
        )
    except Exception as exc:  # Provider errors should not expose credentials.
        raise NoteGenerationError("请检查百炼 API Key、模型权限和网络连接。") from exc

    if getattr(response, "status_code", 200) != 200:
        raise NoteGenerationError("百炼未能生成草稿，请检查模型权限、配额和网络连接。")

    try:
        text = response.output.choices[0].message.content
    except (AttributeError, IndexError, KeyError, TypeError) as exc:
        raise NoteGenerationError("百炼返回格式异常，请稍后重试。") from exc

    if not text or not text.strip():
        raise NoteGenerationError("模型没有返回内容，请缩短转录文本后重试。")
    return text.strip()
