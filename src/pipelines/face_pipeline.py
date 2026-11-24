

import logging

import dlib
import numpy as np
import face_recognition_models
from PIL import Image
import streamlit as st

from src.database.db import get_all_students
from src.pipelines.face_matching import (
    FACE_MATCH_THRESHOLD,
    evaluate_face_match,
    match_face_embeddings,
)


FACE_EMBEDDING_SIZE = 128
logger = logging.getLogger(__name__)


@st.cache_resource
def load_dlib_models():
    detector = dlib.get_frontal_face_detector() 


    sp = dlib.shape_predictor(
        face_recognition_models.pose_predictor_model_location()
    )

    facerec = dlib.face_recognition_model_v1(
        face_recognition_models.face_recognition_model_location()
    )

    return detector, sp, facerec


def get_face_embeddings(image_np, expected_face_count=0):
    detector, sp, facerec = load_dlib_models()
    height, width = image_np.shape[:2]
    max_dimension = max(height, width)
    if max_dimension > 1600:
        scale = 1600 / max_dimension
        image_np = np.asarray(
            Image.fromarray(image_np).resize(
                (int(width * scale), int(height * scale)),
                Image.BOX,
            )
        )

    faces = detector(image_np, 1)
    if expected_face_count and len(faces) < expected_face_count:
        higher_resolution_faces = detector(image_np, 2)
        if len(higher_resolution_faces) > len(faces):
            faces = higher_resolution_faces

    encodings= []

    for face in faces:
        shape = sp(image_np, face)
        face_descriptor = facerec.compute_face_descriptor(image_np, shape, 0)

        encodings.append(np.array(face_descriptor))
    return encodings


def detect_face_boxes(image_np):
    detector, _, _ = load_dlib_models()
    height, width = image_np.shape[:2]
    scale_x = scale_y = 1.0
    detection_image = image_np
    max_dimension = max(height, width)
    if max_dimension > 1600:
        detection_width = int(width * 1600 / max_dimension)
        detection_height = int(height * 1600 / max_dimension)
        detection_image = np.asarray(
            Image.fromarray(image_np).resize(
                (detection_width, detection_height),
                Image.BOX,
            )
        )
        scale_x = width / detection_width
        scale_y = height / detection_height

    boxes = []
    for face in detector(detection_image, 1):
        left = max(0, min(width, round(face.left() * scale_x)))
        top = max(0, min(height, round(face.top() * scale_y)))
        right = max(0, min(width, round(face.right() * scale_x)))
        bottom = max(0, min(height, round(face.bottom() * scale_y)))
        if right > left and bottom > top:
            boxes.append((left, top, right, bottom))
    return boxes


@st.cache_resource
def get_trained_model():
    students = get_all_students()

    if not students:
        return None

    students_by_id = {}
    duplicate_student_ids = set()
    for student in students:
        if not isinstance(student, dict):
            logger.warning("Skipping a face profile without a valid student row.")
            continue
        try:
            student_id = int(student.get('student_id'))
        except (TypeError, ValueError, OverflowError):
            logger.warning("Skipping a face profile with an invalid student ID.")
            continue
        if student_id <= 0:
            logger.warning("Skipping a face profile with an invalid student ID.")
            continue
        if student_id in students_by_id:
            duplicate_student_ids.add(student_id)
        else:
            students_by_id[student_id] = student

    for student_id in duplicate_student_ids:
        logger.error(
            "Excluding duplicate face profiles for student_id=%s.",
            student_id,
        )
        students_by_id.pop(student_id, None)

    embeddings = []
    student_ids = []
    valid_students_by_id = {}

    for student_id, student in students_by_id.items():
        if not isinstance(student.get('name'), str) or not student['name'].strip():
            logger.warning(
                "Skipping face profile without a valid name, student_id=%s.",
                student_id,
            )
            continue
        try:
            embedding = np.asarray(
                student.get('face_embedding'),
                dtype=np.float64,
            )
        except (TypeError, ValueError):
            logger.warning(
                "Skipping malformed face embedding, student_id=%s.",
                student_id,
            )
            continue
        if (
            embedding.shape != (FACE_EMBEDDING_SIZE,)
            or not np.isfinite(embedding).all()
        ):
            logger.warning(
                "Skipping invalid face embedding, student_id=%s.",
                student_id,
            )
            continue

        embeddings.append(embedding)
        student_ids.append(student_id)
        valid_student = dict(student)
        valid_student['student_id'] = student_id
        valid_students_by_id[student_id] = valid_student

    if not embeddings:
        return None

    return {
        'embeddings': np.vstack(embeddings),
        'student_ids': student_ids,
        'students_by_id': valid_students_by_id,
    }


def train_classifier():
    get_trained_model.clear()
    model_data = get_trained_model()
    return bool(model_data)

def predict_attendance(
    class_image_np,
    candidate_student_ids=None,
    expected_face_count=0,
):
    encodings = get_face_embeddings(class_image_np, expected_face_count)
    model_data = get_trained_model()

    if not model_data:
        detected_student, matched_face_count = match_face_embeddings(
            encodings,
            None,
            candidate_student_ids,
        )
        return (
            detected_student,
            len(encodings),
            len(encodings) - matched_face_count,
        )

    detected_student, matched_face_count = match_face_embeddings(
        encodings,
        model_data,
        candidate_student_ids,
    )
    return (
        detected_student,
        len(encodings),
        len(encodings) - matched_face_count,
    )


def identify_student(image_np):
    encodings = get_face_embeddings(image_np)
    if len(encodings) != 1:
        logger.info(
            "Face identification rejected rejection_reason=expected_one_face "
            "detected_face_count=%s",
            len(encodings),
        )
        return None, len(encodings)

    model_data = get_trained_model()
    if not model_data:
        evaluate_face_match(encodings[0], None)
        return None, len(encodings)

    student_id, _, _, _ = evaluate_face_match(encodings[0], model_data)
    if student_id is None:
        return None, len(encodings)

    student = model_data['students_by_id'].get(student_id)
    if student is None:
        logger.error(
            "Matched student_id=%s has no associated student record.",
            student_id,
        )
        return None, len(encodings)
    return student, len(encodings)


def measure_face_match(image_np, saved_embedding):
    encodings = get_face_embeddings(image_np)
    if len(encodings) != 1:
        logger.info(
            "Claimed face profile match rejected "
            "rejection_reason=expected_one_face detected_face_count=%s",
            len(encodings),
        )
        return None, len(encodings)

    try:
        saved_embedding = np.asarray(saved_embedding, dtype=np.float64)
    except (TypeError, ValueError):
        logger.warning("Rejecting malformed saved face embedding.")
        return None, len(encodings)
    if (
        saved_embedding.shape != (FACE_EMBEDDING_SIZE,)
        or not np.isfinite(saved_embedding).all()
    ):
        logger.warning("Rejecting invalid saved face embedding.")
        return None, len(encodings)

    distance = float(np.linalg.norm(saved_embedding - encodings[0]))
    rejection_reason = (
        'distance_above_threshold'
        if not np.isfinite(distance) or distance > FACE_MATCH_THRESHOLD
        else 'none'
    )
    logger.info(
        "Claimed face profile match rejection_reason=%s distance=%s "
        "threshold=%.3f",
        rejection_reason,
        f"{distance:.6f}" if np.isfinite(distance) else "unavailable",
        FACE_MATCH_THRESHOLD,
    )
    return distance, len(encodings)
