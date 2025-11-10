# Reflective Server

A privacy-first journaling backend with zero-knowledge architecture, homomorphic encryption, and encrypted cross-device sync.

## Overview

Reflective Server enables journaling with progressive privacy tiers. By default, all data stays local. Users can opt into encrypted cloud sync and privacy-preserving analytics without the server ever seeing plaintext content.

**Zero-Knowledge Guarantee**: Server stores only encrypted blobs. Encryption keys never leave user devices.

## Key Features

- **3-Tier Privacy System**
  - `local_only` (default): All data stays on device, zero server communication
  - `analytics_sync`: Homomorphic encrypted metrics for privacy-preserving insights
  - `full_sync`: AES-256 encrypted content backup with cross-device sync

- **Homomorphic Encryption (HE)**
  - Server aggregates user metrics without decrypting individual values
  - CKKS scheme via TenSEAL (128-bit security)
  - Client-side encryption/decryption only

- **Encrypted Cross-Device Sync**
  - AES-256 encrypted journal content and embeddings
  - Automatic conflict detection for multi-device edits
  - User-driven conflict resolution (local/remote/merged)

- **Privacy Guarantees**
  - Database breach: Attacker gets encrypted blobs, not plaintext
  - Malicious admin: No access to decryption keys
  - Legal requests: Cannot provide plaintext (cryptographically impossible)

- **User-Scoped Resources**
  - Tags with color coding and auto-cleanup
  - User preferences (timezone, locale, daily goals)
  - Privacy tier upgrades (opt-in only, downgrades delete cloud data)

## Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | 0.104.1 |
| Database | PostgreSQL + SQLAlchemy | 2.0.23 |
| Homomorphic Encryption | TenSEAL (CKKS) | 0.3.16 |
| Authentication | JWT + bcrypt | - |
| Migrations | Alembic | 1.12.1 |
| Validation | Pydantic | 2.5.1 |
| Testing | pytest | 7.4.3 |

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+

### Installation

```bash
# Navigate to server directory
cd reflective-server

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your DATABASE_URL and SECRET_KEY

# Run database migrations
alembic upgrade head

# Start server (development mode)
uvicorn app.main:app --reload
```

Server runs at `http://localhost:8000`

Interactive API docs: `http://localhost:8000/docs`

## Privacy Architecture

### Tier 1: local_only (Default)
- **What syncs**: Nothing (completely offline)
- **Features**: Local storage, local AI theme detection, local semantic search
- **Privacy**: Server never sees any user data

### Tier 2: analytics_sync
- **What syncs**: HE-encrypted metrics only (word count, sentiment, session duration)
- **What stays local**: Journal content, embeddings, themes
- **Privacy**: Server aggregates without decrypting individual values

### Tier 3: full_sync
- **What syncs**: AES-encrypted content, AES-encrypted embeddings, HE-encrypted metrics
- **What stays local**: All encryption keys (AES keys, HE secret key)
- **Privacy**: Server stores encrypted blobs, never sees plaintext

### What's Encrypted vs. Not Encrypted

**Encrypted (server never sees plaintext)**:
- Journal content (AES-256)
- Embeddings (AES-256)
- Individual metric values (HE CKKS)

**Not encrypted (server can see)**:
- User email, display name
- Privacy tier setting
- Timestamps (for sync coordination)
- Device IDs (for conflict detection)
- Metric types (for aggregation filtering)

## API Endpoints

Base URL: `http://localhost:8000`

All protected endpoints require `Authorization: Bearer <token>` header.

### Authentication (`/api/auth`)
- `POST /api/auth/register` - Create new user account
- `POST /api/auth/token` - Login and receive JWT token (30min expiration)

### Users (`/api/users`)
- `GET /api/users/me` - Get user profile with stats
- `PUT /api/users/me` - Update profile (display name, timezone)
- `GET /api/users/me/preferences` - Get user preferences (daily word goal, locale, theme)
- `PUT /api/users/me/preferences` - Update preferences
- `GET /api/users/me/privacy` - Get privacy settings and available features
- `PUT /api/users/me/privacy` - Upgrade privacy tier (requires HE public key, consent timestamp)
- `DELETE /api/users/me/privacy/revoke` - Downgrade to local_only (deletes all cloud data)

### Tags (`/api/tags`)
- `GET /api/tags` - List all user tags
- `POST /api/tags` - Create tag (auto-deduplicates by name, auto-generates color)
- `DELETE /api/tags/cleanup` - Delete stale tags (unused for N days)

### Encryption (`/api/encryption`)
- `GET /api/encryption/context` - Get HE context for client-side encryption (CKKS parameters)
- `POST /api/encryption/metrics` - Upload HE-encrypted metrics (requires analytics_sync or full_sync)
- `POST /api/encryption/aggregate` - Aggregate metrics homomorphically (sum or average)

### Sync (`/api/sync`)
- `POST /api/sync/backup` - Upload encrypted backup (returns 409 if conflict detected)
- `GET /api/sync/backups` - Fetch encrypted backups (with filters: since, device_id, limit)
- `DELETE /api/sync/backup/{id}` - Delete specific backup
- `GET /api/sync/conflicts` - List unresolved sync conflicts
- `POST /api/sync/conflicts/{id}/resolve` - Resolve conflict (choose local/remote/merged)

All sync endpoints require `full_sync` privacy tier.

## Database Schema

### Core Models
- **User**: Accounts with privacy tier, HE public key, preferences
- **Tag**: User-scoped tags with colors and usage tracking
- **EncryptedMetric**: HE-encrypted analytics (word count, sentiment, etc.)
- **EncryptedBackup**: AES-256 encrypted content and embeddings for sync
- **SyncConflict**: Conflict records with local/remote versions for user resolution

All models use SQLAlchemy 2.0 `Mapped[T]` type annotations.

## Testing

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/api/test_encryption.py
pytest tests/api/test_sync.py
pytest tests/services/test_he_service.py

# Run with coverage
pytest --cov=app tests/
```

**Test Stats**: 108 tests, 100% pass rate, 21.90s execution time

**Test Coverage**:
- Encryption API (HE context, metrics upload, aggregation)
- Sync API (backup CRUD, conflict resolution)
- Privacy tier validation (upgrade/downgrade flows)
- HE service operations (encrypt, decrypt, aggregate)
- Sync service logic (conflict detection)

## Development

### Environment Variables

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

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Development Reset

For testing, use the `dev_reset.py` utility to reset databases and create test users:

```bash
# Reset databases and create test users
python dev_reset.py

# Reset and create users with rich journal data
python dev_reset.py --rich

# Only create users (skip database reset)
python dev_reset.py --skip-reset
```

**Test User Credentials**:
- Quick test: `test@example.com` / `testpass123`

## Production Readiness

**Before deploying to production**:

- [ ] Restrict CORS to frontend domain (currently allows all origins)
- [ ] Add rate limiting (e.g., slowapi)
- [ ] Enable HTTPS only
- [ ] Use strong SECRET_KEY (64+ random characters)
- [ ] Set up database backups
- [ ] Configure structured logging
- [ ] Add health check endpoint (`/health`)
- [ ] Set up monitoring (Sentry, DataDog, etc.)
- [ ] Review privacy policy compliance (GDPR, CCPA)
- [ ] Security audit (SQL injection, XSS, CSRF)
- [ ] Load testing (stress test HE operations)

## Architecture Notes

**Privacy Model**: Local-first with progressive enhancement. Users control what syncs.

**Encryption Flow**:
1. Client generates AES keys and HE keypair (never sent to server)
2. Client encrypts data locally before upload
3. Server stores encrypted blobs and performs homomorphic aggregations
4. Client fetches encrypted data and decrypts locally

**Conflict Detection**: Server detects conflicts when same log ID is uploaded with different timestamps from different device IDs. User resolves via client UI.

**Migration History**: 4 migrations created for privacy architecture (Nov 2025). Old plaintext system removed (11 tables dropped).

## Additional Documentation

For comprehensive API documentation, database schema details, and privacy architecture deep-dive, see `PENDING_CLAUDE.md`.

For privacy architecture specifics, see `docs/PRIVACY_ARCHITECTURE.md` (referenced in codebase).

## License

MIT License
