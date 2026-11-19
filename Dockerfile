FROM python:3.15-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY millwork_mcp_lite ./millwork_mcp_lite
RUN pip install --no-cache-dir .
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin millwork
USER 10001
CMD ["millwork-mcp-lite"]
