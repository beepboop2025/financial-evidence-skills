FROM python:3.13-slim@sha256:ffb752e139c0a19692a43af8d8523b274222dd68eebad5d583b45c2201c6e30a AS build
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY integrations/openbb/requirements.lock ./requirements.lock
RUN python -m pip download --disable-pip-version-check --only-binary=:all: --require-hashes --dest /wheels -r requirements.lock \
    && python -m pip wheel --disable-pip-version-check --no-deps --wheel-dir /wheels .

FROM python:3.13-slim@sha256:ffb752e139c0a19692a43af8d8523b274222dd68eebad5d583b45c2201c6e30a
ARG SOURCE_COMMIT
LABEL org.opencontainers.image.source="https://github.com/beepboop2025/financial-evidence-skills" org.opencontainers.image.revision=$SOURCE_COMMIT
COPY --from=build /wheels /wheels
RUN python -m pip install --disable-pip-version-check --no-cache-dir --no-index --find-links /wheels 'financial-evidence[workspace]' && rm -rf /wheels
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FINANCIAL_EVIDENCE_SOURCE_COMMIT=$SOURCE_COMMIT
USER 65532:65532
EXPOSE 6910
ENTRYPOINT ["python", "-m", "uvicorn", "financial_evidence.institutional_api:app"]
CMD ["--host", "0.0.0.0", "--port", "6910", "--no-access-log", "--no-proxy-headers", "--limit-concurrency", "32"]
