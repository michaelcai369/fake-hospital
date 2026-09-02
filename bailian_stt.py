"""Speech-to-text adapter for Alibaba Cloud Bailian."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

import dashscope


MAX_AUDIO_BYTES = 10 * 1024 * 1024


class TranscriptionError(RuntimeError):
    """A user-facing transcription failure."""


def transcribe_audio(audio_bytes: bytes, filename: str, api_key: str) -> str:
    """Transcribe a short recording with Qwen3-ASR-Flash.

    DashScope supports a local ``file://`` URI, so the uploaded audio is only
    written to a temporary file for the duration of the API request.
    """
    if not audio_bytes:
        raise TranscriptionError("音频为空。")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise TranscriptionError("百炼短音频转写仅支持 10 MB 以内的文件，请裁剪后重试。")

    suffix = Path(filename).suffix or ".wav"
    try:
        with NamedTemporaryFile(suffix=suffix) as audio_file:
            audio_file.write(audio_bytes)
            audio_file.flush()
            response = dashscope.MultiModalConversation.call(
                model="qwen3-asr-flash",
                api_key=api_key,
                messages=[
                    {"role": "user", "content": [{"audio": f"file://{audio_file.name}"}]}
                ],
                result_format="message",
                asr_options={"language": "zh", "enable_itn": True},
            )
            if getattr(response, "status_code", 200) != 200:
                raise TranscriptionError("百炼未能完成转写，请检查模型权限、配额和网络连接。")
            text = response.output.choices[0].message.content[0]["text"]
    except TranscriptionError:
        raise
    except Exception as exc:  # SDK exceptions vary by release.
        raise TranscriptionError("请检查百炼 API Key、网络和音频格式。") from exc

    if not text or not text.strip():
        raise TranscriptionError("没有识别到语音，请尝试更清晰、更短的录音。")
    return text.strip()
