# Render-friendly Dockerfile for the FastAPI backend
# - Binds to Render's injected $PORT
# - Keeps image small-ish (slim)
# - Installs OS deps needed by uvicorn[standard] (uvloop is skipped on Windows but used on Linux)

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (minimal). build-essential is required for some wheels in slim images.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app
COPY . .

# Render sets PORT; default to 8000 for local docker runs
ENV PORT=8000

# Expose is optional on Render but helpful for local usage
EXPOSE 8000

# Run the API
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]

