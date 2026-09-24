import json

import pytest

from greenhouse_apply_assistant import (
    GreenhouseJob,
    build_application_plan,
    generate_application_plan,
)


def make_job(questions, **payload):
    body = {"id": 42, "title": "Engineer", "company_name": "Acme", **payload}
    return GreenhouseJob(
        board_token="acme",
        job_id=42,
        job_url="https://boards.greenhouse.io/acme/jobs/42",
        questions=tuple(questions),
        payload=body,
    )


def test_normalizes_questions_location_compliance_and_demographics_without_inputs():
    job = make_job(
        [
            {
                "label": "First Name",
                "required": True,
                "fields": [{"name": "first_name", "type": "input_text", "values": []}],
            },
            {
                "label": "Unknown required question",
                "required": True,
                "fields": [{
                    "name": "question_1",
                    "type": "multi_value_single_select",
                    "values": [{"label": "Yes", "value": 1}],
                }],
            },
            {
                "label": "Work authorization",
                "required": True,
                "fields": [{"name": "work_authorized_us", "type": "input_text", "values": []}],
            },
            {
                "label": "Optional question",
                "required": False,
                "fields": [{"name": "question_2", "type": "input_text", "values": []}],
            },
        ],
        location={"name": "San Francisco, CA"},
        offices=[{"id": 7, "name": "San Francisco, CA", "location": "San Francisco, CA"}],
        compliance=[{
            "type": "eeoc",
            "questions": [{
                "label": "Gender",
                "required": False,
                "fields": [{"name": "gender", "type": "multi_value_single_select", "values": [
                    {"label": "Decline", "value": 0},
                ]}],
            }],
        }],
        data_compliance=[{
            "type": "gdpr",
            "requires_consent": False,
            "requires_processing_consent": True,
            "requires_retention_consent": False,
            "retention_period": None,
            "demographic_data_consent_applies": False,
        }],
        demographic_questions=[{
            "label": "Demographic item",
            "required": False,
            "fields": [{"name": "demographic_1", "type": "input_text", "values": []}],
        }],
    )

    plan = build_application_plan(job)

    assert plan["status"] == "proposed"
    assert plan["job"]["location"]["name"] == "San Francisco, CA"
    assert plan["job"]["location"]["offices"][0]["id"] == 7
    assert plan["sections"]["compliance"]["data_policies"][0]["type"] == "gdpr"
    assert plan["sections"]["compliance"]["questions"][0]["answer_class"] == "manual"
    assert plan["sections"]["demographic"][0]["answer_class"] == "manual"
    first_name = plan["sections"]["application"][0]
    assert first_name["answer_class"] == "known_fact"
    assert first_name["source"] is None
    assert first_name["evidence"] is None
    assert first_name["proposed_value"] is None
    assert first_name["approval"] == "pending"
    assert first_name["verification"] == "not_attempted"
    assert {blocker["code"] for blocker in plan["blockers"]} == {
        "missing_local_fact", "required_manual_answer", "required_manual_consent"
    }
    assert sum(blocker["code"] == "missing_local_fact" for blocker in plan["blockers"]) == 2
    assert not any(blocker["field_id"].endswith("question_2") for blocker in plan["blockers"])


def test_required_cover_letter_has_explicit_blocker(tmp_path, monkeypatch):
    job = make_job([{
        "label": "Cover Letter",
        "required": True,
        "fields": [
            {"name": "cover_letter", "type": "input_file", "values": []},
            {"name": "cover_letter_text", "type": "textarea", "values": []},
        ],
    }])
    monkeypatch.setattr("greenhouse_apply_assistant.plan.fetch_greenhouse_job", lambda *_args, **_kwargs: job)

    plan, path = generate_application_plan(
        "https://boards.greenhouse.io/acme/jobs/42", output_dir=str(tmp_path)
    )

    assert path.name == "acme-42.json"
    assert json.loads(path.read_text())["sections"] == plan["sections"]
    assert plan["sections"]["application"][0]["answer_class"] == "unsupported"
    assert plan["blockers"] == [{
        "field_id": "application:cover_letter|cover_letter_text",
        "code": "required_unsupported_field",
        "message": "Required field has no approved supported answer source.",
    }]
    with pytest.raises(FileExistsError):
        generate_application_plan(
            "https://boards.greenhouse.io/acme/jobs/42", output_dir=str(tmp_path)
        )


def test_unsupported_required_control_remains_blocked():
    plan = build_application_plan(make_job([{
        "label": "Unsupported required control",
        "required": True,
        "fields": [{"name": "question_unsupported", "type": "input_date", "values": []}],
    }]))

    field = plan["sections"]["application"][0]
    assert field["answer_class"] == "unsupported"
    assert plan["blockers"] == [{
        "field_id": field["id"],
        "code": "required_unsupported_field",
        "message": "Required field has no approved supported answer source.",
    }]


def test_demographic_questions_official_object_shape_is_normalized():
    job = make_job(
        [],
        demographic_questions={
            "questions": [{
                "label": "Optional demographic question",
                "required": False,
                "fields": [{
                    "name": "demographic_1",
                    "type": "multi_value_single_select",
                    "values": [{"label": "Decline", "value": 0}],
                }],
            }],
        },
    )

    plan = build_application_plan(job)

    assert len(plan["sections"]["demographic"]) == 1
    field = plan["sections"]["demographic"][0]
    assert field["id"] == "demographic:demographic_1"
    assert field["answer_class"] == "manual"
    assert field["options"] == [{"label": "Decline", "value": 0}]
    assert plan["blockers"] == []


def test_required_location_questions_are_normalized_and_blocked():
    job = make_job(
        [],
        location_questions=[
            {
                "label": label,
                "required": True,
                "fields": [{"name": name, "type": field_type, "values": []}],
            }
            for label, name, field_type in (
                ("Longitude", "longitude", "input_hidden"),
                ("Latitude", "latitude", "input_hidden"),
                ("Location", "location", "input_text"),
            )
        ],
    )

    plan = build_application_plan(job)

    assert [field["id"] for field in plan["sections"]["location"]] == [
        "location:longitude", "location:latitude", "location:location"
    ]
    assert all(field["required"] for field in plan["sections"]["location"])
    assert [blocker["field_id"] for blocker in plan["blockers"]] == [
        "location:longitude", "location:latitude", "location:location"
    ]


def test_required_data_compliance_consent_flags_create_manual_blockers():
    job = make_job(
        [],
        data_compliance=[{
            "type": "gdpr",
            "requires_consent": True,
            "requires_processing_consent": False,
            "requires_retention_consent": None,
        }],
    )

    plan = build_application_plan(job)

    assert [blocker["field_id"] for blocker in plan["blockers"]] == [
        "compliance:data_policy:0:requires_consent",
        "compliance:data_policy:0:requires_retention_consent",
    ]
    assert all(blocker["code"] == "required_manual_consent" for blocker in plan["blockers"])
    assert all("human" in blocker["message"] for blocker in plan["blockers"])
