# Frontend (Next.js)

A minimal Next.js dashboard that talks to the FastAPI backend at `http://localhost:8000`.

## Setup

```cmd
cd frontend\nextjs-app
npm install
```

## Running in Development

```cmd
npm run dev
```

The app will be served at http://localhost:3000.

## Environment Variables

Create a `.env.local` file if you need custom settings:

```
NEXT_PUBLIC_AGENT_API_URL=http://localhost:8000
NEXT_PUBLIC_API_TOKEN=
```

## Features

- Submit natural language commands to the backend.
- Toggle headless/headful execution and screenshot capture.
- View structured results and action logs.
- Browse recent task history and download CSV/JSON exports.
- Optional voice input using the Web Speech API (Chrome).
