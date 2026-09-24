from linkedin_apply_assistant.criteria import classify_job
from linkedin_apply_assistant.models import Job, JobStatus


CRITERIA = {
    "target_min_base": 200000,
    "max_required_yoe": 5,
    "allowed_locations": ["Mountain View", "Palo Alto", "Sunnyvale"],
    "hybrid_allowed_locations": ["San Francisco"],
    "allowed_role_terms": ["software engineer", "backend", "infrastructure", "data platform"],
    "reject_role_terms": ["frontend engineer", "data scientist"],
    "hard_gap_terms": ["data science", "pytorch"],
    "preferred_company_terms": ["ai", "google", "linkedin"],
}

CONTEXT_RULES = {
    "degree_required": {
        "reject": True,
        "anchors": ["phd", "ph.d", "doctorate", "advanced degree"],
        "required_context": ["required", "requirement", "must have", "mandatory", "minimum requirement"],
        "soft_context": ["preferred", "nice to have", "bonus", "plus", "or phd"],
    },
    "kubernetes_required": {
        "reject": True,
        "anchors": ["kubernetes", "k8s"],
        "required_context": ["required", "must have", "production kubernetes"],
        "soft_context": ["preferred", "nice to have", "familiarity"],
    },
    "enterprise_it_ops_required": {
        "reject": True,
        "anchors": ["dicm", "itom", "itsm", "it service management"],
        "required_context": ["required", "required for the role"],
        "soft_context": ["preferred", "nice to have", "familiarity"],
        "reason": "required enterprise IT ops experience",
    },
}


def test_accepts_linkedin_infra_role():
    job = Job(
        job_id="1",
        title="Senior Software Engineer - Systems and Infrastructure",
        company="LinkedIn",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/1/",
        easy_apply=True,
        salary_text="$150,000 - $260,000",
        description="2+ years software engineering, distributed systems, backend APIs",
    )
    result = classify_job(job, CRITERIA, context_rules=CONTEXT_RULES)
    assert result.status == JobStatus.NEEDS_REVIEW
    assert result.estimated_tc == 205000


def test_rejects_non_easy_apply_by_default():
    job = Job(
        job_id="non-easy",
        title="Software Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/non-easy/",
        easy_apply=False,
        salary_text="$200k-$250k",
        description="Minimum Requirements 3+ years backend engineering.",
    )
    result = classify_job(job, CRITERIA)
    assert result.status == JobStatus.REJECTED
    assert "not Easy Apply" in result.reject_reason


def test_easy_apply_requirement_can_be_disabled():
    criteria = {
        **CRITERIA,
        "require_easy_apply": False,
    }
    job = Job(
        job_id="non-easy-ok",
        title="Software Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/non-easy-ok/",
        easy_apply=False,
        salary_text="$200k-$250k",
        description="Minimum Requirements 3+ years backend engineering.",
    )
    result = classify_job(job, criteria)
    assert result.status == JobStatus.NEEDS_REVIEW
    assert "not Easy Apply" not in result.reject_reason


def test_rejects_high_yoe():
    job = Job(
        job_id="2",
        title="Senior Backend Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/2/",
        easy_apply=True,
        description="8+ years production backend experience required",
    )
    result = classify_job(job, CRITERIA)
    assert result.status == JobStatus.REJECTED
    assert "hard YOE" in result.reject_reason


def test_yoe_range_with_plus_uses_lower_bound():
    job = Job(
        job_id="yoe-range-plus",
        title="Backend Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/yoe-range-plus/",
        easy_apply=True,
        salary_text="$200k-$250k",
        description="Minimum Requirements 2–12+ years of professional hands-on software development experience.",
    )
    result = classify_job(job, CRITERIA)
    assert result.status == JobStatus.NEEDS_REVIEW
    assert "hard YOE" not in result.reject_reason


def test_rejects_machine_learning_engineer_title():
    criteria = {
        **CRITERIA,
        "reject_role_terms": ["machine learning engineer"],
    }
    job = Job(
        job_id="ml-engineer",
        title="Principal Machine Learning Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/ml-engineer/",
        easy_apply=True,
        salary_text="$300k-$500k",
        description="Requirements Strong software engineering and ML systems background.",
    )
    result = classify_job(job, criteria)
    assert result.status == JobStatus.REJECTED
    assert "role mismatch: machine learning engineer" in result.reject_reason


def test_does_not_reject_preferred_phd_alternative():
    job = Job(
        job_id="preferred-phd",
        title="Software Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/preferred-phd/",
        easy_apply=True,
        salary_text="$200k-$250k",
        description=(
            "Preferred Qualifications BS and 5+ years of relevant work experience, "
            "MS and 4+ years of relevant work experience, or PhD and 2+ years of relevant work experience."
        ),
    )
    result = classify_job(job, CRITERIA, context_rules=CONTEXT_RULES)
    assert "phd" not in result.reject_reason.lower()


def test_rejects_required_phd():
    job = Job(
        job_id="required-phd",
        title="Software Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/required-phd/",
        easy_apply=True,
        salary_text="$200k-$250k",
        description="Minimum requirement: PhD in computer science or a related field.",
    )
    result = classify_job(job, CRITERIA, context_rules=CONTEXT_RULES)
    assert result.status == JobStatus.REJECTED
    assert "context rule: degree_required" in result.reject_reason


def test_context_rule_rejects_fuzzy_doctorate_requirement():
    job = Job(
        job_id="doctorate",
        title="Software Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/doctorate/",
        easy_apply=True,
        salary_text="$200k-$250k",
        description="Mandatory doctorate in computer science or related field.",
    )
    result = classify_job(job, CRITERIA, context_rules=CONTEXT_RULES)
    assert result.status == JobStatus.REJECTED
    assert "context rule: degree_required" in result.reject_reason


def test_context_rule_rejects_required_kubernetes():
    job = Job(
        job_id="kubernetes",
        title="Software Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/kubernetes/",
        easy_apply=True,
        salary_text="$200k-$250k",
        description="Must have production Kubernetes experience.",
    )
    result = classify_job(job, CRITERIA, context_rules=CONTEXT_RULES)
    assert result.status == JobStatus.REJECTED
    assert "context rule: kubernetes_required" in result.reject_reason


def test_context_rule_ignores_preferred_kubernetes():
    job = Job(
        job_id="preferred-kubernetes",
        title="Software Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/preferred-kubernetes/",
        easy_apply=True,
        salary_text="$200k-$250k",
        description="Kubernetes preferred, but not required.",
    )
    result = classify_job(job, CRITERIA, context_rules=CONTEXT_RULES)
    assert "kubernetes_required" not in result.reject_reason


def test_preferred_hard_gap_does_not_reject():
    job = Job(
        job_id="preferred-pytorch",
        title="Software Engineer",
        company="Example AI",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/preferred-pytorch/",
        easy_apply=True,
        salary_text="$200k-$250k",
        description=(
            "Basic Qualifications 2+ years backend experience with Java or Python. "
            "Preferred Qualifications Expertise in deep learning frameworks like PyTorch or TensorFlow."
        ),
    )
    result = classify_job(job, CRITERIA, context_rules=CONTEXT_RULES)
    assert result.status == JobStatus.NEEDS_REVIEW
    assert "hard skill gap" not in result.reject_reason
    assert "non-required gaps: pytorch" in result.fit_notes


def test_required_hard_gap_still_rejects():
    job = Job(
        job_id="required-pytorch",
        title="Software Engineer",
        company="Example AI",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/required-pytorch/",
        easy_apply=True,
        salary_text="$200k-$250k",
        description="Basic Qualifications 2+ years production PyTorch platform experience.",
    )
    result = classify_job(job, CRITERIA, context_rules=CONTEXT_RULES)
    assert result.status == JobStatus.REJECTED
    assert "hard skill gap: pytorch" in result.reject_reason


def test_rejects_required_enterprise_it_ops_gap():
    job = Job(
        job_id="it-ops",
        title="Backend Software Engineer - Platforms",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/it-ops/",
        easy_apply=True,
        salary_text="$200k-$250k",
        description=(
            "Minimum Qualifications Either DICM, ITOM, or ITSM experience required for the role. "
            "Preferred Qualifications 3 years software development experience with Python."
        ),
    )
    result = classify_job(job, CRITERIA, context_rules=CONTEXT_RULES)
    assert result.status == JobStatus.REJECTED
    assert "required enterprise IT ops experience" in result.reject_reason


def test_preferred_high_yoe_does_not_reject_when_required_is_in_range():
    job = Job(
        job_id="preferred-yoe",
        title="Software Engineer",
        company="Example AI",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/preferred-yoe/",
        easy_apply=True,
        salary_text="$200k-$250k",
        description=(
            "Basic Qualifications 3+ years backend engineering experience. "
            "Preferred Qualifications 8+ years building distributed platforms."
        ),
    )
    result = classify_job(job, CRITERIA, context_rules=CONTEXT_RULES)
    assert result.status == JobStatus.NEEDS_REVIEW
    assert "hard YOE" not in result.reject_reason


def test_accepts_yoe_range_by_lower_bound():
    job = Job(
        job_id="range",
        title="Software Engineer",
        company="Example AI",
        location="San Francisco, CA",
        url="https://www.linkedin.com/jobs/view/range/",
        easy_apply=True,
        salary_text="$180k–$250k base + equity",
        description="Hybrid role in San Francisco. 3–7 years backend experience.",
    )
    result = classify_job(job, CRITERIA)
    assert result.status == JobStatus.NEEDS_REVIEW
    assert result.estimated_tc == 215000


def test_ignores_decimal_tenure_for_yoe_requirement():
    job = Job(
        job_id="tenure",
        title="Backend Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/tenure/",
        easy_apply=True,
        salary_text="$200k-$350k",
        description="Median employee tenure: 2.9 years. 3+ years backend experience.",
    )
    result = classify_job(job, CRITERIA)
    assert result.status == JobStatus.NEEDS_REVIEW


def test_accepts_k_salary_range():
    job = Job(
        job_id="3",
        title="Backend Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/3/",
        easy_apply=True,
        salary_text="Salary Range / Rate: Base $200k-$350k + Bonus + Stock Options",
        description="2+ years backend",
    )
    result = classify_job(job, CRITERIA)
    assert result.status == JobStatus.NEEDS_REVIEW
    assert result.estimated_tc == 275000


def test_rejects_base_below_target():
    job = Job(
        job_id="low-base",
        title="Backend Engineer",
        company="Example",
        location="Mountain View, CA",
        url="https://www.linkedin.com/jobs/view/low-base/",
        easy_apply=True,
        salary_text="$150k-$190k",
        description="3+ years backend",
    )
    result = classify_job(job, CRITERIA)
    assert result.status == JobStatus.REJECTED
    assert "estimated base below target" in result.reject_reason


def test_accepts_farther_location_when_hybrid():
    job = Job(
        job_id="4",
        title="Backend Engineer",
        company="Example",
        location="San Francisco, CA",
        url="https://www.linkedin.com/jobs/view/4/",
        easy_apply=True,
        salary_text="$200k-$350k",
        description="Hybrid role. 3+ years backend platform experience.",
    )
    result = classify_job(job, CRITERIA)
    assert result.status == JobStatus.NEEDS_REVIEW


def test_rejects_farther_location_when_not_hybrid():
    job = Job(
        job_id="5",
        title="Backend Engineer",
        company="Example",
        location="San Francisco, CA",
        url="https://www.linkedin.com/jobs/view/5/",
        easy_apply=True,
        salary_text="$200k-$350k",
        description="Onsite role. 3+ years backend platform experience.",
    )
    result = classify_job(job, CRITERIA)
    assert result.status == JobStatus.REJECTED
    assert "location outside target band" in result.reject_reason
