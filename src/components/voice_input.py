import streamlit as st


_AUDIO_TYPES = ["wav", "mp3", "ogg", "webm", "m4a"]


def _clear_audio_recording(key):
    st.session_state.pop(key, None)


def voice_input(label, *, key, disabled=False):
    input_method = st.radio(
        "Voice input method",
        ("Live microphone", "Upload audio file"),
        horizontal=True,
        key=f"{key}_method",
        disabled=disabled,
        help=(
            "Use Live microphone for a fresh voice check. Choose Upload audio "
            "file if the browser blocks microphone access."
        ),
    )

    if input_method == "Live microphone":
        st.caption(
            f"{label}. Allow microphone access when your browser asks, then "
            "stop recording when you finish."
        )
        audio = st.audio_input(
            label,
            sample_rate=16000,
            key=key,
            disabled=disabled,
            help="Record a clear voice sample of at least one second.",
        )
        if audio is not None:
            clear_column, download_column = st.columns(2)
            with clear_column:
                st.button(
                    "Clear recording",
                    key=f"{key}_clear",
                    on_click=_clear_audio_recording,
                    args=(key,),
                )
            with download_column:
                st.download_button(
                    "Download as WAV",
                    data=audio.getvalue(),
                    file_name="voice-recording.wav",
                    mime="audio/wav",
                    key=f"{key}_download",
                    disabled=disabled,
                )
        return audio

    st.caption(
        f"{label}. Upload a clear recording of at least one second "
        "(WAV, MP3, OGG, WEBM, or M4A)."
    )
    return st.file_uploader(
        "Choose an audio file",
        type=_AUDIO_TYPES,
        key=f"{key}_upload",
        disabled=disabled,
        help="Microphone recording is unavailable in this browser session.",
    )
