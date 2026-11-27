# ACE in one image: the site and API (gunicorn), MCP over HTTP (ace-mcp) and the snapshot refresh job (ace refresh).
# Build:  docker build --build-arg ACE_COMMIT=$(git rev-parse HEAD) -t ace .
# Run:    docker run -p 8080:8080 -e ACE_PSEUDONYM_SALT=<a secret of 32 characters or more> ace
# The image starts in production mode, so it refuses to start with the development salt.

FROM python:3.12-slim AS build
WORKDIR /src
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
COPY context_packs ./context_packs
COPY snapshots ./snapshots
RUN pip wheel --no-cache-dir --wheel-dir /wheels ".[serve,cloud,mcp]"

FROM python:3.12-slim
ARG ACE_COMMIT=""
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 ACE_ENV=production ACE_COMMIT=${ACE_COMMIT} PORT=8080
RUN useradd --create-home --uid 10001 ace
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels "ace-engine[serve,cloud,mcp]" && rm -rf /wheels
USER ace
WORKDIR /home/ace
EXPOSE 8080
CMD ["sh", "-c", "exec gunicorn --bind :${PORT} --workers 1 --threads 8 --timeout 30 --access-logfile - --access-logformat '%(m)s %(U)s %(s)s %(L)s' 'ace_engine.app:create_app()'"]
