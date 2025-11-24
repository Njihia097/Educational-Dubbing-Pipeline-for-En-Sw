# Educational Dubbing Pipeline

**An MVP system for multilingual video dubbing, specializing in English → Kenyan Swahili translation for educational content.**

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Project Structure](#project-structure)
- [Pipeline Process](#pipeline-process)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

---

## 🎯 Overview

The Educational Dubbing Pipeline is a full-stack application that automates the process of dubbing educational videos from English to Kenyan Swahili. It uses machine learning models for Automatic Speech Recognition (ASR), Machine Translation (MT), and Text-to-Speech (TTS) synthesis, combined with audio processing for music separation and video mixing.

The system consists of:
- **Backend API**: Flask-based REST API with Celery task queue
- **Frontend**: React-based dashboard for job management and monitoring
- **External AI Service**: Separate microservice handling ML model inference
- **Storage**: MinIO (S3-compatible) object storage
- **Database**: PostgreSQL for metadata and job tracking

---

## ✨ Features

### For Content Creators
- 📤 **Video Upload**: Drag-and-drop interface for video file uploads
- 📊 **Job Dashboard**: View all dubbing jobs with real-time status updates
- 📝 **Transcript Viewer**: View and edit English and Swahili transcripts with timestamps
- 🎬 **Video Preview**: Preview dubbed videos with synchronized transcript segments
- 📥 **Download Manager**: Download final dubbed videos and intermediate outputs
- 🔄 **Translation Feedback**: Submit corrections and feedback on translation quality

### For Administrators
- 📈 **Analytics Dashboard**: System-wide metrics and performance monitoring
- 👥 **User Management**: Monitor all users and their job activity
- 📊 **Pipeline Metrics**: Track ASR, MT, and TTS performance metrics
- 📉 **Model Metrics**: Monitor model performance across jobs
- 🔍 **MT Quality Analytics**: Analyze translation feedback and quality trends
- 🔧 **Worker Monitoring**: Track Celery worker status and job processing

### Core Pipeline Capabilities
- 🎤 **ASR (Automatic Speech Recognition)**: Extracts English transcripts from video
- 🔄 **Machine Translation**: Translates English text to Kenyan Swahili
- 🔊 **Text-to-Speech**: Synthesizes Swahili audio from translated text
- 🎵 **Music Separation**: Separates background music from speech using Demucs
- 🎬 **Audio Mixing**: Mixes generated speech with background music
- 🎥 **Video Rendering**: Replaces original audio with dubbed audio

---

## 🏗️ Architecture

The system follows a microservices architecture:

```
┌─────────────┐
│   Frontend  │ (React + Vite)
│  (Port 5173)│
└──────┬──────┘
       │ HTTP/REST
       │
┌──────▼─────────────────────────────────┐
│         Backend API (Flask)            │
│         (Port 5000)                    │
│  ┌──────────────────────────────────┐  │
│  │  - Job Management                │  │
│  │  - User Authentication           │  │
│  │  - Storage API                   │  │
│  │  - Admin Dashboard               │  │
│  └──────────────────────────────────┘  │
└──────┬─────────────┬───────────────────┘
       │             │
       │             │ Celery Tasks
       │             │
   ┌───▼───┐    ┌───▼──────────────┐
   │Postgres│    │  Celery Worker   │
   │  :5432 │    │   (GPU-enabled)  │
   └───────┘    └─────────┬─────────┘
                          │
                    ┌─────▼──────────────┐
                    │ External AI Server │
                    │   (Port 7001)      │
                    │  ┌──────────────┐  │
                    │  │ - Whisper    │  │
                    │  │ - MT Models  │  │
                    │  │ - TTS Models │  │
                    │  │ - Demucs     │  │
                    │  └──────────────┘  │
                    └────────────────────┘
       │
┌──────▼──────┐    ┌──────▼──────┐
│   MinIO     │    │    Redis    │
│  (S3 API)   │    │   Queue     │
│  :9000      │    │   :6379     │
└─────────────┘    └─────────────┘
```

### Component Details

1. **Frontend (React)**: Modern UI built with React 19, React Router, and Tailwind CSS
2. **Backend (Flask)**: RESTful API handling authentication, job management, and file operations
3. **Celery Worker**: Asynchronous task processor for pipeline execution
4. **External AI Service**: Standalone Flask service running ML models (ASR, MT, TTS, Demucs)
5. **PostgreSQL**: Persistent storage for users, jobs, metrics, and feedback
6. **MinIO**: S3-compatible object storage for video files
7. **Redis**: Message broker for Celery task queue

---

## 🛠️ Tech Stack

### Backend
- **Python 3.13**: Core language
- **Flask 3.1.2**: Web framework
- **Celery 5.5.3**: Distributed task queue
- **SQLAlchemy 2.0.44**: ORM
- **Alembic**: Database migrations
- **PostgreSQL 16**: Database
- **Redis 7**: Message broker
- **MinIO**: Object storage

### Frontend
- **React 19.2.0**: UI framework
- **React Router 7.9.6**: Routing
- **Vite 7.2.2**: Build tool
- **Tailwind CSS 4.1.17**: Styling
- **Recharts 3.4.1**: Data visualization

### DevOps
- **Docker & Docker Compose**: Containerization
- **Alembic**: Database migrations

---

## 📦 Prerequisites

Before you begin, ensure you have the following installed:

- **Docker** (v20.10+) and **Docker Compose** (v2.0+)
- **Node.js** (v18+) and **npm** (for frontend development)
- **Python 3.13** (for local backend development, optional)
- **CUDA-capable GPU** (for ML model inference, optional but recommended)
- **Git**

### For GPU Support (Optional)
- **NVIDIA Docker Runtime** (`nvidia-container-toolkit`)
- **CUDA drivers** compatible with PyTorch

---

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Educational-Dubbing-Pipeline
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```bash
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=edu_dubbing

# MinIO Storage
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123

# External AI Service (adjust if running externally)
EXTERNAL_AI_URL=http://host.docker.internal:7001

# Flask
FLASK_ENV=production
FLASK_DEBUG=0
JWT_SECRET=your-secret-key-change-this

# Storage Configuration
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin123
S3_BUCKET=edu-dubbing
S3_BUCKET_UPLOADS=uploads
S3_BUCKET_OUTPUTS=outputs
S3_REGION=us-east-1
S3_SECURE=False
```

Create `backend/.env` for backend-specific settings (if needed).

### 3. Start Infrastructure Services

Start PostgreSQL, Redis, and MinIO:

```bash
docker-compose up -d postgres redis minio
```

Wait for services to be healthy (check with `docker-compose ps`).

### 4. Initialize Database

Run database migrations:

```bash
# If running backend in Docker:
docker-compose run --rm backend flask db upgrade

# Or if running locally:
cd backend
pip install -r requirements.txt
flask db upgrade
```

### 5. Start External AI Service

The external AI service should run separately (on a machine with GPU access):

```bash
cd external_ai
pip install -r requirements.txt
python local_ai_server.py
```

This service listens on port `7001` by default.

### 6. Start Backend Services

Start the Flask API and Celery worker:

```bash
docker-compose up -d backend worker
```

Or run locally:

```bash
# Terminal 1: Flask API
cd backend
python run.py

# Terminal 2: Celery Worker
cd backend
celery -A app.celery_app worker --loglevel=info
```

### 7. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

### 8. Quick Start (All Services)

Alternatively, use Docker Compose to start everything:

```bash
# Clean start (removes old containers)
# On Windows PowerShell:
.\clean_run.ps1

# Or manually:
docker-compose down -v
docker-compose up -d --build
```

---

## ⚙️ Configuration

### Backend Configuration

Key configuration files:
- `backend/app/config.py`: Main configuration
- `backend/.env`: Environment variables
- `docker-compose.yml`: Service configuration

### Frontend Configuration

- `frontend/vite.config.js`: Vite build configuration
- `frontend/src/main.jsx`: Application entry point

### External AI Service

Configure the external AI service in `external_ai/local_ai_server.py`:
- Model paths and versions
- GPU/CPU device selection
- Whisper model size

---

## 📖 Usage

### For End Users

1. **Register/Login**: Create an account or login at `/login`
2. **Upload Video**: Go to `/dashboard/upload` and upload your English video
3. **Monitor Job**: View job progress in `/dashboard/jobs`
4. **View Results**: Click on a job to see transcripts and download the dubbed video
5. **Provide Feedback**: Submit translation corrections if needed

### For Administrators

1. **Admin Dashboard**: Access at `/dashboard/admin/overview`
2. **System Metrics**: Monitor pipeline performance at `/dashboard/admin/pipeline-metrics`
3. **Model Analytics**: View model performance at `/dashboard/admin/model-metrics`
4. **MT Quality**: Analyze translation feedback at `/dashboard/admin/mt-quality`
5. **Worker Status**: Check Celery worker status at `/dashboard/admin/monitoring`

### API Usage

#### Create a Job

```bash
POST /api/jobs
Content-Type: application/json

{
  "video_file": <multipart-form-data>
}
```

#### Get Job Status

```bash
GET /api/jobs/{job_id}
```

#### Download Output

```bash
GET /api/storage/download/{job_id}?kind=video
```

See [API Documentation](#api-documentation) for more details.

---

## 📚 API Documentation

### Authentication

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Get current user

### Jobs

- `GET /api/jobs` - List user's jobs
- `POST /api/jobs` - Create new dubbing job
- `GET /api/jobs/{job_id}` - Get job details
- `DELETE /api/jobs/{job_id}` - Cancel/delete job

### Storage

- `GET /api/storage/download/{job_id}` - Download job output
- `GET /api/storage/uploads/{upload_id}` - Get upload URL

### Pipeline

- `POST /api/pipeline/run` - Manually trigger pipeline
- `GET /api/pipeline/status/{task_id}` - Get pipeline task status

### Admin (Admin Only)

- `GET /api/admin/jobs` - List all jobs
- `GET /api/admin/metrics` - Get system metrics
- `GET /api/admin/pipeline-metrics` - Get pipeline performance metrics
- `GET /api/admin/model-metrics` - Get model performance data

### MT Feedback

- `POST /api/mt-feedback` - Submit translation feedback
- `GET /api/mt-feedback/job/{job_id}` - Get feedback for a job
- `GET /api/mt-feedback/stats` - Get feedback statistics

---

## 💻 Development

### Backend Development

```bash
cd backend

# Install dependencies
pip install -r requirements.txt
pip install -r requirements.dev.txt  # For development tools

# Run migrations
flask db upgrade

# Run tests
pytest tests/

# Run with hot reload
python run.py
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Lint code
npm run lint
```

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/

# Smoke tests
pytest tests/smoke/
```

### Database Migrations

```bash
# Create a new migration
flask db migrate -m "description"

# Apply migrations
flask db upgrade

# Rollback migration
flask db downgrade
```

---

## 📁 Project Structure

```
Educational-Dubbing-Pipeline/
├── backend/                 # Flask backend application
│   ├── app/
│   │   ├── __init__.py     # Flask app factory
│   │   ├── config.py       # Configuration
│   │   ├── database.py     # SQLAlchemy setup
│   │   ├── models/         # Database models
│   │   ├── routes/         # API routes (blueprints)
│   │   ├── tasks/          # Celery tasks
│   │   ├── services/       # Business logic services
│   │   └── utils/          # Utility functions
│   ├── migrations/         # Alembic migrations
│   ├── tests/              # Test suite
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile          # Backend container definition
│   └── run.py              # Application entry point
│
├── frontend/               # React frontend application
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── hooks/          # Custom React hooks
│   │   ├── utils/          # Utility functions
│   │   ├── auth/           # Authentication context
│   │   └── App.jsx         # Main app component
│   ├── package.json        # Node dependencies
│   └── vite.config.js      # Vite configuration
│
├── external_ai/            # External ML inference service
│   ├── local_ai_server.py  # Flask server for ML models
│   ├── pipeline_core_loader.py  # Pipeline initialization
│   └── requirements.txt    # ML dependencies
│
├── storage/                # Local storage (uploads/outputs)
├── storage_data/           # MinIO data (docker volume)
├── postgres_data/          # PostgreSQL data (docker volume)
├── redis_data/             # Redis data (docker volume)
│
├── docker-compose.yml      # Docker services configuration
├── PIPELINE_DATA_SPECIFICATION.md  # Pipeline output format spec
├── clean_run.ps1          # Windows cleanup script
└── README.md              # This file
```

---

## 🔄 Pipeline Process

The dubbing pipeline follows these steps:

1. **Video Upload**: User uploads video via frontend → stored in MinIO
2. **Job Creation**: Backend creates a `Job` record and enqueues Celery task
3. **ASR (Automatic Speech Recognition)**: Extract English transcript from audio
4. **Punctuation**: Add punctuation to transcript
5. **Translation**: Translate English text to Kenyan Swahili
6. **TTS (Text-to-Speech)**: Synthesize Swahili audio from translated text
7. **Music Separation**: Separate background music from original audio (Demucs)
8. **Audio Mixing**: Mix generated speech with separated background music
9. **Video Rendering**: Replace original audio with dubbed audio in video
10. **Storage**: Upload final dubbed video to MinIO outputs bucket
11. **Completion**: Update job status and make results available for download

Each step is tracked as a `JobStep` with metrics and timestamps.

### Pipeline Data Format

The pipeline returns structured data including:
- English and Swahili transcripts (full text)
- Timestamped segments for both languages
- Output video path
- Optional metrics (ASR confidence, processing time, etc.)

See `PIPELINE_DATA_SPECIFICATION.md` for detailed format specification.

---

## 🔧 Troubleshooting

### Common Issues

**1. Services won't start**
- Check Docker is running: `docker ps`
- Check ports are not in use (5000, 5432, 6379, 9000, 7001)
- Check `.env` file exists and has correct values

**2. Database connection errors**
- Ensure PostgreSQL container is healthy: `docker-compose ps`
- Check database credentials in `.env`
- Try: `docker-compose restart postgres`

**3. Celery worker not processing jobs**
- Check Redis is running: `docker-compose ps redis`
- Check worker logs: `docker-compose logs worker`
- Verify `EXTERNAL_AI_URL` is accessible from worker container

**4. External AI service connection failed**
- Ensure external AI service is running on port 7001
- Check firewall/network settings
- Verify `EXTERNAL_AI_URL` in docker-compose.yml matches actual service URL

**5. MinIO upload/download errors**
- Check MinIO is healthy: `docker-compose ps minio`
- Access MinIO console at `http://localhost:9001` (use MINIO_ROOT_USER/PASSWORD)
- Verify bucket exists: `edu-dubbing`

**6. Frontend can't connect to backend**
- Check backend is running on port 5000
- Verify CORS settings if running frontend on different port
- Check browser console for errors

### Getting Help

1. Check logs: `docker-compose logs <service-name>`
2. Review error messages in job details
3. Check database for job state: `SELECT * FROM job WHERE id = '<job_id>'`
4. Verify all environment variables are set correctly

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Run tests: `pytest tests/` and `npm test` (frontend)
5. Commit changes: `git commit -m "Add your feature"`
6. Push to branch: `git push origin feature/your-feature`
7. Submit a pull request

### Code Style

- **Python**: Follow PEP 8, use Black for formatting
- **JavaScript/React**: Follow ESLint rules, use Prettier
- **Commits**: Use conventional commit messages

---

## 🙏 Acknowledgments

- Whisper for ASR capabilities
- Demucs for audio source separation
- Open-source translation models for MT
- TTS models for speech synthesis

---


**Last Updated**: 2024
