"""ResidentScribe V1: a review-first Chinese medical-note drafting tool."""

from __future__ import annotations

import json
import re

import streamlit as st
import streamlit.components.v1 as components

from bailian_stt import TranscriptionError, transcribe_audio
from medical_note import NoteGenerationError, generate_note


st.set_page_config(page_title="ResidentScribe", page_icon="🩺", layout="wide")


def redact_obvious_identifiers(text: str) -> str:
    """Redact common Chinese identifiers before sending a transcript to an LLM.

    This is intentionally conservative: it is a convenience guardrail, not a
    de-identification guarantee. Users must still avoid entering patient IDs.
    """
    patterns = (
        (r"(?<!\d)1[3-9]\d{9}(?!\d)", "[手机号已隐藏]"),
        (r"(?<!\d)\d{17}[\dXx](?!\d)", "[身份证号已隐藏]"),
        (r"(?i)(住院号|门诊号|病案号)\s*[:：]?\s*[A-Za-z0-9-]+", r"\1：[编号已隐藏]"),
    )
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


def api_key(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
    except FileNotFoundError:
        value = None
    return value or None


def main() -> None:
    st.title("🩺 ResidentScribe")
    st.caption("中文问诊录音 → 转写 → 入院病历草稿（必须由临床医生审核）")
    st.warning(
        "仅用于教学、模拟或获得授权的临床辅助场景。不会保存音频或病历；"
        "请勿上传可识别患者信息，并遵守医院制度与知情同意要求。"
    )

    dashscope_key = api_key("DASHSCOPE_API_KEY")
    if not dashscope_key:
        st.info("尚未配置百炼 API Key。请按 README 创建 `.streamlit/secrets.toml` 后重启应用。")

    st.sidebar.header("生成设置")
    st.sidebar.caption("使用百炼：语音转写与病历草稿共用一把 API Key。")
    redact = st.sidebar.toggle("发送前隐藏常见编号", value=True)
    st.sidebar.markdown("本工具不会作出诊断、处方或检查决策。")

    consent = st.checkbox("我确认已获得必要授权，且内容中不含可识别患者信息。")

    st.subheader("方式一：直接粘贴转录文本（推荐手机使用）")
    st.caption("在 iPhone 录音中复制转写内容，粘贴到这里后可直接生成病历草稿，无需再次上传音频。")
    pasted_transcript = st.text_area(
        "粘贴问诊转录文本",
        placeholder="长按 iPhone 录音中的文字，选择复制后粘贴到这里…",
        height=180,
        key="pasted_transcript",
    )
    if st.button(
        "使用这段文本",
        type="primary",
        disabled=not (consent and pasted_transcript.strip()),
    ):
        st.session_state["transcript"] = pasted_transcript.strip()
        st.session_state.pop("note", None)

    st.divider()
    st.subheader("方式二：录音或上传音频")
    st.caption("如手机录音不可用，可使用上方的直接粘贴文本方式。")
    audio_recording = st.audio_input("录制模拟或授权的问诊音频（5 分钟内、10 MB 内）", sample_rate=16_000)
    uploaded_file = st.file_uploader(
        "或上传音频", type=["wav", "mp3", "m4a", "mp4", "webm", "ogg", "flac"]
    )
    audio = audio_recording or uploaded_file

    if audio:
        st.audio(audio)

    if st.button("① 转写问诊", type="primary", disabled=not (audio and consent and dashscope_key)):
        filename = getattr(audio, "name", "consultation.wav")
        audio_bytes = audio.getvalue()
        with st.spinner("正在转写…"):
            try:
                transcript = transcribe_audio(audio_bytes, filename, dashscope_key)
            except TranscriptionError as exc:
                st.error(f"转写失败：{exc}")
            else:
                st.session_state["transcript"] = transcript
                st.session_state.pop("note", None)

    transcript = st.session_state.get("transcript", "")
    if transcript:
        st.subheader("转录文本")
        edited_transcript = st.text_area(
            "请先校对人名、数字、时间与否定词；可直接修改。",
            value=transcript,
            height=220,
        )
        st.session_state["transcript"] = edited_transcript

        if st.button("② 生成病历草稿", disabled=not (edited_transcript.strip() and dashscope_key)):
            llm_input = redact_obvious_identifiers(edited_transcript) if redact else edited_transcript
            with st.spinner("正在整理病历草稿…"):
                try:
                    note = generate_note(llm_input, dashscope_key)
                except NoteGenerationError as exc:
                    st.error(f"生成失败：{exc}")
                else:
                    st.session_state["note"] = note

    note = st.session_state.get("note", "")
    if note:
        st.subheader("病历草稿")
        st.caption("请逐项核对。未询及不等于阴性；不得将此草稿直接用于病历签署。")
        st.markdown(note)
        st.download_button(
            "下载草稿（.md）",
            data=note,
            file_name="resident-scribe-draft.md",
            mime="text/markdown",
        )
        note_json = json.dumps(note, ensure_ascii=False)
        components.html(
            f"""
            <button onclick='navigator.clipboard.writeText({note_json}); this.textContent="已复制";'>
              复制完整病历
            </button>
            """,
            height=40,
        )
        st.text_area("复制用纯文本", value=note, height=300)


if __name__ == "__main__":
    main()
