# Build the React client first.
FROM node:22-slim AS client-builder
WORKDIR /app/client
COPY client/package*.json ./
RUN npm ci
COPY client/ ./
RUN npm run build && mkdir -p dist/images && cp -r images/* dist/images/

# Run the Flask/Socket.IO server with Gunicorn + eventlet.
FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

COPY server/ ./server
COPY --from=client-builder /app/client/dist ./client/dist

EXPOSE 8080
CMD ["sh", "-c", "cd server && gunicorn --worker-class eventlet -w 1 app:app --bind 0.0.0.0:${PORT:-8080}"]
