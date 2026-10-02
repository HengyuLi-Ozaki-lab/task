"""The records of the GitHub rulesets on kyoshimi-develop (.github/rulesets/).

kyoshimi-develop.json is what the live ruleset must hold (the author applies it
with `gh api -X PUT`); its required checks must be exactly the workflow's jobs,
or a required check never reports and nothing can merge.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BRANCH = {"include": ["refs/heads/kyoshimi-develop"], "exclude": []}


def _ruleset(name: str) -> tuple[dict, dict]:
    data = json.loads((REPO / ".github" / "rulesets" / name).read_text())
    assert data["target"] == "branch" and data["conditions"]["ref_name"] == BRANCH
    return data, {rule["type"]: rule.get("parameters", {}) for rule in data["rules"]}


def _job_names() -> set[str]:
    workflow = (REPO / ".github" / "workflows" / "python-tests.yml").read_text()
    names = set(re.findall(r"^    name: (.+)$", workflow, re.M))
    matrix = "pytest (Python ${{ matrix.python-version }})"
    assert matrix in names
    versions = re.search(r"python-version: \[([^\]]+)\]", workflow).group(1)
    return (names - {matrix}) | {f"pytest (Python {v.strip().strip(chr(39))})" for v in versions.split(",")}


def test_the_live_ruleset_has_no_bypass_and_requires_exactly_the_workflows_jobs():
    data, rules = _ruleset("kyoshimi-develop.json")
    assert data["enforcement"] == "active" and data["bypass_actors"] == []
    assert set(rules) == {"deletion", "non_fast_forward", "pull_request", "required_status_checks"}
    assert rules["pull_request"]["allowed_merge_methods"] == ["merge"]
    # GitHub's default for this flag is true, and it blocks a merge with no reviewer to ask.
    assert rules["pull_request"]["require_extra_approval_for_unattributed_changes"] is False
    assert rules["pull_request"]["required_reviewers"] == []
    required = {check["context"] for check in rules["required_status_checks"]["required_status_checks"]}
    assert required == _job_names()
    assert len(required) >= 3


def test_the_review_ruleset_is_a_record_for_later_and_is_not_in_force():
    data, rules = _ruleset("kyoshimi-develop-review.json")
    assert data["enforcement"] == "disabled"        # AI sessions share the author's account: nobody could approve
    assert set(rules) == {"pull_request"}
    assert rules["pull_request"]["required_approving_review_count"] == 1
    assert rules["pull_request"]["allowed_merge_methods"] == ["merge"]
