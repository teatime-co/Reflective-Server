# Reflective Server

A sophisticated FastAPI backend for the Reflective journaling application, featuring AI-powered analytics, semantic search, and comprehensive user management.

## 🚀 Overview

Reflective Server is a robust backend that combines traditional journaling functionality with cutting-edge AI features including:

- **Semantic Search**: RAG (Retrieval-Augmented Generation) powered by Weaviate
- **AI Theme Detection**: Automatic content theme classification using embeddings
- **Linguistic Analytics**: Advanced NLP analysis with spaCy and TextBlob
- **Writing Session Tracking**: Comprehensive session management and focus tracking
- **User Management**: JWT-based authentication with comprehensive user preferences
- **Real-time Processing**: Async processing pipeline for AI features

## 📋 Features

### ✅ **Fully Implemented**

#### **Core Platform**
- **User Authentication & Management**
  - JWT-based authentication with refresh tokens
  - User registration and login
  - Comprehensive user preferences (timezone, locale, writing goals)
  - Secure password hashing with bcrypt

- **Journal Entry Management**
  - Full CRUD operations for journal entries
  - Rich text content support
  - Automatic word counting and metadata tracking
  - User-scoped data access

- **Tag System**
  - Hashtag-based tag extraction from content
  - Tag management and organization
  - Tag-based filtering and search

#### **Advanced AI Features**
- **Semantic Search (RAG)**
  - Weaviate-powered vector search
  - Embedding generation and storage
  - Relevance scoring and result ranking
  - Query history tracking

- **AI Theme Detection**
  - Automatic theme classification using Ollama embeddings
  - Confidence scoring and thresholding
  - Theme evolution tracking
  - Dual classification system (AI themes vs user tags)

- **Linguistic Analytics**
  - Comprehensive NLP analysis using spaCy
  - Sentiment analysis with TextBlob
  - Vocabulary diversity scoring
  - Readability level calculation
  - Emotion analysis with confidence scores
  - Writing style metrics

- **Writing Session Tracking**
  - Session lifecycle management
  - Focus score calculation
  - Interruption counting
  - Session type classification (daily/freeform/prompted)

### 🔶 **Schema Ready (Implementation Pending)**
- **Revision Tracking**: Database schema complete, service layer needed
- **Contextual Prompts**: Schema ready, prompt generation service needed
- **User Insights**: Schema ready, analytics computation needed

## 🏗️ Architecture

### **Tech Stack**
- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL with SQLAlchemy 2.0.23
- **Vector Database**: Weaviate (Embedded)
- **NLP**: spaCy 3.7.2, TextBlob 0.15.3
- **Authentication**: JWT with python-jose
- **Testing**: pytest with comprehensive coverage
- **AI/ML**: scikit-learn, numpy, custom embedding pipeline

### **Project Structure**
```
app/
├── api/                    # API route handlers
│   ├── auth.py            # Authentication endpoints
│   ├── users.py           # User management
│   ├── logs.py            # Journal entry CRUD
│   ├── tags.py            # Tag management
│   ├── sessions.py        # Writing session tracking
│   ├── themes.py          # AI theme detection
│   └── linguistic.py      # Text analysis
├── models/
│   └── models.py          # SQLAlchemy database models
├── schemas/               # Pydantic request/response models
├── services/              # Business logic layer
│   ├── auth_service.py    # Authentication logic
│   ├── weaviate_rag_service.py # Semantic search (25KB)
│   ├── theme_service.py   # AI theme detection (9.7KB)
│   ├── linguistic_service.py # NLP analysis (19KB)
│   └── session_service.py # Session management (7KB)
├── utils/                 # Utility functions
├── main.py               # FastAPI application setup
└── database.py           # Database configuration
```

### **Database Schema**

The server implements a comprehensive schema supporting:

- **Users**: Complete user management with preferences
- **Logs**: Enhanced journal entries with AI metadata
- **Tags**: User-created tags with color coding
- **Themes**: AI-detected themes with confidence scores
- **Writing Sessions**: Session tracking and analytics
- **Linguistic Metrics**: Detailed text analysis results
- **Queries/Query Results**: Search history and results
- **Entry Revisions**: Version control (schema ready)
- **Prompts**: Contextual prompts (schema ready)
- **User Insights**: Analytics and growth tracking (schema ready)

## 🚦 Getting Started

### **Prerequisites**
- Python 3.8+
- PostgreSQL
- Docker (optional, for containerized deployment)

### **Installation**

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd reflective-server
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

3. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

   Required environment variables:
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/reflective
   SECRET_KEY=your-secret-key-here
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   OLLAMA_BASE_URL=http://localhost:11434  # For theme detection
   ```

4. **Database Setup**
   ```bash
   # Create database
   createdb reflective
   
   # Run migrations
   alembic upgrade head
   ```

5. **Start the Server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The API will be available at:
   - **API**: http://localhost:8000
   - **Interactive Docs**: http://localhost:8000/docs
   - **ReDoc**: http://localhost:8000/redoc

### **Development Setup**

1. **Run Tests**
   ```bash
   pytest
   # With coverage
   pytest --cov=app --cov-report=html
   ```

2. **Code Quality**
   ```bash
   # Format code
   black app/
   
   # Lint
   flake8 app/
   ```

## 📚 API Documentation

### **Authentication**
```http
POST /api/auth/register    # User registration
POST /api/auth/login       # User login
POST /api/auth/refresh     # Token refresh
```

### **User Management**
```http
GET    /api/users/me       # Get current user
PUT    /api/users/me       # Update user profile
GET    /api/users/preferences # Get user preferences
PUT    /api/users/preferences # Update preferences
```

### **Journal Entries**
```http
GET    /api/logs           # List entries (with filters)
POST   /api/logs           # Create entry
GET    /api/logs/{id}      # Get specific entry
PUT    /api/logs/{id}      # Update entry
DELETE /api/logs/{id}      # Delete entry
POST   /api/logs/search    # Semantic search
```

### **Advanced Features**
```http
GET    /api/tags           # List all tags
GET    /api/sessions       # Writing sessions
POST   /api/sessions       # Start session
PUT    /api/sessions/{id}  # Update session
GET    /api/themes         # AI-detected themes
GET    /api/linguistic/{log_id} # Text analysis
```

## 🧪 Testing

The server includes comprehensive test coverage:

- **API Tests**: All endpoints tested
- **Service Tests**: Business logic validation
- **Integration Tests**: End-to-end workflows
- **Performance Tests**: Response time validation

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/api/          # API endpoint tests
pytest tests/services/     # Service layer tests
pytest tests/core/         # Core functionality tests

# Generate coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## 🔧 Configuration

### **Database Configuration**
- **Development**: SQLite (for quick testing)
- **Production**: PostgreSQL (recommended)
- **Migrations**: Alembic for schema management

### **AI Services Configuration**
- **Weaviate**: Embedded mode (default) or external instance
- **Ollama**: For theme detection embeddings
- **spaCy**: English model (`en_core_web_sm`)

### **Security Configuration**
- **JWT**: Configurable expiration times
- **CORS**: Configurable origins
- **Rate Limiting**: Available for production

## 🚀 Deployment

### **Docker Deployment**
```bash
# Build image
docker build -t reflective-server .

# Run with docker-compose
docker-compose up -d
```

### **Environment Variables for Production**
```env
DATABASE_URL=postgresql://user:pass@db:5432/reflective
SECRET_KEY=your-production-secret-key
DEBUG=false
CORS_ORIGINS=https://yourapp.com,https://api.yourapp.com
```

## 📊 Performance & Monitoring

- **Response Times**: Average <100ms for CRUD operations
- **Search Performance**: Semantic search <500ms
- **Scalability**: Designed for horizontal scaling
- **Monitoring**: Health check endpoints available

## 🔮 Roadmap

### **Upcoming Features** (Schema Ready)
1. **Revision Tracking System**: Complete version control for entries
2. **Contextual Prompts**: AI-generated writing prompts
3. **User Insights**: Advanced analytics and growth tracking
4. **Knowledge Graph**: Enhanced relationship mapping between entries

### **Future Enhancements**
- Real-time collaborative editing
- Advanced export/import capabilities
- Mobile app backend support
- Advanced analytics dashboard

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Available at `/docs` endpoint
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

---

**Built with ❤️ for thoughtful journaling and personal growth** 