# DataLens Analytics

An AI-powered analytics dashboard that turns raw data into interactive visualizations and natural-language insights. Built with a React + Vite frontend and a FastAPI backend, using Google Gemini 2.5 Flash for natural-language analysis and Gemini Embeddings (`gemini-embedding-001`) with ChromaDB for retrieval-augmented generation (RAG).

## Overview

DataLens Analytics lets you upload a dataset, explore it through interactive charts and tables, and ask questions about it in plain language. The backend handles data processing, deterministic aggregations, and Gemini AI queries; the frontend delivers a fast, responsive dashboard experience.

## Features

- Interactive data visualization dashboard (charts, tables, distribution summaries)
- Natural-language querying over your dataset via Google Gemini 2.5 Flash
- Semantic RAG search with Google Gemini Embeddings (`gemini-embedding-001`, 768-dim) and ChromaDB
- Deterministic math fallback for exact mathematical calculations
- Cross-dataset isolation and verified source citations
- FastAPI backend with strict CORS, rate limiting, and ephemeral or persistent storage support
- Fast, modern frontend built with React + Vite, styled with Tailwind CSS

## Tech Stack

**Frontend**
- React 18
- Vite
- Tailwind CSS
- Lucide React & Recharts
- Deployed on Vercel (Root Directory: `frontend`)

**Backend**
- Python 3.13.5
- FastAPI & Uvicorn (Single worker)
- Google Gemini 2.5 Flash (`gemini-2.5-flash`)
- Google Gemini Embeddings (`gemini-embedding-001`)
- ChromaDB (vector store)
- pandas & PyArrow
- Deployed on Render Free Web Service

## Project Structure

```
DataLens-Analytics/
├── backend/          # FastAPI app, data processing, RAG, and AI services
├── frontend/         # React + Vite dashboard (Vercel deployment root)
├── docs/             # Architecture and deployment reports
├── render.yaml       # Render Free Web Service configuration
├── requirements.txt  # Python dependencies
└── .gitignore
```

## Getting Started

### Prerequisites

- Node.js (v18+ recommended)
- Python 3.11+ (Python 3.13.5 recommended for production)
- Google Gemini API Key (`GOOGLE_API_KEY`)

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # configure GOOGLE_API_KEY
uvicorn app:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173` and the backend API at `http://localhost:8000` by default.

## Usage

1. Start the backend server.
2. Start the frontend dev server.
3. Open the dashboard in your browser and upload a dataset.
4. Explore the generated visualizations and ask questions about your data.

## Roadmap

- [ ] Add support for additional file formats
- [ ] Expand visualization types
- [ ] Add authentication / multi-user support

## License

Specify a license (e.g. MIT) or note that this project is currently unlicensed.

## Author

**Mohamed Alaa**
Computer Engineering student, AI/ML & Computer Vision
Portfolio: [mohameedalaa.lovable.app](https://mohameedalaa.lovable.app)
