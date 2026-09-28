FROM python:3.13-slim@sha256:ffb752e139c0a19692a43af8d8523b274222dd68eebad5d583b45c2201c6e30a AS build
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip wheel --disable-pip-version-check --wheel-dir /wheels '.[workspace]'

FROM python:3.13-slim@sha256:ffb752e139c0a19692a43af8d8523b274222dd68eebad5d583b45c2201c6e30a
COPY --from=build /wheels /wheels
RUN python -m pip install --disable-pip-version-check --no-cache-dir --no-index --find-links /wheels 'financial-evidence[workspace]' \
    && rm -rf /wheels
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 65532:65532
EXPOSE 6900
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:6900/healthz', timeout=3)"
ENTRYPOINT ["financial-evidence-api"]
CMD ["--host", "0.0.0.0", "--port", "6900"]
