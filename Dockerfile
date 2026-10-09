FROM node:22-bookworm-slim AS viewer
RUN apt-get update && apt-get install -y --no-install-recommends python3 python-is-python3 && rm -rf /var/lib/apt/lists/*
WORKDIR /app/web
COPY assets /app/assets
COPY scripts/restore_assets.py /app/scripts/restore_assets.py
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libgl1 libxerces-c3.2 libproj25 && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml requirements.lock ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements.lock && pip install --no-cache-dir --no-deps .
COPY data ./data
COPY networks ./networks
COPY scenarios ./scenarios
COPY assets ./assets
COPY scripts/restore_assets.py ./scripts/restore_assets.py
RUN python scripts/restore_assets.py
COPY --from=viewer /app/web/dist ./web/dist
RUN useradd --create-home traffic && mkdir /app/var && chown traffic:traffic /app/var
USER traffic
EXPOSE 8000
CMD ["uvicorn", "traffic_twin.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
