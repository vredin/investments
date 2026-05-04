FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .

# CPU-only torch first — prevents uv from pulling 2GB of CUDA packages
RUN uv pip install --system --no-cache torch --index-url https://download.pytorch.org/whl/cpu

RUN uv pip install --system --no-cache .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
