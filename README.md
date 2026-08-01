# DataLens Analytics

An AI-powered analytics dashboard that turns raw data into interactive visualizations and natural-language insights. Built with a React + Vite frontend and a FastAPI backend, with local LLM inference (Qwen 2.5) generating summaries and answering questions about your data.

## Overview

DataLens Analytics lets you upload a dataset, explore it through interactive charts and tables, and ask questions about it in plain language. The backend handles data processing and model inference; the frontend delivers a fast, responsive dashboard experience.

## Features

- Interactive data visualization dashboard
- Natural-language querying over your dataset via local LLM inference (Qwen 2.5)
- FastAPI backend for data processing and model serving
- Fast, modern frontend built with React + Vite

> Update this list with the specific charts/views and query capabilities your app actually ships.

## Tech Stack

**Frontend**
- React
- Vite
- CSS

**Backend**
- Python
- FastAPI
- Qwen 2.5 (local inference)

## Project Structure

```
DataLens-Analytics/
├── backend/     # FastAPI app, data processing, model inference
├── frontend/    # React + Vite dashboard
└── .gitignore
```

## Getting Started

### Prerequisites

- Node.js (v18+ recommended)
- Python 3.10+
- pip

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload
```

> Adjust the entry point (`main:app`) if your FastAPI app is defined elsewhere.

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
