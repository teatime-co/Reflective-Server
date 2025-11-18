# Reflective Server

A **zero-knowledge backend** for the Reflective journaling app. Enables multi-device sync and encrypted analytics without ever accessing plaintext journal content.

\>> [Reflective Web Client](https://github.com/teatime-co/Reflective-App) <<

## Overview

### Architecture: Progressive Privacy Enhancement

Reflective Server supports three sync modes, allowing users to choose their privacy-convenience tradeoff:

**Tier 1: Local Only** (default)
- Zero server communication beyond authentication
- All data stays on device

**Tier 2: Analytics Sync**
- Encrypted metrics only (word count, sentiment scores)
- Uses homomorphic encryption (CKKS) for privacy-preserving aggregation
- Server computes insights on encrypted data without decryption

**Tier 3: Full Sync**
- Encrypted journal entries (AES-256) for multi-device access
- Automatic conflict detection with user-driven resolution
- Server stores encrypted blobs only

### What the Server Knows vs. Doesn't Know

**Server NEVER sees**:
- Journal content (encrypted client-side with AES-256)
- Embeddings for semantic search
- Individual metric values (homomorphically encrypted)

**Server CAN see** (for coordination only):
- User email and display name
- Timestamps (for sync ordering)
- Device IDs (for conflict detection)
- Metric types (for aggregation filtering)

### Security Guarantees

- **Database breach**: Attacker gets encrypted blobs, not plaintext
- **Malicious admin**: No access to decryption keys (stored in client OS keychain)
- **Legal requests**: Cannot provide plaintext (cryptographically impossible)

**Zero-Knowledge Architecture**: Encryption keys never leave user devices. Even with full database access, the server cannot decrypt journal entries.

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+

### Installation

```bash
cd reflective-server

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env with your DATABASE_URL and SECRET_KEY

alembic upgrade head
```

Start the server:
```bash
uvicorn app.main:app --reload
```

Server runs at `http://localhost:8000`

Interactive API docs: `http://localhost:8000/docs`

### Development Setup

For testing and demos:

```bash
# Reset database and create test users
python dev_reset.py
```

**Test User Credentials**:
- `test@example.com` / `testpass123`
- `love@food.com` / `foodlover123`
- `cell@apoptosis.com` / `researcher123`
- `hike@man.com` / `hiker123`

### Coordinated Frontend + Backend Demo

For a fully synced demo with the Reflective web client:

```bash
# Backend (this repository)
cd reflective-server
python dev_reset.py
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd ../reflective-web
./scripts/dev-reset.sh
node scripts/seed-demo-data-authed.js
npm run dev
```

Entries will sync automatically every 30 seconds.

## Technology Stack

Built with modern Python web technologies:

- **FastAPI** - Async web framework with automatic API documentation
- **PostgreSQL** - Encrypted data storage with SQLAlchemy ORM
- **TenSEAL** - Homomorphic encryption (CKKS scheme)
- **JWT + bcrypt** - Secure authentication
- **Alembic** - Database migrations
- **pytest** - Testing (108 tests, 100% pass rate)

For detailed technical architecture, see [ARCHITECTURE.md](./ARCHITECTURE.md).

## Core Features

**Progressive Privacy**
- User-controlled data sharing with three privacy tiers
- Upgrade/downgrade at any time
- Tier downgrades delete cloud data automatically

**Encrypted Sync**
- Cross-device backup with conflict detection
- User-driven conflict resolution (local/remote/merged)
- Device-aware versioning

**Privacy-Preserving Analytics**
- Server aggregates metrics without decryption
- Homomorphic encryption enables insights without surveillance
- Client-side decryption only

**User Data Sovereignty**
- Tags with color coding and auto-cleanup
- User preferences (timezone, locale, daily goals)
- Export and delete cloud data anytime

## API Overview

All protected endpoints require JWT authentication via `Authorization: Bearer <token>` header.

**Authentication**: Register, login, JWT tokens

**Users**: Profile management, preferences, privacy tier upgrades/downgrades

**Tags**: User-scoped tags with auto-deduplication and stale cleanup

**Encryption**: Homomorphic encryption context, metrics upload, aggregation

**Sync**: Encrypted backup upload/fetch, conflict detection and resolution

For complete API documentation, visit `http://localhost:8000/docs` or see [ARCHITECTURE.md](./ARCHITECTURE.md).

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/
```

**Test Coverage**: 108 tests covering encryption, sync, privacy tiers, conflict resolution, and authentication.

## Environment Configuration

**Required**:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/reflective_db
SECRET_KEY=your-secret-key-here
```

**Optional**:
```env
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

## Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Technical architecture, design decisions, scalability
- [API Docs (interactive)](http://localhost:8000/docs) - Swagger UI with request/response examples
