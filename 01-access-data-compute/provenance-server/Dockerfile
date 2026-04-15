FROM python:3.12-slim

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir hatchling

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/

# Install the package and its dependencies
RUN pip install --no-cache-dir ".[postgres]"

# Expose default port
EXPOSE 8000

# Default environment
ENV PROVENANCE_DATABASE_URL="sqlite+aiosqlite:///./provenance.db"
ENV PROVENANCE_SERVICE_ID="provenance-server"
ENV PROVENANCE_SITE="local"

CMD ["python", "-m", "uvicorn", "provenance_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
