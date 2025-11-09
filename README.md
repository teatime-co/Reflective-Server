# Reflective Server

A FastAPI backend for an AI-powered journaling application featuring semantic search, AI theme detection, linguistic analytics, and user management.

## What It Does

Reflective Server provides a complete journaling backend with AI-powered features:

- **Journal Management** - Full CRUD operations with automatic metadata tracking
- **Semantic Search** - RAG-powered search using Weaviate to find entries by meaning, not just keywords
- **AI Theme Detection** - Automatic theme classification using Ollama embeddings with confidence scoring
- **Linguistic Analytics** - NLP analysis providing sentiment, vocabulary diversity, readability, and emotion detection
- **Tag System** - User-scoped tags with automatic hashtag extraction and color coding
- **Writing Sessions** - Session tracking with focus scores, interruption counting, and duration metrics
- **User Management** - JWT authentication with user preferences (timezone, locale, daily goals)

All data is user-scoped with privacy-by-design architecture.

## Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL
- Ollama (running locally at `http://localhost:11434`)

### Installation

```bash
# Clone and setup
git clone <repository-url>
cd reflective-server
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials and secret key

# Setup database
createdb reflective
alembic upgrade head

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server will be available at:
- **API**: http://localhost:8000
- **Interactive API Docs**: http://localhost:8000/docs

## API Endpoints

All routes are prefixed with `/api`. Protected endpoints require JWT token in `Authorization: Bearer <token>` header.

Full interactive documentation with request/response schemas available at http://localhost:8000/docs

### Authentication
- `POST /api/auth/register` - Create new user account
- `POST /api/auth/login` - Authenticate and receive JWT token
- `POST /api/auth/refresh` - Refresh access token

### User Management
- `GET /api/users/me` - Get current user profile
- `PUT /api/users/me` - Update user profile (username, email)
- `GET /api/users/preferences` - Get user preferences (timezone, locale, daily goals)
- `PUT /api/users/preferences` - Update user preferences

### Journal Entries
- `GET /api/logs` - List entries with optional filters (mood, tags, themes, date range)
- `POST /api/logs` - Create entry with automatic tag extraction and theme detection
- `GET /api/logs/{id}` - Get specific entry with tags and themes
- `PUT /api/logs/{id}` - Update entry (re-triggers theme detection and updates embeddings)
- `DELETE /api/logs/{id}` - Delete entry and associated data

### Semantic Search
- `POST /api/search` - Search entries by semantic meaning using Weaviate embeddings
- `GET /api/search/similar` - Find similar past queries based on semantic similarity
- `GET /api/search/suggest` - Get query suggestions from search history

### Tags
- `GET /api/tags` - List all user tags with usage counts
- `POST /api/tags` - Create new tag with custom color
- `PUT /api/tags/{id}` - Update tag name or color
- `DELETE /api/tags/{id}` - Delete tag and remove from all entries
- `DELETE /api/tags/cleanup` - Remove tags unused for specified number of days

### Themes (AI-Detected)
- `GET /api/themes` - List all themes with entry counts
- `GET /api/themes/{id}` - Get theme details with associated entries and confidence scores
- `PUT /api/themes/{id}` - Update theme name, description, or color
- `DELETE /api/themes/{id}` - Delete theme (removes associations, not entries)

### Writing Sessions
- `GET /api/sessions` - List sessions with optional type filter
- `POST /api/sessions` - Start new session (daily, freeform, or prompted)
- `GET /api/sessions/{id}` - Get session details with associated logs
- `PUT /api/sessions/{id}` - Update session focus score, interruptions, and end session

### Linguistic Analytics
- `GET /api/linguistic/{log_id}` - Get NLP analysis for entry (sentiment, vocabulary diversity, readability, emotion scores)

*Note: Linguistic analysis is performed automatically when entries are created or updated*

## Architecture

### Tech Stack
- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL with SQLAlchemy 2.0.23
- **Vector Database**: Weaviate (Embedded) for semantic search
- **AI/Embeddings**: Ollama with snowflake-arctic-embed2 model
- **NLP**: spaCy (en_core_web_sm), TextBlob
- **Authentication**: JWT with bcrypt password hashing
- **Testing**: pytest

### Key Design Principles

1. **User-Scoped Data** - All entries, tags, themes, and sessions are isolated per-user
2. **Dual AI Pipeline** - PostgreSQL for structured data + Weaviate for vector embeddings (synchronized)
3. **Privacy-by-Design** - Tags and themes are private to each user
4. **Async Processing** - AI features (theme detection, linguistic analysis) run asynchronously

### Project Structure
```
app/
├── api/
│   ├── auth.py
│   ├── users.py
│   ├── logs.py
│   ├── search.py
│   ├── tags.py
│   ├── themes.py
│   ├── sessions.py
│   └── linguistic.py
├── services/
│   ├── auth_service.py
│   ├── weaviate_rag_service.py
│   ├── theme_service.py
│   ├── linguistic_service.py
│   └── session_service.py
├── models/
├── schemas/
└── main.py
```

## Development

### Running Tests
```bash
# Run all tests
pytest

# Run specific categories
pytest tests/api/          # API endpoint tests
pytest tests/services/     # Service layer tests
pytest tests/core/         # Core functionality tests

# Run with coverage
pytest --cov=app --cov-report=html
```

### Development Environment Reset

For frontend testing, use the `dev_reset.py` utility to quickly reset your development environment:

```bash
# Reset databases and create test users
python dev_reset.py

# Reset and create users with rich journal data
python dev_reset.py --rich

# Only create users (skip database reset)
python dev_reset.py --skip-reset
```

**Test User Credentials:**
- Quick test: `test@example.com` / `testpass123`
- Food blogger: `love@food.com` / `foodlover123`
- Researcher: `cell@apoptosis.com` / `researcher123`
- Hiker: `hike@man.com` / `hiker123`

See [DEV_SETUP.md](DEV_SETUP.md) for complete documentation and API examples.

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Environment Variables
```env
DATABASE_URL=postgresql://user:password@localhost:5432/reflective
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
OLLAMA_BASE_URL=http://localhost:11434
```

## License

MIT License
