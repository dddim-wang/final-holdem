# Hold'em Squat

Texas Hold'em party game built with React, Flask, and Socket.IO.

## Railway deployment

This repository is ready for Railway GitHub auto deploy with the root `Dockerfile`.

Railway will:

1. Install the React client dependencies with `npm ci`.
2. Build the client with `npm run build`.
3. Install the Flask server dependencies from `server/requirements.txt`.
4. Start the app with Gunicorn and the eventlet worker.

Start command used by the Docker image:

```sh
cd server && gunicorn --worker-class eventlet -w 1 app:app --bind 0.0.0.0:${PORT:-8080}
```

Set these Railway variables before production use:

```env
SECRET_KEY=replace-with-a-long-random-secret
JWT_SECRET_KEY=replace-with-a-different-long-random-secret
CORS_ORIGINS=*
```

After Railway gives you a public URL, you can tighten `CORS_ORIGINS` to that URL.

## Local development

Server:

```sh
cd server
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

Client:

```sh
cd client
npm install
npm run dev
```

## Git hygiene

Do not commit local runtime artifacts. The existing `.gitignore` excludes:

- `server/.venv/`
- `server/app.db`
- `server/__pycache__/`
- `client/node_modules/`
- `client/dist/`
