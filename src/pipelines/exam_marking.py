import math


def subquestion_label(index):
    if index < 0:
        raise ValueError("Sub-question index must not be negative.")
    label = ""
    while True:
        index, remainder = divmod(index, 26)
        label = chr(ord("a") + remainder) + label
        if index == 0:
            return label
        index -= 1


def _positive_marks(value, description):
    try:
        marks = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{description} must be a positive number.") from error
    if not math.isfinite(marks) or marks <= 0:
        raise ValueError(f"{description} must be a positive number.")
    return marks


def _validate_or_group_consistency(module_name, group_id, alternatives):
    if len(alternatives) < 2:
        raise ValueError(
            f"OR group {group_id} in {module_name} must contain at least "
            "two alternatives."
        )

    reference = alternatives[0]
    reference_marks = _positive_marks(
        reference.get("max_marks"),
        f"{reference.get('label', 'Question')} maximum marks",
    )
    reference_subquestions = reference.get("subquestions", [])
    if not isinstance(reference_subquestions, list):
        raise ValueError(
            f"{reference.get('label', 'Question')} has invalid sub-questions."
        )
    if any(not isinstance(item, dict) for item in reference_subquestions):
        raise ValueError(
            f"{reference.get('label', 'Question')} has invalid sub-questions."
        )
    reference_distribution = tuple(
        _positive_marks(
            subquestion.get("max_marks"),
            f"{subquestion.get('label', 'Sub-question')} maximum marks",
        )
        for subquestion in reference_subquestions
    )

    for alternative in alternatives[1:]:
        question_label = alternative.get("label", "Question")
        alternative_marks = _positive_marks(
            alternative.get("max_marks"),
            f"{question_label} maximum marks",
        )
        if not math.isclose(
            reference_marks,
            alternative_marks,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(
                f"OR group {group_id} in {module_name} must give every "
                "alternative the same maximum marks."
            )

        subquestions = alternative.get("subquestions", [])
        if not isinstance(subquestions, list):
            raise ValueError(
                f"{question_label} has invalid sub-questions."
            )
        if any(not isinstance(item, dict) for item in subquestions):
            raise ValueError(
                f"{question_label} has invalid sub-questions."
            )
        distribution = tuple(
            _positive_marks(
                subquestion.get("max_marks"),
                f"{subquestion.get('label', 'Sub-question')} maximum marks",
            )
            for subquestion in subquestions
        )
        if len(distribution) != len(reference_distribution) or any(
            not math.isclose(
                expected_marks,
                actual_marks,
                rel_tol=0.0,
                abs_tol=1e-9,
            )
            for expected_marks, actual_marks in zip(
                reference_distribution,
                distribution,
            )
        ):
            raise ValueError(
                f"OR group {group_id} in {module_name} must have the same "
                "sub-question count and marks distribution for every alternative."
            )


def get_scoring_targets(marking_scheme):
    targets = []
    for module in marking_scheme.get("modules", []):
        for question in module.get("questions", []):
            subquestions = question.get("subquestions", [])
            if subquestions:
                for subquestion in subquestions:
                    targets.append({
                        "target_id": subquestion["subquestion_id"],
                        "question_id": question["question_id"],
                        "module_id": module["module_id"],
                        "question_no": subquestion["label"],
                        "max_marks": subquestion["max_marks"],
                        "checkpoints": subquestion.get("checkpoints", []),
                        "rubric_notes": subquestion.get("rubric_notes", ""),
                    })
            else:
                targets.append({
                    "target_id": question["question_id"],
                    "question_id": question["question_id"],
                    "module_id": module["module_id"],
                    "question_no": question["label"],
                    "max_marks": question["max_marks"],
                    "checkpoints": question.get("checkpoints", []),
                    "rubric_notes": question.get("rubric_notes", ""),
                })
    return targets


def validate_student_answers(marking_scheme, answers):
    if not isinstance(answers, dict):
        raise ValueError("Exam answers must be submitted as a structured response.")
    answer_text = answers.get("answers", {})
    selected_alternatives = answers.get("selected_alternatives", {})
    if not isinstance(answer_text, dict) or not isinstance(selected_alternatives, dict):
        raise ValueError("Exam answers or OR selections have an invalid format.")

    scoring_targets = get_scoring_targets(marking_scheme)
    known_targets = {target["target_id"] for target in scoring_targets}
    if set(answer_text) - known_targets:
        raise ValueError("The submitted answers contain an unknown question.")
    normalized_answers = {}
    for target_id, value in answer_text.items():
        if not isinstance(value, str):
            raise ValueError("Each answer must be text.")
        normalized_answers[target_id] = value.strip()

    group_limits = {}
    group_questions = {}
    for module in marking_scheme.get("modules", []):
        for group in module.get("or_groups", []):
            alternatives = [
                question
                for question in module.get("questions", [])
                if question.get("or_group_id") == group["group_id"]
            ]
            _validate_or_group_consistency(
                module.get("name", "Module"),
                group["group_id"],
                alternatives,
            )
            group_limits[group["group_id"]] = int(group["allowed_attempts"])
        for question in module.get("questions", []):
            group_id = question.get("or_group_id")
            if group_id:
                group_questions.setdefault(group_id, set()).add(
                    question["question_id"]
                )
    if set(selected_alternatives) - set(group_limits):
        raise ValueError("The submission contains an unknown OR group.")

    normalized_selections = {}
    for group_id, question_ids in selected_alternatives.items():
        if not isinstance(question_ids, list) or len(question_ids) != len(set(question_ids)):
            raise ValueError("OR alternatives must be selected without duplicates.")
        if len(question_ids) > group_limits[group_id]:
            raise ValueError(
                f"Choose no more than {group_limits[group_id]} alternative(s) "
                f"for OR group {group_id}."
            )
        if set(question_ids) - group_questions[group_id]:
            raise ValueError("An OR selection contains an unrelated question.")
        normalized_selections[group_id] = list(question_ids)

    return {
        "answers": normalized_answers,
        "selected_alternatives": normalized_selections,
    }


def validate_marking_scheme(marking_scheme, total_marks):
    if not isinstance(marking_scheme, dict):
        raise ValueError("Configure the exam's module and question structure.")
    modules = marking_scheme.get("modules")
    if not isinstance(modules, list) or not modules:
        raise ValueError("Add at least one exam module.")

    module_ids = set()
    target_ids = set()
    exam_max = 0.0
    for module in modules:
        if not isinstance(module, dict):
            raise ValueError("Each module must have a valid configuration.")
        module_id = str(module.get("module_id", "")).strip()
        if not module_id or module_id in module_ids:
            raise ValueError("Every module must have a unique identifier.")
        module_ids.add(module_id)
        module_name = str(module.get("name", "")).strip()
        if not module_name:
            raise ValueError("Every module needs a name.")
        module_max = _positive_marks(
            module.get("max_marks"),
            f"{module_name} maximum marks",
        )
        exam_max += module_max

        questions = module.get("questions")
        if not isinstance(questions, list) or not questions:
            raise ValueError(f"Add at least one question to {module_name}.")
        groups = module.get("or_groups", [])
        if not isinstance(groups, list):
            raise ValueError(f"{module_name} has invalid OR alternatives.")
        group_by_id = {}
        for group in groups:
            group_id = str(group.get("group_id", "")).strip()
            if not group_id or group_id in group_by_id:
                raise ValueError(f"{module_name} has a duplicate OR group.")
            try:
                allowed_attempts = int(group.get("allowed_attempts"))
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"{module_name} OR groups need an attempt limit."
                ) from error
            if allowed_attempts < 1:
                raise ValueError(
                    f"{module_name} OR groups must allow at least one alternative."
                )
            group_by_id[group_id] = allowed_attempts

        question_ids = set()
        group_counts = {group_id: 0 for group_id in group_by_id}
        module_capacity = 0.0
        for question in questions:
            if not isinstance(question, dict):
                raise ValueError(f"{module_name} contains an invalid question.")
            question_id = str(question.get("question_id", "")).strip()
            if (
                not question_id
                or question_id in question_ids
                or question_id in target_ids
            ):
                raise ValueError("Every question needs a unique identifier.")
            question_ids.add(question_id)
            target_ids.add(question_id)
            question_label = str(question.get("label", "")).strip()
            if not question_label:
                raise ValueError(f"{module_name} contains an unlabeled question.")
            question_max = _positive_marks(
                question.get("max_marks"),
                f"{question_label} maximum marks",
            )
            group_id = question.get("or_group_id")
            if group_id:
                group_id = str(group_id)
                if group_id not in group_by_id:
                    raise ValueError(
                        f"{question_label} refers to an unknown OR group."
                    )
                if question.get("compulsory"):
                    raise ValueError(
                        f"{question_label} cannot be compulsory inside an OR group."
                    )
                group_counts[group_id] += 1
            else:
                module_capacity += question_max

            subquestions = question.get("subquestions", [])
            if not isinstance(subquestions, list):
                raise ValueError(f"{question_label} has invalid sub-questions.")
            if subquestions:
                child_ids = set()
                child_total = 0.0
                for subquestion in subquestions:
                    if not isinstance(subquestion, dict):
                        raise ValueError(
                            f"{question_label} contains an invalid sub-question."
                        )
                    child_id = str(subquestion.get("subquestion_id", "")).strip()
                    if (
                        not child_id
                        or child_id in child_ids
                        or child_id in target_ids
                    ):
                        raise ValueError(
                            f"{question_label} has a duplicate sub-question."
                        )
                    child_ids.add(child_id)
                    target_ids.add(child_id)
                    if not str(subquestion.get("label", "")).strip():
                        raise ValueError(
                            f"{question_label} has an unlabeled sub-question."
                        )
                    child_total += _positive_marks(
                        subquestion.get("max_marks"),
                        f"{subquestion['label']} maximum marks",
                    )
                if not math.isclose(child_total, question_max, abs_tol=0.01):
                    raise ValueError(
                        f"{question_label} marks must equal the sum of its "
                        "sub-question marks."
                    )

        for group_id, allowed_attempts in group_by_id.items():
            alternatives = [
                question
                for question in questions
                if question.get("or_group_id") == group_id
            ]
            if not alternatives:
                raise ValueError(f"An empty OR group exists in {module_name}.")
            _validate_or_group_consistency(
                module_name,
                group_id,
                alternatives,
            )
            if allowed_attempts > len(alternatives):
                raise ValueError(
                    f"{module_name} allows more OR alternatives than are configured."
                )
            module_capacity += sum(
                sorted(
                    (
                        float(question["max_marks"])
                        for question in alternatives
                    ),
                    reverse=True,
                )[:allowed_attempts]
            )

        if not math.isclose(module_capacity, module_max, abs_tol=0.01):
            raise ValueError(
                f"{module_name} can award {module_capacity:g} marks from its "
                f"questions and OR choices, but its maximum is {module_max:g}."
            )

    try:
        declared_total = float(total_marks)
    except (TypeError, ValueError) as error:
        raise ValueError("The exam maximum must be a positive number.") from error
    if (
        not math.isfinite(declared_total)
        or declared_total <= 0
        or not math.isclose(exam_max, declared_total, abs_tol=0.01)
    ):
        raise ValueError(
            f"Module marks total {exam_max:g}, but exam maximum is "
            f"{declared_total:g}."
        )
    return marking_scheme


def calculate_exam_result(marking_scheme, target_scores):
    module_results = []
    final_marks = 0.0
    resolved_alternatives = {}

    for module in marking_scheme["modules"]:
        for group in module.get("or_groups", []):
            alternatives = [
                question
                for question in module["questions"]
                if question.get("or_group_id") == group["group_id"]
            ]
            _validate_or_group_consistency(
                module.get("name", "Module"),
                group["group_id"],
                alternatives,
            )
        groups = {
            group["group_id"]: int(group["allowed_attempts"])
            for group in module.get("or_groups", [])
        }
        question_results = []
        grouped_questions = {}
        group_labels = {
            group["group_id"]: group.get("label", group["group_id"])
            for group in module.get("or_groups", [])
        }
        module_marks = 0.0

        for question in module["questions"]:
            subquestion_results = []
            subquestions = question.get("subquestions", [])
            scoring_items = subquestions or [question]
            for item in scoring_items:
                target_id = (
                    item["subquestion_id"] if subquestions
                    else question["question_id"]
                )
                target_score = target_scores.get(target_id, {})
                max_marks = float(item["max_marks"])
                attempted = bool(target_score.get("attempted", False))
                awarded_marks = 0.0
                if attempted:
                    try:
                        awarded_marks = float(target_score.get("awarded_marks", 0))
                    except (TypeError, ValueError) as error:
                        raise ValueError(
                            f"{item.get('label', question['label'])} has an invalid score."
                        ) from error
                    if not math.isfinite(awarded_marks):
                        raise ValueError("An awarded score must be finite.")
                    awarded_marks = max(0.0, min(max_marks, awarded_marks))
                detail = {
                    "target_id": target_id,
                    "question_no": item.get("label", question["label"]),
                    "max_marks": max_marks,
                    "awarded_marks": round(awarded_marks, 2),
                    "attempted": attempted,
                    "semantic_match_pct": target_score.get(
                        "semantic_match_pct",
                        0.0,
                    ),
                    "feedback": str(target_score.get("feedback", "")),
                }
                if subquestions:
                    subquestion_results.append(detail)

            question_marks = round(sum(
                item["awarded_marks"] for item in subquestion_results
            ), 2) if subquestions else (
                detail["awarded_marks"]
            )
            attempted_question = (
                any(item["attempted"] for item in subquestion_results)
                if subquestions
                else detail["attempted"]
            )
            question_result = {
                "question_id": question["question_id"],
                "question_no": question["label"],
                "max_marks": float(question["max_marks"]),
                "awarded_marks": question_marks,
                "attempted": attempted_question,
                "compulsory": bool(question.get("compulsory", False)),
                "or_group_id": question.get("or_group_id"),
                "counted_for_score": False,
                "subquestions": subquestion_results,
            }
            question_results.append(question_result)
            if question_result["or_group_id"]:
                grouped_questions.setdefault(
                    question_result["or_group_id"],
                    [],
                ).append(question_result)
            else:
                question_result["counted_for_score"] = True
                module_marks += question_marks

        for group_id, alternatives in grouped_questions.items():
            allowed = groups[group_id]
            attempted = [
                question for question in alternatives if question["attempted"]
            ]
            counted = sorted(
                attempted,
                key=lambda question: (
                    -question["awarded_marks"],
                    question["question_no"],
                ),
            )[:allowed]
            for question in counted:
                question["counted_for_score"] = True
                module_marks += question["awarded_marks"]

        or_group_results = []
        for group in module.get("or_groups", []):
            alternatives = grouped_questions.get(group["group_id"], [])
            counted = [
                question
                for question in alternatives
                if question["counted_for_score"]
            ]
            resolved_alternatives[group["group_id"]] = [
                question["question_id"] for question in counted
            ]
            or_group_results.append({
                "group_id": group["group_id"],
                "label": group_labels[group["group_id"]],
                "allowed_attempts": int(group["allowed_attempts"]),
                "max_marks": (
                    float(alternatives[0]["max_marks"])
                    if alternatives
                    else 0.0
                ),
                "awarded_marks": round(
                    sum(question["awarded_marks"] for question in counted),
                    2,
                ),
                "selected_alternatives": [
                    {
                        "question_id": question["question_id"],
                        "question_no": question["question_no"],
                        "awarded_marks": question["awarded_marks"],
                    }
                    for question in counted
                ],
            })

        module_marks = round(
            max(0.0, min(float(module["max_marks"]), module_marks)),
            2,
        )
        final_marks += module_marks
        module_results.append({
            "module_id": module["module_id"],
            "name": module["name"],
            "max_marks": float(module["max_marks"]),
            "awarded_marks": module_marks,
            "questions": question_results,
            "or_groups": or_group_results,
        })

    total_max = sum(float(module["max_marks"]) for module in marking_scheme["modules"])
    return {
        "modules": module_results,
        "final_marks": round(max(0.0, min(total_max, final_marks)), 2),
        "max_marks": total_max,
        "alternative_policy": "highest_scoring",
        "selected_alternatives": resolved_alternatives,
    }


def target_scores_from_result(result):
    scores = {}
    for module in result.get("modules", []):
        for question in module.get("questions", []):
            subquestions = question.get("subquestions", [])
            if subquestions:
                for subquestion in subquestions:
                    scores[subquestion["target_id"]] = {
                        "attempted": subquestion.get("attempted", False),
                        "awarded_marks": subquestion.get("awarded_marks", 0),
                        "semantic_match_pct": subquestion.get(
                            "semantic_match_pct",
                            0,
                        ),
                        "feedback": subquestion.get("feedback", ""),
                    }
            else:
                scores[question["question_id"]] = {
                    "attempted": question.get("attempted", False),
                    "awarded_marks": question.get("awarded_marks", 0),
                    "semantic_match_pct": question.get(
                        "semantic_match_pct",
                        0,
                    ),
                    "feedback": question.get("feedback", ""),
                }
    return scores
