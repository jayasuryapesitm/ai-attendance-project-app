import logging

import numpy as np


FACE_MATCH_THRESHOLD = 0.45
FACE_MATCH_STRONG_THRESHOLD = 0.3375
FACE_MATCH_MIN_MARGIN = 0.05

logger = logging.getLogger(__name__)


def evaluate_face_match(encoding, model_data, candidate_student_ids=None):
    result = evaluate_face_match_details(
        encoding,
        model_data,
        candidate_student_ids,
    )
    student_id, best_distance, second_distance, rejection_reason, _, _ = result
    return student_id, best_distance, second_distance, rejection_reason


def evaluate_face_match_details(encoding, model_data, candidate_student_ids=None):
    if not isinstance(model_data, dict):
        result = _log_rejection('no_registered_profiles')
        return (*result, 'no_match', None)

    student_ids = model_data.get('student_ids', [])
    try:
        embeddings = np.asarray(model_data.get('embeddings'), dtype=np.float64)
        encoding = np.asarray(encoding, dtype=np.float64)
    except (TypeError, ValueError):
        result = _log_rejection('invalid_embedding_data')
        return (*result, 'no_match', None)

    if (
        encoding.ndim != 1
        or not np.isfinite(encoding).all()
        or embeddings.ndim != 2
        or embeddings.shape[0] != len(student_ids)
        or embeddings.shape[1] != encoding.shape[0]
        or not np.isfinite(embeddings).all()
    ):
        result = _log_rejection('invalid_embedding_data')
        return (*result, 'no_match', None)

    candidate_indices = list(range(len(student_ids)))
    if candidate_student_ids is not None:
        allowed_student_ids = set()
        for student_id in candidate_student_ids:
            try:
                allowed_student_ids.add(int(student_id))
            except (TypeError, ValueError, OverflowError):
                logger.warning("Ignoring invalid candidate student ID: %r", student_id)
        candidate_indices = [
            index
            for index in candidate_indices
            if int(student_ids[index]) in allowed_student_ids
        ]

    if not candidate_indices:
        result = _log_rejection('no_registered_candidates')
        return (*result, 'no_match', None)

    student_distances = {}
    student_pose_labels = {}
    for index in candidate_indices:
        try:
            student_id = int(student_ids[index])
        except (TypeError, ValueError, OverflowError):
            continue
        distance = float(np.linalg.norm(embeddings[index] - encoding))
        if not np.isfinite(distance):
            continue
        if student_id not in student_distances or distance < student_distances[student_id]:
            student_distances[student_id] = distance
            pose_labels = model_data.get('pose_labels', {})
            student_pose_labels[student_id] = (
                pose_labels.get(index) if isinstance(pose_labels, dict) else None
            )

    if not student_distances:
        result = _log_rejection('invalid_distance')
        return (*result, 'no_match', None)

    ranked = sorted(student_distances.items(), key=lambda item: item[1])
    best_student_id, best_distance = ranked[0]
    second_student_id = ranked[1][0] if len(ranked) > 1 else None
    second_distance = ranked[1][1] if len(ranked) > 1 else None
    pose_label = student_pose_labels.get(best_student_id)

    if best_distance > FACE_MATCH_THRESHOLD:
        rejection_reason = 'distance_above_threshold'
        matching_status = 'no_match'
        decision_student_id = None
    elif (
        second_distance is not None
        and second_distance - best_distance < FACE_MATCH_MIN_MARGIN
    ):
        rejection_reason = 'ambiguous_best_and_second_match'
        matching_status = 'borderline'
        decision_student_id = best_student_id
    elif best_distance > FACE_MATCH_STRONG_THRESHOLD:
        rejection_reason = 'borderline_distance'
        matching_status = 'borderline'
        decision_student_id = best_student_id
    else:
        rejection_reason = None
        matching_status = 'recognized'
        decision_student_id = best_student_id

    logger.info(
        "Face match decision=%s rejection_reason=%s best_student_id=%s "
        "best_distance=%.6f second_student_id=%s second_distance=%s "
        "threshold=%.3f minimum_margin=%.3f",
        matching_status,
        rejection_reason or "none",
        best_student_id,
        best_distance,
        second_student_id,
        f"{second_distance:.6f}" if second_distance is not None else "unavailable",
        FACE_MATCH_THRESHOLD,
        FACE_MATCH_MIN_MARGIN,
    )

    if matching_status == 'recognized':
        rejection_reason = None
    return (
        decision_student_id,
        best_distance,
        second_distance,
        rejection_reason,
        matching_status,
        pose_label,
    )


def _log_rejection(reason):
    logger.info(
        "Face match decision=rejected rejection_reason=%s best_student_id=None "
        "best_distance=unavailable second_student_id=None "
        "second_distance=unavailable threshold=%.3f minimum_margin=%.3f",
        reason,
        FACE_MATCH_THRESHOLD,
        FACE_MATCH_MIN_MARGIN,
    )
    return None, None, None, reason


def match_face_embeddings(encodings, model_data, candidate_student_ids=None):
    detected_students = {}
    matched_face_count = 0

    for encoding in encodings:
        student_id, _, _, _, status, _ = evaluate_face_match_details(
            encoding,
            model_data,
            candidate_student_ids,
        )
        if status == 'recognized' and student_id is not None:
            detected_students[student_id] = True
            matched_face_count += 1

    return detected_students, matched_face_count
