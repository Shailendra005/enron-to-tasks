import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import grader

ANSWER_PATH = Path(os.environ.get("ANSWER_PATH", "/app/answer.json"))
EXPECTED = json.loads((HERE / "expected.json").read_text())
CLUSTERS = json.loads((HERE / "clusters.json").read_text())


@pytest.fixture(scope="module")
def answer():
    return grader.load_answer(ANSWER_PATH)


def test_answer_file_and_schema(answer):
    assert grader.schema_ok(answer, EXPECTED)


@pytest.mark.parametrize("field", sorted(EXPECTED["fields"]))
def test_field(answer, field):
    assert grader.field_ok(answer, EXPECTED, field)


def test_evidence_citations(answer):
    assert grader.citations_ok(answer, EXPECTED, CLUSTERS)
