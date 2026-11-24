import logging

import numpy as np


FACE_MATCH_THRESHOLD = 0.45
FACE_MATCH_MIN_MARGIN = 0.05

logger = logging.getLogger(__name__)


def evaluate_face_match(encoding, model_data, candidate_student_ids=None):
    if not isinstance(model_data, dict):
        return _log_rejection('no_registered_profiles')

    student_ids = model_data.get('student_ids', [])
    try:
        embeddings = np.asarray(model_data.get('embeddings'), dtype=np.float64)
        encoding = np.asarray(encoding, dtype=np.float64)
    except (TypeError, ValueError):
        return _log_rejection('invalid_embedding_data')

    if (
        encoding.ndim != 1
        or not np.isfinite(encoding).all()
        or embeddings.ndim != 2
        or embeddings.shape[0] != len(student_ids)
        or embeddings.shape[1] != encoding.shape[0]
        or not np.isfinite(embeddings).all()
    ):
        return _log_rejection('invalid_embedding_data')

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
        return _log_rejection('no_registered_candidates')

    distances = np.linalg.norm(embeddings[candidate_indices] - encoding, axis=1)
    finite_indices = [
        index for index, distance in enumerate(distances) if np.isfinite(distance)
    ]
    if not finite_indices:
        return _log_rejection('invalid_distance')

    ranked_indices = sorted(finite_indices, key=lambda index: distances[index])
    best_rank = ranked_indices[0]
    best_index = candidate_indices[best_rank]
    best_student_id = int(student_ids[best_index])
    best_distance = float(distances[best_rank])

    second_student_id = None
    second_distance = None
    if len(ranked_indices) > 1:
        second_rank = ranked_indices[1]
        second_index = candidate_indices[second_rank]
        second_student_id = int(student_ids[second_index])
        second_distance = float(distances[second_rank])

    if best_distance > FACE_MATCH_THRESHOLD:
        rejection_reason = 'distance_above_threshold'
    elif (
        second_distance is not None
        and second_distance - best_distance < FACE_MATCH_MIN_MARGIN
    ):
        rejection_reason = 'ambiguous_best_and_second_match'
    else:
        rejection_reason = None

    logger.info(
        "Face match decision=%s rejection_reason=%s best_student_id=%s "
        "best_distance=%.6f second_student_id=%s second_distance=%s "
        "threshold=%.3f minimum_margin=%.3f",
        "accepted" if rejection_reason is None else "rejected",
        rejection_reason or "none",
        best_student_id,
        best_distance,
        second_student_id,
        (
            f"{second_distance:.6f}"
            if second_distance is not None
            else "unavailable"
        ),
        FACE_MATCH_THRESHOLD,
        FACE_MATCH_MIN_MARGIN,
    )

    if rejection_reason is not None:
        return None, best_distance, second_distance, rejection_reason
    return best_student_id, best_distance, second_distance, None


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
        student_id, _, _, _ = evaluate_face_match(
            encoding,
            model_data,
            candidate_student_ids,
        )
        if student_id is not None:
            detected_students[student_id] = True
            matched_face_count += 1

    return detected_students, matched_face_count
