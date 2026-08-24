FROM python:3.13-slim@sha256:ffb752e139c0a19692a43af8d8523b274222dd68eebad5d583b45c2201c6e30a AS build

WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip wheel --disable-pip-version-check --no-deps --wheel-dir /wheels .

FROM python:3.13-slim@sha256:ffb752e139c0a19692a43af8d8523b274222dd68eebad5d583b45c2201c6e30a

COPY --from=build /wheels /wheels
RUN python -m pip install --disable-pip-version-check --no-cache-dir /wheels/*.whl \
    && rm -rf /wheels

USER 65532:65532
ENTRYPOINT ["financial-evidence"]
CMD ["topics", "--format", "json"]

