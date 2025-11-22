FROM python:3.11-slim

WORKDIR /app

# Install system deps (none needed currently) and Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py ./

# Environment defaults (can be overridden at runtime)
ENV PORT=8080

EXPOSE 8080

CMD ["python", "main.py"]
