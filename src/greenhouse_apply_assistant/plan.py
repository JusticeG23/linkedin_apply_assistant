"""Create local, reviewable Greenhouse application plans from public job data."""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .client import GreenhouseJob, InvalidResponseError, fetch_greenhouse_job


_KNOWN_FACTS = {
    "first_name": "first_name",
    "last_name": "last_name",
    "email": "email",
    "phone": "phone",
    "location": "location",
    "work_authorized_us": "work_authorized_us",
    "needs_sponsorship": "needs_sponsorship",
}


def _controls(question: Dict[str, Any], source: str) -> List[Dict[str, Any]]:
    controls = question.get("fields")
    if not isinstance(controls, list) or not controls:
        raise InvalidResponseError(f"{source} must contain one or more fields")

    normalized = []
    for index, control in enumerate(controls):
        control_source = f"{source}.fields[{index}]"
        if not isinstance(control, dict):
            raise InvalidResponseError(f"{control_source} must be an object")
        values = control.get("values", [])
        if not isinstance(values, list):
            raise InvalidResponseError(f"{control_source}.values must be an array")
        options = []
        for option in values:
            if not isinstance(option, dict) or "label" not in option or "value" not in option:
                raise InvalidResponseError(f"{control_source}.values contains an invalid option")
            options.append({"label": option["label"], "value": option["value"]})
        name = control.get("name")
        field_type = control.get("type")
        if not isinstance(name, str) or not isinstance(field_type, str):
            raise InvalidResponseError(f"{control_source} must include string name and type")
        normalized.append({"name": name, "type": field_type, "options": options})
    return normalized


def _answer_class(section: str, controls: List[Dict[str, Any]]) -> str:
    if section in {"compliance", "demographic"}:
        return "manual"
    names = {control["name"].removesuffix("[]") for control in controls}
    types = {control["type"] for control in controls}
    if len(names) == 1 and next(iter(names)) in _KNOWN_FACTS:
        return "known_fact"
    if any("cover_letter" in name for name in names):
        return "unsupported"
    if any(field_type not in {
        "input_text", "textarea", "input_file", "multi_value_single_select",
        "multi_value_multi_select", "input_checkbox", "input_hidden",
    } for field_type in types):
        return "unsupported"
    return "manual"


def _normalize_questions(
    questions: Any, section: str, source_prefix: str
) -> List[Dict[str, Any]]:
    if not isinstance(questions, (list, tuple)):
        raise InvalidResponseError(f"{source_prefix} must be an array")
    normalized = []
    for index, question in enumerate(questions):
        source = f"{source_prefix}[{index}]"
        if not isinstance(question, dict):
            raise InvalidResponseError(f"{source} must be an object")
        required = question.get("required")
        if not isinstance(required, bool):
            raise InvalidResponseError(f"{source}.required must be a boolean")
        label = question.get("label")
        if not isinstance(label, str):
            raise InvalidResponseError(f"{source}.label must be a string")
        controls = _controls(question, source)
        names = [control["name"] for control in controls]
        answer_class = _answer_class(section, controls)
        entry = {
            "id": f"{section}:{'|'.join(names)}",
            "section": section,
            "label": label,
            "description": question.get("description"),
            "fields": controls,
            "options": controls[0]["options"] if len(controls) == 1 else [],
            "required": required,
            "answer_class": answer_class,
            "api_source": source,
            "source": None,
            "evidence": None,
            "proposed_value": None,
            "approval": "pending",
            "verification": "not_attempted",
        }
        normalized.append(entry)
    return normalized


def _blockers(fields: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    blockers = []
    for field in fields:
        if not field["required"] or field["proposed_value"] is not None:
            continue
        if field["answer_class"] == "known_fact":
            code = "missing_local_fact"
            message = "Required local applicant fact was not provided."
        elif field["answer_class"] == "manual":
            code = "required_manual_answer"
            message = "Required user-specific answer needs human input."
        else:
            code = "required_unsupported_field"
            message = "Required field has no approved supported answer source."
        blockers.append({"field_id": field["id"], "code": code, "message": message})
    return blockers


def _data_compliance_blockers(policies: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Require human review for consent flags not explicitly disabled by API."""
    blockers = []
    consent_flags = (
        "requires_consent",
        "requires_processing_consent",
        "requires_retention_consent",
    )
    for index, policy in enumerate(policies):
        for flag in consent_flags:
            if policy.get(flag) is False:
                continue
            blockers.append({
                "field_id": f"compliance:data_policy:{index}:{flag}",
                "code": "required_manual_consent",
                "message": "Consent decision requires explicit human review.",
            })
    return blockers


def build_application_plan(job: GreenhouseJob) -> Dict[str, Any]:
    """Normalize API questions without reading applicant or resume files."""
    application = _normalize_questions(job.questions, "application", "questions")
    raw_compliance = job.payload.get("compliance", [])
    if not isinstance(raw_compliance, list):
        raise InvalidResponseError("compliance must be an array")
    compliance = []
    for index, section in enumerate(raw_compliance):
        source = f"compliance[{index}]"
        if not isinstance(section, dict):
            raise InvalidResponseError(f"{source} must be an object")
        group_type = section.get("type", "unknown")
        questions = _normalize_questions(
            section.get("questions", []), "compliance", f"{source}.questions"
        )
        for field in questions:
            field["id"] = f"compliance:{group_type}:{field['id'].split(':', 1)[1]}"
            field["compliance_type"] = group_type
        compliance.extend(questions)

    raw_demographic = job.payload.get("demographic_questions") or []
    if isinstance(raw_demographic, dict):
        raw_demographic = raw_demographic.get("questions", [])
    demographic = _normalize_questions(
        raw_demographic,
        "demographic",
        "demographic_questions",
    )
    for field in demographic:
        field["id"] = f"demographic:{field['id'].split(':', 1)[1]}"

    location_questions = _normalize_questions(
        job.payload.get("location_questions") or [],
        "location",
        "location_questions",
    )

    location = job.payload.get("location")
    if location is not None and not isinstance(location, dict):
        raise InvalidResponseError("location must be an object or null")
    offices = job.payload.get("offices", [])
    if not isinstance(offices, list):
        raise InvalidResponseError("offices must be an array")
    normalized_offices = []
    for index, office in enumerate(offices):
        if not isinstance(office, dict):
            raise InvalidResponseError(f"offices[{index}] must be an object")
        normalized_offices.append({
            key: office[key] for key in ("id", "name", "location") if key in office
        })

    compliance_policy = []
    raw_data_compliance = job.payload.get("data_compliance", [])
    if not isinstance(raw_data_compliance, list):
        raise InvalidResponseError("data_compliance must be an array")
    for policy in raw_data_compliance:
        if not isinstance(policy, dict):
            raise InvalidResponseError("data_compliance entries must be objects")
        compliance_policy.append({
            key: policy.get(key)
            for key in (
                "type", "requires_consent", "requires_processing_consent",
                "requires_retention_consent", "retention_period",
                "demographic_data_consent_applies",
            )
        })

    fields = application + compliance + demographic + location_questions
    title = job.payload.get("title")
    company = job.payload.get("company_name")
    return {
        "schema_version": 1,
        "status": "proposed",
        "job": {
            "url": job.job_url,
            "board_token": job.board_token,
            "job_id": job.job_id,
            "title": title,
            "company": company,
            "location": {
                "name": location.get("name") if location else None,
                "offices": normalized_offices,
                "api_source": "job.location and offices",
            },
        },
        "inputs": {
            "applicant_profile": None,
            "resume_md": None,
            "resume_pdf": None,
        },
        "sections": {
            "application": application,
            "compliance": {
                "data_policies": compliance_policy,
                "questions": compliance,
            },
            "demographic": demographic,
            "location": location_questions,
        },
        "blockers": _blockers(fields) + _data_compliance_blockers(compliance_policy),
    }


def generate_application_plan(
    job_url: str,
    output_dir: str = "data/greenhouse-plans",
    timeout: float = 10.0,
) -> Tuple[Dict[str, Any], Path]:
    """Fetch public job data and create a non-overwriting local JSON plan."""
    job = fetch_greenhouse_job(job_url, timeout=timeout)
    plan = build_application_plan(job)
    path = Path(output_dir) / f"{job.board_token}-{job.job_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        json.dump(plan, output, ensure_ascii=False, indent=2)
        output.write("\n")
    return plan, path
