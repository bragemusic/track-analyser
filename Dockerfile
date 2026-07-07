FROM python:3.12-slim-trixie
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY --from=krallin/ubuntu-tini:trusty /usr/local/bin/tini /usr/local/bin/tini

COPY ./src /app/src
COPY ./uv.lock ./pyproject.toml ./.python-version /app/

ENV UV_NO_DEV=1

WORKDIR /app
RUN uv sync --locked

ENTRYPOINT ["tini", "--", "uv", "run", "src/analyser/main.py"]
