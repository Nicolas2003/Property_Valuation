FROM python:3.13-slim

# Links the GHCR package to the GitHub repo.
LABEL org.opencontainers.image.source="https://github.com/Nicolas2003/Property_Valuation.git"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

COPY .streamlit/config.toml .streamlit/config.toml
COPY app.py ./

ARG GIT_SHA=unknown
ARG GIT_COMMITTED_AT=unknown
ENV GIT_SHA=$GIT_SHA \
    GIT_COMMITTED_AT=$GIT_COMMITTED_AT

RUN useradd --system --create-home --uid 1000 streamlit && chown -R streamlit:streamlit /app
USER streamlit

EXPOSE 8501

CMD ["/app/.venv/bin/streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]