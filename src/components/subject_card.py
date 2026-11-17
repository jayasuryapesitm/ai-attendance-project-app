import streamlit as st


def subject_card(name, code, section, stats=None, footer_callback=None):
    with st.container(border=True):
        st.subheader(name)
        details = f"Course code: {code}"
        if section:
            details += f" · Section: {section}"
        st.caption(details)

        if stats:
            columns = st.columns(len(stats))
            for column, (icon, label, value) in zip(columns, stats):
                with column:
                    st.metric(f"{icon} {label}", value)
            total = next(
                (value for _, label, value in stats if label.lower() == "total"),
                None,
            )
            attended = next(
                (value for _, label, value in stats if label.lower() == "attended"),
                None,
            )
            if total and attended is not None:
                attendance_rate = min(1.0, max(0.0, attended / total))
                st.progress(
                    attendance_rate,
                    text=f"Attendance {attendance_rate:.1%}",
                )

        if footer_callback:
            footer_callback()
