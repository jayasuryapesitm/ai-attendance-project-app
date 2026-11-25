import hashlib
import json
import uuid

import streamlit as st

from src.pipelines.exam_marking import (
    subquestion_label,
    validate_marking_scheme,
)


def exam_review_fingerprint(
    title,
    total_marks,
    marking_scheme,
    blueprint_file,
    question_paper_file,
):
    digest = hashlib.sha256()
    digest.update(
        json.dumps(
            [title, total_marks, marking_scheme],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    for uploaded_file in (blueprint_file, question_paper_file):
        if uploaded_file is None:
            digest.update(b"\0")
        else:
            digest.update(hashlib.sha256(uploaded_file.getvalue()).digest())
    return digest.hexdigest()


def _widget_key(namespace, module_id, *parts):
    return "_".join(
        [str(namespace), str(module_id)]
        + [str(part) for part in parts]
    )


def _get_or_create_ids(key, initial_ids=None, create_one=True):
    if key not in st.session_state:
        if initial_ids is not None:
            st.session_state[key] = list(initial_ids)
        else:
            st.session_state[key] = [uuid.uuid4().hex] if create_one else []
    return st.session_state[key]


def _add_id(ids_key):
    ids = list(st.session_state[ids_key])
    ids.append(uuid.uuid4().hex)
    st.session_state[ids_key] = ids
    st.rerun()


def _remove_id(ids_key, item_id):
    st.session_state[ids_key] = [
        value for value in st.session_state[ids_key]
        if value != item_id
    ]
    st.rerun()


def render_marking_scheme_editor(total_marks, namespace, initial_scheme=None):
    generation_key = f"{namespace}_marking_generation"
    generation = st.session_state.setdefault(generation_key, 0)
    widget_namespace = f"{namespace}_{generation}"
    module_ids_key = f"{widget_namespace}_module_ids"
    initial_modules = (initial_scheme or {}).get("modules", [])
    module_ids = _get_or_create_ids(
        module_ids_key,
        [module["module_id"] for module in initial_modules]
        if initial_scheme is not None
        else None,
    )
    initial_modules_by_id = {
        module["module_id"]: module for module in initial_modules
    }

    st.subheader("Configure modules, questions, and marks")
    st.caption(
        "Enter the complete scheme from the exam documents. Questions in the "
        "same OR group share alternatives and must have identical question and "
        "sub-question marks; each group's attempt limit is shown below."
    )
    if st.button("Add module", key=f"{widget_namespace}_add_module"):
        _add_id(module_ids_key)

    modules = []
    question_number = 0
    for module_index, module_id in enumerate(module_ids, start=1):
        initial_module = initial_modules_by_id.get(module_id, {})
        question_ids_key = f"{widget_namespace}_{module_id}_question_ids"
        initial_questions = initial_module.get("questions", [])
        question_ids = _get_or_create_ids(
            question_ids_key,
            [question["question_id"] for question in initial_questions]
            if initial_module
            else None,
        )
        initial_questions_by_id = {
            question["question_id"]: question
            for question in initial_questions
        }
        initial_groups = {
            group["group_id"]: group
            for group in initial_module.get("or_groups", [])
        }
        with st.expander(f"Module {module_index}", expanded=True):
            module_name = st.text_input(
                "Module name",
                value=initial_module.get("name", f"Module {module_index}"),
                key=_widget_key(widget_namespace, module_id, "name"),
            )
            module_max = st.number_input(
                "Module maximum marks",
                min_value=0.0,
                value=float(initial_module.get("max_marks", 0)),
                step=1.0,
                key=_widget_key(widget_namespace, module_id, "max"),
            )
            raw_questions = []
            group_labels = {}
            for question_id in question_ids:
                initial_question = initial_questions_by_id.get(question_id, {})
                question_number += 1
                question_label = f"Q{question_number}"
                with st.container(border=True):
                    st.markdown(f"**{question_label}**")
                    question_max = st.number_input(
                        f"{question_label} maximum marks",
                        min_value=0.0,
                        value=float(initial_question.get("max_marks", 0)),
                        step=1.0,
                        key=_widget_key(
                            widget_namespace,
                            module_id,
                            question_id,
                            "max",
                        ),
                    )
                    initial_group = initial_groups.get(
                        initial_question.get("or_group_id"),
                        {},
                    )
                    group_label = st.text_input(
                        f"OR group for {question_label} (optional)",
                        placeholder="For example: A",
                        help=(
                            "Use the same label for every alternative in this "
                            "module. This field identifies the OR relationship; "
                            "it is not a marks field."
                        ),
                        value=initial_group.get("label", ""),
                        key=_widget_key(
                            widget_namespace,
                            module_id,
                            question_id,
                            "or_group",
                        ),
                    ).strip()
                    if group_label:
                        compulsory = False
                        st.caption(
                            f"{question_label} is an OR alternative; the student "
                            "chooses from its group."
                        )
                    else:
                        compulsory = st.checkbox(
                            f"{question_label} is compulsory",
                            value=bool(
                                initial_question.get("compulsory", True)
                            ),
                            key=_widget_key(
                                widget_namespace,
                                module_id,
                                question_id,
                                "compulsory",
                            ),
                        )

                    subquestion_ids_key = (
                        f"{widget_namespace}_{module_id}_{question_id}_"
                        "subquestion_ids"
                    )
                    subquestion_ids = _get_or_create_ids(
                        subquestion_ids_key,
                        [
                            subquestion["subquestion_id"]
                            for subquestion in initial_question.get(
                                "subquestions",
                                [],
                            )
                        ]
                        if initial_question
                        else None,
                    )
                    initial_subquestions = {
                        subquestion["subquestion_id"]: subquestion
                        for subquestion in initial_question.get(
                            "subquestions",
                            [],
                        )
                    }
                    subquestions = []
                    if subquestion_ids:
                        st.caption(
                            f"Sub-questions for {question_label} "
                            "(remove all to configure one standalone question)"
                        )
                    for sub_index, subquestion_id in enumerate(subquestion_ids):
                        initial_subquestion = initial_subquestions.get(
                            subquestion_id,
                            {},
                        )
                        sub_label = (
                            f"{question_label}({subquestion_label(sub_index)})"
                        )
                        sub_max = st.number_input(
                            f"{sub_label} maximum marks",
                            min_value=0.0,
                            value=float(initial_subquestion.get("max_marks", 0)),
                            step=1.0,
                            key=_widget_key(
                                widget_namespace,
                                module_id,
                                question_id,
                                subquestion_id,
                                "max",
                            ),
                        )
                        rubric_notes = st.text_area(
                            f"Expected concepts for {sub_label} "
                            "(optional if clear in blueprint)",
                            value=initial_subquestion.get("rubric_notes", ""),
                            key=_widget_key(
                                widget_namespace,
                                module_id,
                                question_id,
                                subquestion_id,
                                "rubric_notes",
                            ),
                            height=70,
                        )
                        subquestions.append({
                            "subquestion_id": subquestion_id,
                            "label": sub_label,
                            "max_marks": sub_max,
                            "rubric_notes": rubric_notes,
                            "checkpoints": initial_subquestion.get(
                                "checkpoints",
                                [],
                            ),
                        })
                        if st.button(
                            f"Remove {sub_label}",
                            key=_widget_key(
                                widget_namespace,
                                module_id,
                                question_id,
                                subquestion_id,
                                "remove",
                            ),
                            type="tertiary",
                        ):
                            _remove_id(subquestion_ids_key, subquestion_id)
                    if st.button(
                        f"Add sub-question to {question_label}",
                        key=_widget_key(
                            widget_namespace,
                            module_id,
                            question_id,
                            "add_subquestion",
                        ),
                        type="tertiary",
                    ):
                        _add_id(subquestion_ids_key)
                    if st.button(
                        f"Remove {question_label}",
                        key=_widget_key(
                            widget_namespace,
                            module_id,
                            question_id,
                            "remove",
                        ),
                        type="tertiary",
                    ):
                        _remove_id(question_ids_key, question_id)

                normalized_group = group_label.casefold()
                if normalized_group:
                    group_labels.setdefault(normalized_group, group_label)
                raw_questions.append({
                    "question_id": question_id,
                    "label": question_label,
                    "max_marks": question_max,
                    "compulsory": compulsory and not group_label,
                    "or_group_label": normalized_group or None,
                    "subquestions": subquestions,
                    "checkpoints": initial_question.get("checkpoints", []),
                    "rubric_notes": initial_question.get("rubric_notes", ""),
                })

            if st.button(
                f"Add question to Module {module_index}",
                key=f"{widget_namespace}_{module_id}_add_question",
                type="secondary",
            ):
                _add_id(question_ids_key)

            group_ids = {}
            or_groups = []
            for group_index, (normalized_label, label) in enumerate(
                group_labels.items(),
                start=1,
            ):
                group_id = f"{module_id}-or-{group_index}"
                group_ids[normalized_label] = group_id
                alternatives_count = sum(
                    question["or_group_label"] == normalized_label
                    for question in raw_questions
                )
                allowed_attempts = st.number_input(
                    f"Maximum alternatives to attempt in OR group “{label}”",
                    min_value=1,
                    max_value=alternatives_count,
                    value=int(
                        initial_groups.get(group_id, {}).get(
                            "allowed_attempts",
                            1,
                        )
                    ),
                    step=1,
                    key=_widget_key(
                        widget_namespace,
                        module_id,
                        group_id,
                        "allowed_attempts",
                    ),
                )
                or_groups.append({
                    "group_id": group_id,
                    "label": label,
                    "allowed_attempts": allowed_attempts,
                    "policy": "highest_scoring",
                })

            questions = []
            for question in raw_questions:
                group_label = question.pop("or_group_label")
                question["or_group_id"] = (
                    group_ids.get(group_label) if group_label else None
                )
                questions.append(question)
            modules.append({
                "module_id": module_id,
                "name": module_name,
                "max_marks": module_max,
                "questions": questions,
                "or_groups": or_groups,
            })

            if st.button(
                f"Remove Module {module_index}",
                key=f"{widget_namespace}_{module_id}_remove",
                type="tertiary",
            ):
                _remove_id(module_ids_key, module_id)

    scheme = {"modules": modules, "alternative_policy": "highest_scoring"}
    render_marking_scheme_summary(scheme, total_marks)
    try:
        validate_marking_scheme(scheme, total_marks)
    except ValueError as error:
        st.error(f"Marking scheme needs attention: {error}")
    return scheme, generation_key


def render_marking_scheme_summary(marking_scheme, total_marks):
    module_total = sum(
        float(module.get("max_marks") or 0)
        for module in marking_scheme.get("modules", [])
    )
    st.metric(
        "Total examination marks",
        f"{module_total:g} allocated / {float(total_marks):g} maximum",
    )
    for module in marking_scheme.get("modules", []):
        st.markdown(
            f"**{module.get('name', 'Module')} — "
            f"{float(module.get('max_marks') or 0):g} marks**"
        )
        for question in module.get("questions", []):
            st.caption(
                f"{question['label']}: {float(question['max_marks']):g} marks"
            )
            for subquestion in question.get("subquestions", []):
                st.caption(
                    f"  {subquestion['label']}: "
                    f"{float(subquestion['max_marks']):g} marks"
                )
        for group in module.get("or_groups", []):
            st.caption(
                f"OR group {group['label']}: attempt at most "
                f"{group['allowed_attempts']} alternative(s); highest marks count."
            )
