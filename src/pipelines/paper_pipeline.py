import json
import logging
import math
import time
import uuid
from copy import deepcopy
from io import BytesIO

from PIL import Image, ImageOps

from src.database.config import get_vision_api_key, get_vision_model, supabase
from src.pipelines.exam_marking import calculate_exam_result, get_scoring_targets


logger = logging.getLogger(__name__)
PAPER_BUCKET = "exam-sheets"
MAX_IMAGE_WIDTH = 1200
TARGET_PAGE_BYTES = 250 * 1024
MAX_PDF_PAGES = 60
MAX_UPLOAD_BYTES = 30 * 1024 * 1024


def exam_storage_prefix(exam_id, purpose):
    if purpose not in {"blueprints", "question-papers", "submissions"}:
        raise ValueError("Unsupported exam document type.")
    return f"exams/{exam_id}/{purpose}"


def _encode_jpeg(image):
    image = ImageOps.exif_transpose(image).convert("RGB")
    if image.width > MAX_IMAGE_WIDTH:
        height = round(image.height * MAX_IMAGE_WIDTH / image.width)
        image = image.resize((MAX_IMAGE_WIDTH, height), Image.Resampling.LANCZOS)

    while True:
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=75, optimize=True)
        content = buffer.getvalue()
        if len(content) <= TARGET_PAGE_BYTES or image.width <= 480:
            return content
        image = image.resize(
            (max(480, round(image.width * 0.85)), max(1, round(image.height * 0.85))),
            Image.Resampling.LANCZOS,
        )


def compress_uploaded_pages(uploaded_file):
    """Convert an uploaded image or PDF to in-memory, compressed JPEG pages."""
    raw = uploaded_file.getvalue()
    if not raw:
        raise ValueError("The uploaded file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise ValueError("Each upload must be 30 MB or smaller.")

    filename = getattr(uploaded_file, "name", "")
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix == "pdf" or getattr(uploaded_file, "type", "") == "application/pdf":
        try:
            import pymupdf as pdf_engine
        except ImportError:
            try:
                import fitz as pdf_engine
            except ImportError as error:
                raise RuntimeError(
                    "PDF uploads require PyMuPDF in the Python environment "
                    "running Streamlit. Install it with "
                    "`python -m pip install PyMuPDF google-genai`, then restart "
                    "ClassLens.ai."
                ) from error
        pages = []
        with pdf_engine.open(stream=raw, filetype="pdf") as document:
            if len(document) > MAX_PDF_PAGES:
                raise ValueError(f"PDFs may contain at most {MAX_PDF_PAGES} pages.")
            for page in document:
                pixmap = page.get_pixmap(
                    matrix=pdf_engine.Matrix(1.5, 1.5),
                    alpha=False,
                )
                image = Image.open(BytesIO(pixmap.tobytes("png")))
                pages.append(_encode_jpeg(image))
        if not pages:
            raise ValueError("The PDF does not contain any pages.")
        return pages

    try:
        with Image.open(BytesIO(raw)) as image:
            return [_encode_jpeg(image)]
    except Exception as error:
        raise ValueError("Upload an image (PNG, JPEG, or WEBP) or a PDF.") from error


def upload_compressed_pages(uploaded_file, storage_prefix):
    return upload_page_images(compress_uploaded_pages(uploaded_file), storage_prefix)


def upload_page_images(pages, storage_prefix):
    paths = []
    try:
        for index, content in enumerate(pages, start=1):
            path = f"{storage_prefix}/{uuid.uuid4().hex}-page-{index:03d}.jpg"
            supabase.storage.from_(PAPER_BUCKET).upload(
                path,
                content,
                file_options={"content-type": "image/jpeg", "upsert": "false"},
            )
            paths.append(path)
    except Exception:
        if paths:
            try:
                remove_stored_pages(paths)
            except Exception:
                logger.exception("Could not clean up a partially uploaded paper")
        raise
    return paths


def remove_stored_pages(paths):
    if paths:
        supabase.storage.from_(PAPER_BUCKET).remove(list(paths))


def download_stored_pages(paths):
    return [
        supabase.storage.from_(PAPER_BUCKET).download(path)
        for path in paths
    ]


def encode_storage_paths(paths):
    return json.dumps(paths)


def decode_storage_paths(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        paths = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return [value]
    return paths if isinstance(paths, list) else [value]


def _call_vision_json(prompt, page_images):
    api_key = get_vision_api_key()
    if not api_key:
        raise RuntimeError(
            "Set GEMINI_API_KEY in the environment or Streamlit secrets to "
            "enable AI paper evaluation."
        )
    try:
        from google import genai
        from google.genai import types
    except ImportError as error:
        raise RuntimeError(
            "AI paper evaluation requires google-genai. Install the project "
            "requirements and restart ClassLens.ai."
        ) from error

    content = [prompt]
    for page in page_images:
        content.append(types.Part.from_bytes(data=page, mime_type="image/jpeg"))

    client = genai.Client(api_key=api_key)
    primary_model = get_vision_model()
    model_candidates = list(dict.fromkeys([
        primary_model,
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
    ]))

    last_error = None
    unavailable_models = []
    for model_name in model_candidates:
        model_succeeded = False
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=content,
                    config=types.GenerateContentConfig(
                        system_instruction=(
                            "You are a careful exam marker. Read the supplied pages, "
                            "follow the requested JSON schema, and never invent illegible "
                            "answers or questions."
                        ),
                        response_mime_type="application/json",
                        temperature=0,
                    ),
                )
                result = response.text
                model_succeeded = True
                break
            except Exception as error:
                last_error = error
                error_text = str(error)
                unavailable = (
                    "404" in error_text
                    or "NOT_FOUND" in error_text.upper()
                    or "is no longer available" in error_text.lower()
                )
                if unavailable:
                    unavailable_models.append(model_name)
                    logger.warning(
                        "Gemini model %s is unavailable; trying a fallback",
                        model_name,
                    )
                    break
                transient = (
                    "503" in error_text
                    or "UNAVAILABLE" in error_text
                    or "429" in error_text
                    or "RESOURCE_EXHAUSTED" in error_text
                )
                if not transient:
                    raise
                if attempt < 2:
                    time.sleep(2 ** attempt)
        if model_succeeded:
            break
    else:
        if unavailable_models:
            raise RuntimeError(
                "The configured Gemini model is unavailable. Tried "
                + ", ".join(unavailable_models)
                + ". Set GEMINI_MODEL to `gemini-3.5-flash-lite` in the "
                "environment or `.streamlit/secrets.toml`, then retry. "
                f"Last error: {last_error}"
            ) from last_error
        raise RuntimeError(
            "Gemini is temporarily unavailable or overloaded after all retry "
            f"attempts. Please wait a minute and try again. Last error: {last_error}"
        ) from last_error
    if not result:
        raise ValueError("The AI returned an empty evaluation.")
    try:
        return json.loads(result)
    except json.JSONDecodeError as error:
        raise ValueError("The AI returned invalid evaluation JSON.") from error


def create_blueprint_rubric(page_images, total_marks):
    response = _call_vision_json(
        "Read the blueprint answer key pages and create a grading rubric. "
        "Return a JSON object (not a top-level array) with a 'questions' array; "
        "each question must have "
        "'question_no' (string), 'max_marks' (number), and 'checkpoints' "
        "(array of concise, independently gradeable conceptual requirements). "
        f"The sum of all question max_marks must equal exactly {total_marks}. "
        "Include every question and sub-question shown. If a question's marks "
        "are not visible, allocate marks proportionally and still total exactly "
        f"{total_marks}.",
        page_images,
    )
    if isinstance(response, list):
        questions = response
    elif isinstance(response, dict):
        questions = response.get("questions")
    else:
        questions = None
    if not isinstance(questions, list) or not questions:
        raise ValueError("No questions could be extracted from the blueprint.")

    rubric = []
    for question in questions:
        try:
            max_marks = float(question["max_marks"])
            question_no = str(question["question_no"])
            checkpoints = question["checkpoints"]
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("The blueprint rubric has an invalid question.") from error
        cleaned_checkpoints = (
            [str(item).strip() for item in checkpoints if str(item).strip()]
            if isinstance(checkpoints, list)
            else []
        )
        if (
            not question_no.strip()
            or not math.isfinite(max_marks)
            or max_marks <= 0
            or not cleaned_checkpoints
        ):
            raise ValueError("The blueprint rubric contains invalid question marks.")
        rubric.append({
            "question_no": question_no,
            "max_marks": max_marks,
            "checkpoints": cleaned_checkpoints,
        })

    if len({question["question_no"] for question in rubric}) != len(rubric):
        raise ValueError("The blueprint contains duplicate question numbers.")
    if not math.isclose(sum(row["max_marks"] for row in rubric), total_marks, abs_tol=0.01):
        raise ValueError(
            "The extracted question marks do not add up to the exam total. "
            "Check the blueprint and total marks, then try again."
        )
    return {"questions": rubric}


def _read_mark(value, target_id, source_name):
    if value is None:
        return None
    try:
        marks = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"The extracted {source_name} marks for {target_id} are invalid."
        ) from error
    if not math.isfinite(marks) or marks < 0:
        raise ValueError(
            f"The extracted {source_name} marks for {target_id} are invalid."
        )
    return marks


def _manual_checkpoints(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not isinstance(value, str):
        return []
    return [
        item.strip(" \t-*")
        for item in value.replace(";", "\n").splitlines()
        if item.strip(" \t-*")
    ]


def extract_exam_rubric(blueprint_pages, question_paper_pages, marking_scheme):
    targets = get_scoring_targets(marking_scheme)
    prompt = (
        "Inspect the supplied exam documents. The first "
        f"{len(blueprint_pages)} image pages are the answer-key blueprint; "
        f"the next {len(question_paper_pages)} pages are the question paper. "
        "For each configured scoring item below, return its exact id, answer-key "
        "checkpoints, the marks visibly printed for it in the blueprint "
        "(blueprint_marks) and question paper (question_paper_marks). Use null "
        "for marks that are not clearly visible. Do not infer missing marks or "
        "invent checkpoints; use an empty checkpoint array when unclear. Also "
        "list any question/sub-question labels and module/section labels visible "
        "in either document that are not configured. Return a JSON object with "
        "'items', 'modules', 'unconfigured_questions', and "
        "'unconfigured_modules'.\nConfigured modules:\n"
        + json.dumps(
            [
                {
                    "id": module["module_id"],
                    "name": module["name"],
                    "configured_marks": module["max_marks"],
                }
                for module in marking_scheme.get("modules", [])
            ],
            ensure_ascii=False,
        )
        + "\nConfigured scoring items:\n"
        + json.dumps(
            [
                {
                    "id": target["target_id"],
                    "question_no": target["question_no"],
                    "configured_marks": target["max_marks"],
                }
                for target in targets
            ],
            ensure_ascii=False,
        )
    )
    response = _call_vision_json(
        prompt,
        list(blueprint_pages) + list(question_paper_pages),
    )
    if isinstance(response, list):
        extracted_items = response
        extracted_modules = []
        unconfigured_questions = []
        unconfigured_modules = []
    elif isinstance(response, dict):
        extracted_items = response.get("items", [])
        extracted_modules = response.get("modules", [])
        unconfigured_questions = response.get("unconfigured_questions", [])
        unconfigured_modules = response.get("unconfigured_modules", [])
    else:
        extracted_items = []
        extracted_modules = []
        unconfigured_questions = []
        unconfigured_modules = []
    if not isinstance(extracted_items, list):
        raise ValueError("The AI returned an invalid exam-structure analysis.")
    if not isinstance(extracted_modules, list):
        raise ValueError("The AI returned invalid module marks.")
    if not isinstance(unconfigured_questions, list):
        raise ValueError("The AI returned invalid unconfigured question labels.")
    if not isinstance(unconfigured_modules, list):
        raise ValueError("The AI returned invalid unconfigured module labels.")

    extracted_by_id = {}
    for item in extracted_items:
        if not isinstance(item, dict):
            raise ValueError("The AI returned an invalid exam-structure item.")
        target_id = str(item.get("id", "")).strip()
        if not target_id or target_id in extracted_by_id:
            raise ValueError("The AI returned duplicate or missing question IDs.")
        extracted_by_id[target_id] = item

    updated_scheme = deepcopy(marking_scheme)
    updated_targets = {}
    for module in updated_scheme.get("modules", []):
        for question in module.get("questions", []):
            scoring_items = question.get("subquestions", []) or [question]
            for item in scoring_items:
                target_id = item.get("subquestion_id") or item.get("question_id")
                updated_targets[target_id] = item
    report = {
        "items": [],
        "modules": [],
        "unconfigured_questions": [
            str(label).strip()
            for label in unconfigured_questions
            if str(label).strip()
        ],
        "unconfigured_modules": [
            str(label).strip()
            for label in unconfigured_modules
            if str(label).strip()
        ],
        "missing_rubric": [],
        "mark_mismatches": [],
        "module_mismatches": [],
    }
    extracted_modules_by_id = {}
    for module in extracted_modules:
        if not isinstance(module, dict):
            raise ValueError("The AI returned an invalid module structure.")
        module_id = str(module.get("id", "")).strip()
        if not module_id or module_id in extracted_modules_by_id:
            raise ValueError("The AI returned duplicate or missing module IDs.")
        extracted_modules_by_id[module_id] = module
    expected_module_ids = {
        module["module_id"] for module in updated_scheme["modules"]
    }
    for module in updated_scheme["modules"]:
        module_id = module["module_id"]
        extracted = extracted_modules_by_id.get(module_id, {})
        blueprint_marks = _read_mark(
            extracted.get("blueprint_marks"),
            module["name"],
            "blueprint module",
        )
        question_paper_marks = _read_mark(
            extracted.get("question_paper_marks"),
            module["name"],
            "question-paper module",
        )
        configured_marks = float(module["max_marks"])
        mismatches = [
            (source, marks)
            for source, marks in (
                ("blueprint", blueprint_marks),
                ("question paper", question_paper_marks),
            )
            if marks is not None
            and not math.isclose(marks, configured_marks, abs_tol=0.01)
        ]
        if mismatches:
            report["module_mismatches"].append({
                "module": module["name"],
                "configured_marks": configured_marks,
                "documents": mismatches,
            })
        report["modules"].append({
            "module": module["name"],
            "configured_marks": configured_marks,
            "blueprint_marks": blueprint_marks,
            "question_paper_marks": question_paper_marks,
        })
    extra_module_ids = set(extracted_modules_by_id) - expected_module_ids
    if extra_module_ids:
        report["unconfigured_modules"].extend(sorted(extra_module_ids))

    for target in targets:
        target_id = target["target_id"]
        extracted = extracted_by_id.get(target_id, {})
        blueprint_marks = _read_mark(
            extracted.get("blueprint_marks"),
            target["question_no"],
            "blueprint",
        )
        question_paper_marks = _read_mark(
            extracted.get("question_paper_marks"),
            target["question_no"],
            "question-paper",
        )
        configured_marks = float(target["max_marks"])
        mismatches = [
            (source, marks)
            for source, marks in (
                ("blueprint", blueprint_marks),
                ("question paper", question_paper_marks),
            )
            if marks is not None
            and not math.isclose(marks, configured_marks, abs_tol=0.01)
        ]
        if mismatches:
            report["mark_mismatches"].append({
                "question_no": target["question_no"],
                "configured_marks": configured_marks,
                "documents": mismatches,
            })

        extracted_checkpoints = extracted.get("checkpoints", [])
        if isinstance(extracted_checkpoints, list):
            extracted_checkpoints = _manual_checkpoints(extracted_checkpoints)
        else:
            extracted_checkpoints = []
        checkpoints = list(dict.fromkeys(
            extracted_checkpoints
            + _manual_checkpoints(target.get("rubric_notes"))
        ))
        if not checkpoints:
            checkpoints = list(dict.fromkeys(
                _manual_checkpoints(target.get("checkpoints"))
                + _manual_checkpoints(target.get("rubric_notes"))
            ))
        updated_targets[target_id]["checkpoints"] = checkpoints
        if not checkpoints:
            report["missing_rubric"].append(target["question_no"])
        report["items"].append({
            "target_id": target_id,
            "question_no": target["question_no"],
            "configured_marks": configured_marks,
            "blueprint_marks": blueprint_marks,
            "question_paper_marks": question_paper_marks,
        })

    expected_ids = set(updated_targets)
    extra_ids = set(extracted_by_id) - expected_ids
    if extra_ids:
        report["unconfigured_questions"].extend(sorted(extra_ids))
    return updated_scheme, report


def evaluate_answer_sheet(page_images, rubric):
    response = _call_vision_json(
        "Grade the student's handwritten or typed answers against this rubric. "
        "Treat paraphrases and other accurate conceptual equivalents as correct; "
        "do not require exact keywords. For each question, estimate the "
        "percentage of rubric checkpoint meaning accurately conveyed, from 0 "
        "to 100. At 85% or higher award full marks; below 85% award proportional "
        "partial marks (max_marks multiplied by semantic_match_pct / 100). "
        "Return a JSON object (not a top-level array) with a 'questions' array; "
        "each item must contain "
        "'question_no', 'max_marks', 'awarded_marks', 'semantic_match_pct', and "
        "'feedback'. Feedback should briefly state concepts covered and missed. "
        "If the answer is unreadable or absent, give 0 and explain that. "
        "Use exactly these rubric questions and marks:\n"
        + json.dumps(rubric, ensure_ascii=False),
        page_images,
    )
    if isinstance(response, list):
        response_questions = response
    elif isinstance(response, dict):
        response_questions = response.get("questions", [])
    else:
        response_questions = []
    if not isinstance(response_questions, list):
        raise ValueError("The AI returned an invalid evaluation question list.")
    rubric_by_number = {
        str(question["question_no"]): question
        for question in rubric.get("questions", [])
    }
    results = []
    for item in response_questions:
        question_no = str(item.get("question_no", ""))
        question_rubric = rubric_by_number.get(question_no)
        if question_rubric is None:
            continue
        try:
            match_pct = float(item["semantic_match_pct"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                f"The AI returned an invalid score for question {question_no}."
            ) from error
        if not math.isfinite(match_pct):
            raise ValueError(
                f"The AI returned an invalid score for question {question_no}."
            )
        match_pct = max(0.0, min(100.0, match_pct))
        max_marks = float(question_rubric["max_marks"])
        awarded_marks = (
            max_marks
            if match_pct >= 85
            else round(max_marks * match_pct / 100, 2)
        )
        results.append({
            "question_no": question_no,
            "max_marks": max_marks,
            "awarded_marks": awarded_marks,
            "semantic_match_pct": round(match_pct, 2),
            "feedback": str(item.get("feedback", "")),
        })
    if (
        len(results) != len(rubric_by_number)
        or {result["question_no"] for result in results} != set(rubric_by_number)
    ):
        raise ValueError("The AI evaluation did not return every rubric question.")
    return results


def evaluate_configured_exam(marking_scheme, page_images=None, text_answers=None):
    targets = get_scoring_targets(marking_scheme)
    if not targets:
        raise ValueError("This exam has no configured questions to evaluate.")

    text_answers = text_answers or {}
    if page_images is None:
        requested_targets = [
            target for target in targets
            if str(text_answers.get(target["target_id"], "")).strip()
        ]
    else:
        requested_targets = targets

    scores = {
        target["target_id"]: {
            "attempted": False,
            "awarded_marks": 0.0,
            "semantic_match_pct": 0.0,
            "feedback": "Question not attempted.",
        }
        for target in targets
    }
    if not requested_targets:
        return scores


    attempt_instruction = (
        "Each supplied text answer is attempted; return semantic_match_pct "
        "(0 to 100) and brief feedback for it."
        if page_images is None
        else
        "For every supplied id, return attempted (boolean), "
        "semantic_match_pct (0 to 100), and brief feedback. Mark an item "
        "attempted only when an answer to that exact sub-question is visible; "
        "do not treat an answer to another sub-question as an attempt. Give "
        "zero for absent or unreadable answers."
    )
    prompt = (
        "Evaluate each configured exam item independently against its answer-key "
        "checkpoints. Do not compare or transfer marks between items. "
        + attempt_instruction
        + " Return a JSON object with an 'items' array containing exactly these ids:\n"
        + json.dumps(
            [
                {
                    "id": target["target_id"],
                    "question_no": target["question_no"],
                    "max_marks": target["max_marks"],
                    "checkpoints": target["checkpoints"],
                    **(
                        {"student_answer": str(text_answers[target["target_id"]])}
                        if page_images is None
                        else {}
                    ),
                }
                for target in requested_targets
            ],
            ensure_ascii=False,
        )
    )
    response = _call_vision_json(prompt, page_images or [])
    if isinstance(response, list):
        response_items = response
    elif isinstance(response, dict):
        response_items = response.get("items", [])
    else:
        response_items = []
    if not isinstance(response_items, list):
        raise ValueError("The AI returned an invalid exam evaluation.")

    requested_by_id = {
        target["target_id"]: target for target in requested_targets
    }
    response_by_id = {}
    for item in response_items:
        if not isinstance(item, dict):
            raise ValueError("The AI returned an invalid exam score.")
        target_id = str(item.get("id", "")).strip()
        if target_id not in requested_by_id or target_id in response_by_id:
            raise ValueError("The AI returned unknown or duplicate exam question IDs.")
        response_by_id[target_id] = item
    if set(response_by_id) != set(requested_by_id):
        missing = sorted(set(requested_by_id) - set(response_by_id))
        raise ValueError(
            "The AI evaluation did not return every configured question: "
            + ", ".join(missing)
        )

    for target_id, item in response_by_id.items():
        target = requested_by_id[target_id]
        if page_images is None:
            attempted = True
        else:
            attempted = item.get("attempted")
            if not isinstance(attempted, bool):
                raise ValueError(
                    f"The AI returned an invalid attempt status for "
                    f"{target['question_no']}."
                )
        try:
            match_pct = float(item["semantic_match_pct"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                f"The AI returned an invalid score for {target['question_no']}."
            ) from error
        if not math.isfinite(match_pct):
            raise ValueError(
                f"The AI returned an invalid score for {target['question_no']}."
            )
        match_pct = max(0.0, min(100.0, match_pct)) if attempted else 0.0
        max_marks = float(target["max_marks"])
        awarded_marks = (
            round(max_marks * match_pct / 100, 2)
            if attempted
            else 0.0
        )
        scores[target_id] = {
            "attempted": attempted,
            "awarded_marks": awarded_marks,
            "semantic_match_pct": round(match_pct, 2),
            "feedback": str(item.get("feedback", "")),
        }
    return scores


def evaluate_exam_pages(exam, page_images):
    marking_scheme = exam.get("marking_scheme") or {}
    if marking_scheme.get("modules"):
        target_scores = evaluate_configured_exam(
            marking_scheme,
            page_images=page_images,
        )
        evaluation_result = calculate_exam_result(marking_scheme, target_scores)
        return evaluation_result["final_marks"], evaluation_result

    question_scores = evaluate_answer_sheet(
        page_images,
        exam["blueprint_rubric"],
    )
    ai_marks = round(
        sum(item["awarded_marks"] for item in question_scores),
        2,
    )
    return ai_marks, question_scores
