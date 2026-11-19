"""The records of the GitHub rulesets on kyoshimi-develop (.github/rulesets/).

kyoshimi-develop.json is what the live ruleset must hold (the author applies it
with `gh api -X PUT`); its required checks must be exactly the workflow's jobs,
or a required check never reports and nothing can merge.
"""
from __future__ import annotations

import itertools
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BRANCH = {"include": ["refs/heads/kyoshimi-develop"], "exclude": []}


def _ruleset(name: str) -> tuple[dict, dict]:
    data = json.loads((REPO / ".github" / "rulesets" / name).read_text())
    assert data["target"] == "branch" and data["conditions"]["ref_name"] == BRANCH
    return data, {rule["type"]: rule.get("parameters", {}) for rule in data["rules"]}


def _job_names(workflow: str | None = None) -> set[str]:
    """The status-check name of every job of the workflow: its `name:`, or its id when it has none, with
    `${{ matrix.<key> }}` expanded over that job's own `<key>: [..]` list. A shape this does not understand
    fails the test instead of being skipped."""
    if workflow is None:
        workflow = (REPO / ".github" / "workflows" / "python-tests.yml").read_text()
    names: set[str] = set()
    jobs = re.split(r"^jobs:\s*$", workflow, maxsplit=1, flags=re.M)[1]
    for line in re.findall(r"^  [^\s#].*$", jobs, re.M):          # the job ids, and nothing else, sit at this indent
        assert re.fullmatch(r"  [\w-]+:\s*", line), f"a job line this test cannot read: {line!r}"
    for block in re.split(r"^  (?=[\w-]+:\s*$)", jobs, flags=re.M)[1:]:
        job_id = block.split(":", 1)[0]
        assert not re.search(r"^\s+(include|exclude):", block, re.M), \
            f"job {job_id}: a matrix with include/exclude, which this test cannot expand"
        found = re.search(r"^    name: (.+)$", block, re.M)
        name = found.group(1).strip().strip("'\"") if found else job_id
        keys = re.findall(r"\$\{\{\s*matrix\.([\w-]+)\s*\}\}", name)
        assert "${{" not in re.sub(r"\$\{\{\s*matrix\.[\w-]+\s*\}\}", "", name), \
            f"job {job_id}: the check name {name!r} has an expression this test cannot expand"
        lists = []
        for key in keys:
            values = re.search(rf"^\s+{re.escape(key)}: \[([^\]]+)\]\s*$", block, re.M)
            assert values, f"job {job_id}: no `{key}: [...]` list to expand {name!r}"
            lists.append([v.strip().strip("'\"") for v in values.group(1).split(",")])
        for combo in itertools.product(*lists):
            check = name
            for key, value in zip(keys, combo):
                check = re.sub(r"\$\{\{\s*matrix\." + re.escape(key) + r"\s*\}\}", value, check)
            names.add(check)
    return names


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


WORKFLOW = """name: x
jobs:
  plain:
    name: a plain job
    runs-on: ubuntu-latest
  unnamed:
    runs-on: ubuntu-latest
  matrix:
    name: tests (Python ${{ matrix.python-version }}, ${{ matrix.os }})
    strategy:
      matrix:
        python-version: ['3.11', "3.13"]
        os: [linux]
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
"""


def test_the_job_names_are_read_as_github_names_the_checks():
    assert _job_names(WORKFLOW) == {"a plain job", "unnamed", "tests (Python 3.11, linux)", "tests (Python 3.13, linux)"}


def test_a_workflow_shape_the_reader_does_not_understand_fails_instead_of_passing():
    matrix = "  m:\n    name: t ${{ matrix.v }}\n    strategy:\n      matrix:\n        v: [1, 2]\n"
    static = "  s:\n    name: static\n    strategy:\n      matrix:\n        v: [1]\n        include:\n          - v: 2\n"
    for bad in (matrix + "        exclude:\n          - v: 2\n", matrix + "        include:\n          - v: 3\n", static,
                "  'quoted':\n    name: q\n", "  odd: # a comment after the id\n    name: q\n", "  - dash\n"):
        try:
            _job_names("jobs:\n" + bad)
        except AssertionError:
            continue
        raise AssertionError(f"{bad!r} was accepted")


def test_a_check_name_the_reader_cannot_expand_fails_instead_of_passing():
    for bad in ("    name: ${{ github.event_name }} job\n", "    name: tests ${{ matrix.missing }}\n"):
        try:
            _job_names("jobs:\n  odd:\n" + bad)
        except AssertionError:
            continue
        raise AssertionError(f"{bad!r} was accepted")
