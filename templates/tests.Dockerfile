FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

COPY requirements.lock /opt/grade-lock/requirements.lock
RUN python3 -m venv /opt/grade-venv \
    && /opt/grade-venv/bin/python -m pip install --no-cache-dir --no-deps --require-hashes -r /opt/grade-lock/requirements.lock

RUN mkdir -p /app /logs/verifier

WORKDIR /tests
COPY test.sh test_outputs.py grader.py expected.json clusters.json /tests/
RUN chmod 755 /tests/test.sh
