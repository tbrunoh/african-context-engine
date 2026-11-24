FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
COPY context_packs ./context_packs
RUN pip install --no-cache-dir . && useradd --create-home ace
USER ace
ENV ACE_ENV=production
EXPOSE 8000
CMD ["ace", "serve", "--host", "0.0.0.0", "--port", "8000"]
