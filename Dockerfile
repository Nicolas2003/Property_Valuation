FROM python:3.13-slim

# Links the GHCR package to the GitHub repo.
LABEL org.opencontainers.image.source="https://github.com/Nicolas2003/Property_Valuation.git"

COPY --from=ghcr.io/astral-sh/uv:0.12.17@sha256:10787c682e4184e4f290de1171fd4703dc63de99221f10fe1c99002ce7fa9acc /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

RUN useradd --system --create-home --uid 1000 streamlit

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY estimator/ estimator/
COPY data/ data/
COPY migrations/ migrations/
COPY app.py db.py users.py ./

USER streamlit

EXPOSE 8501

ARG GIT_SHA=unknown
ARG GIT_COMMITTED_AT=unknown
ENV GIT_SHA=$GIT_SHA \
    GIT_COMMITTED_AT=$GIT_COMMITTED_AT

# A failed migration exits before Streamlit starts, so the healthcheck fails and Kamal keeps the previous version.
CMD ["sh", "-c", "/app/.venv/bin/python -m db && exec /app/.venv/bin/streamlit run app.py --server.address=0.0.0.0 --server.port=8501"]
