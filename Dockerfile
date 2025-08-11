FROM docker:25.0-dind
RUN apk update && apk upgrade --no-interactive && apk add tini
RUN apk add --no-cache python3 git fuse-overlayfs tini nodejs-current npm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY . /app/
RUN uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

ENTRYPOINT ["tini", "-s", "--"]
CMD ["python", "-m", "mcp_anywhere", "serve", "http"]