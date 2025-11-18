# Reflective Server - Technical Architecture

Technical reference for the Reflective Server backend implementation.

## System Overview

### Architecture Pattern

Zero-knowledge backend with three-tier privacy model. Server provides sync and analytics aggregation without seeing plaintext user data.

**Implementation**:
- Client-side encryption (AES-256, CKKS homomorphic encryption)
- Server stores encrypted blobs and metadata for coordination
- Conflict detection uses timestamps and device IDs only

### Application Structure

```
reflective-server/
├── app/
│   ├── api/              # FastAPI route handlers
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic validation schemas
│   ├── services/         # Business logic (auth, HE, sync)
│   ├── core/             # Configuration and utilities
│   ├── database.py       # DB session management
│   └── main.py           # App initialization
├── alembic/versions/     # Database migrations (17 total)
├── tests/                # Test suite (108 tests)
└── docs/                 # Additional documentation
```

**Layers**:
- Routes (`/app/api/*.py`) handle HTTP, validate with Pydantic, call services
- Services (`/app/services/*.py`) contain business logic, interact with models
- Models (`/app/models/models.py`) define database schema with SQLAlchemy 2.0

## Technology Stack


| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | 0.104.1 |
| Database | PostgreSQL | 14+ |
| ORM | SQLAlchemy | 2.0.23 |
| HE Library | TenSEAL | 0.3.16 |
| Auth | python-jose + bcrypt | - |
| Migrations | Alembic | 1.12.1 |
| Validation | Pydantic | 2.5.1 |
| Testing | pytest | 7.4.3 |
| Server | uvicorn | 0.24.0 |
| Monitoring | prometheus-client | 0.19.0 |


## Data Flow

### Authentication

1. POST `/api/auth/token` with credentials (form-urlencoded)
2. `auth_service.authenticate_user()` validates bcrypt hash
3. JWT created with HS256, 30min expiration, payload: `{user_id, email, exp}`
4. Client sends token in `Authorization: Bearer <token>` header
5. `get_current_user()` dependency validates JWT and returns User object

### Homomorphic Encryption (Tier 2+)

1. Client fetches CKKS context from GET `/api/encryption/context` (public endpoint)
2. Client encrypts metrics locally using TenSEAL with server's context
3. POST `/api/encryption/metrics` with base64-encoded ciphertexts
4. Server stores in `encrypted_metrics` table (LargeBinary column)
5. Client requests aggregation via POST `/api/encryption/aggregate` (sum/average)
6. `he_service.aggregate()` performs homomorphic operations on ciphertexts
7. Server returns encrypted result, client decrypts with secret key

**CKKS Parameters**: poly_modulus_degree=8192, scale=2^40, 128-bit security

### Encrypted Sync (Tier 3)

1. Client encrypts journal content with AES-256-GCM (random IV per entry)
2. POST `/api/sync/backup` with `{log_id, encrypted_content, content_iv, device_id, updated_at, ...}`
3. `sync_service.detect_conflict()` checks if same log_id exists with different timestamp + device_id
4. **Conflict detected**: Return 409, create SyncConflict record with both versions (still encrypted)
5. **No conflict**: Store in `encrypted_backups` table, return 201
6. Client periodically fetches GET `/api/sync/backups?since=<timestamp>&device_id=<exclude_self>`
7. Client decrypts fetched backups locally
8. User resolves conflicts via POST `/api/sync/conflicts/{id}/resolve` (local/remote/merged choice)

**Conflict Detection Logic**: `(log_id match) AND (updated_at differs) AND (device_id differs) = conflict`

## Database Schema

### Tables

**users**
- Stores accounts, privacy tier enum, HE public key, preferences
- Cascade deletes: tags, encrypted_metrics, encrypted_backups, sync_conflicts
- Indexes: email (unique)

**tags**
- User-scoped tags with color codes and last_used_at timestamp
- Unique constraint: (user_id, name)
- `Tag.get_or_create()` class method handles deduplication

**encrypted_metrics**
- Stores HE ciphertexts (LargeBinary), metric_type, timestamp
- Server never decrypts these values
- Indexes: (user_id, metric_type, timestamp) for aggregation queries

**encrypted_backups**
- Stores AES-encrypted journal content and embeddings (LargeBinary)
- Metadata: log_id, device_id, created_at, updated_at, IVs, auth tags
- Indexes: (user_id, updated_at), (user_id, log_id)

**sync_conflicts**
- Stores both encrypted versions (local + remote) with metadata
- Fields: local_encrypted_content, local_iv, local_updated_at, local_device_id, remote_*
- Boolean `resolved` flag for filtering unresolved conflicts
- Indexes: (user_id, resolved)

### Models Implementation

SQLAlchemy 2.0 with `Mapped[T]` type annotations. See `/app/models/models.py`.

## API Reference

Base: `http://localhost:8000/api`

All endpoints except `/auth/register`, `/auth/token`, `/encryption/context` require JWT.

### Endpoints by Domain

**Authentication** (`/api/auth`)
- POST `/register` - Create account, returns JWT
- POST `/token` - Login, returns JWT (30min expiration)

**Users** (`/api/users`)
- GET `/me` - Profile with stats
- PUT `/me` - Update display_name, timezone
- GET `/me/preferences` - Get daily_word_goal, locale, theme_preferences, etc.
- PUT `/me/preferences` - Update preferences
- GET `/me/privacy` - Get privacy tier and HE public key status
- PUT `/me/privacy` - Upgrade tier (requires he_public_key, consent_timestamp)
- DELETE `/me/privacy/revoke` - Downgrade to local_only, deletes all cloud data

**Tags** (`/api/tags`)
- GET `/` - List user's tags (alphabetical)
- POST `/` - Create tag (auto-deduplicates, generates color if not provided)
- DELETE `/cleanup?days=N` - Delete tags unused for N days

**Encryption** (`/api/encryption`)
- GET `/context` - HE context for client encryption (public, no auth)
- POST `/metrics` - Upload HE-encrypted metrics (Tier 2+)
- POST `/aggregate` - Aggregate metrics homomorphically (Tier 2+)

**Sync** (`/api/sync`)
- POST `/backup` - Upload encrypted backup (Tier 3, returns 409 if conflict)
- GET `/backups?since&device_id&limit` - Fetch backups (Tier 3, pagination)
- DELETE `/backup/{id}` - Delete specific backup (Tier 3)
- DELETE `/backup/content` - Delete all backups (Tier 3)
- DELETE `/metrics/all` - Delete all metrics (Tier 2+)
- GET `/conflicts` - List unresolved conflicts (Tier 3)
- POST `/conflicts/{id}/resolve` - Resolve conflict (Tier 3)

Full API docs with examples: `http://localhost:8000/docs`

## Encryption Implementation

### Homomorphic Encryption (CKKS)

**Library**: TenSEAL (Python wrapper for Microsoft SEAL)

**Context Parameters**:
- Scheme: CKKS (supports floating-point arithmetic)
- Poly modulus degree: 8192 (128-bit security)
- Scale: 2^40 (precision for float encoding)

**Supported Operations**:
- Addition (ciphertext + ciphertext)
- Scalar multiplication (ciphertext * plaintext_scalar)
- Averaging (sum of ciphertexts / count)

**Performance**: Encryption ~10ms, aggregation ~1ms per ciphertext, decryption ~5ms

**Implementation**: `/app/services/he_service.py`

### Symmetric Encryption (AES-256)

**Client-Side Only** (server never sees keys)

**Algorithm**: AES-256-GCM
- Random IV per encryption (stored with ciphertext)
- Authentication tag prevents tampering
- Keys stored in OS keychain (macOS Keychain, Windows Credential Manager)

**Workflow**: Client encrypts → uploads (content, IV, tag) → server stores LargeBinary → client fetches → decrypts locally

## Privacy Tier Transitions

### Upgrade Flow

**local_only → analytics_sync**:
- Client generates HE keypair (public key sent to server, secret key stays local)
- PUT `/api/users/me/privacy` with he_public_key, consent_timestamp
- Server updates privacy_tier column
- Client begins encrypting metrics and uploading

**analytics_sync → full_sync**:
- Client reuses HE keypair (or generates new one)
- PUT `/api/users/me/privacy` with updated tier
- Client encrypts journal content with AES-256 and uploads backups

### Downgrade Flow

**full_sync → analytics_sync**:
- DELETE `/api/sync/backup/content` (deletes all encrypted_backups)
- PUT `/api/users/me/privacy` to set tier to analytics_sync
- Local copies retained

**analytics_sync → local_only** OR **full_sync → local_only**:
- DELETE `/api/users/me/privacy/revoke`
- Server deletes: encrypted_metrics, encrypted_backups, sync_conflicts
- Returns counts of deleted records
- Local copies retained

## Testing

### Organization

- `/tests/api/` - Integration tests for all endpoints
- `/tests/services/` - Unit tests for business logic
- `/tests/core/` - Utility tests
- `/tests/conftest.py` - Fixtures (test DB, test users with JWTs, test client)

### Running Tests

```bash
pytest                          # All tests
pytest tests/api/test_sync.py   # Specific suite
pytest --cov=app tests/         # With coverage
```

**Stats**: 108 tests, 100% pass rate, 21.90s execution

### Test Database

- Uses separate test database (configured in pytest.ini)
- Transaction rollback per test for isolation
- Fixtures create users with pre-generated JWT tokens for each tier

## Development

### Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit DATABASE_URL and SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

**Environment Variables**:
- DATABASE_URL (required): PostgreSQL connection string
- SECRET_KEY (required): JWT signing key
- ALGORITHM (optional): Default HS256
- ACCESS_TOKEN_EXPIRE_MINUTES (optional): Default 30

### Database Migrations

```bash
alembic revision --autogenerate -m "description"  # Create
alembic upgrade head                              # Apply
alembic downgrade -1                              # Rollback
```

### Development Utilities

**dev_reset.py** - Reset PostgreSQL database and create test users

```bash
python dev_reset.py                 # Interactive reset
python dev_reset.py --no-confirm    # Skip confirmation
python dev_reset.py --skip-reset    # Users only
```

**Test Users**: test@example.com, love@food.com, cell@apoptosis.com, hike@man.com (all password: *pass123)

## Performance

### Database Indexing

**Composite Indexes**:
- `encrypted_metrics(user_id, metric_type, timestamp)` - Aggregation queries
- `encrypted_backups(user_id, updated_at)` - Sync since queries
- `sync_conflicts(user_id, resolved)` - Unresolved conflict queries
- `tags(user_id, name)` - Unique constraint, get_or_create queries

**Single Indexes**:
- `users(email)` - Login lookups
- `tags(last_used_at)` - Stale cleanup queries

### Query Optimization

- Pagination with `limit` parameter (max 500 per request)
- Time-range filtering on indexed timestamp columns
- User-scoped queries (all queries filter by user_id from JWT)

### Bottlenecks

- HE aggregation: 1-2s for 1000 metrics (CPU-bound)
- Batch metric upload: ~10ms per metric
- Conflict detection: Early return on first match

## Security

### Authentication

- Bcrypt password hashing with automatic salts
- JWT tokens: HS256, 30min expiration, SECRET_KEY from env
- `get_current_user()` dependency validates all protected routes
- User-scoped queries prevent cross-user access

### Data Protection

- Client-side encryption (server never sees keys)
- Encrypted data stored as PostgreSQL LargeBinary
- Base64 encoding for JSON transport
- Pydantic validation on all inputs

### CORS Configuration

**Development**: `allow_origins=["*"]` in `/app/main.py`

**Production**: MUST restrict to frontend domain

### Rate Limiting

Not implemented. Planned: per-user upload limits, per-IP request limits.

## Key Files

**Core Logic**:
- `/app/services/he_service.py` - CKKS context, aggregation
- `/app/services/sync_service.py` - Conflict detection, resolution
- `/app/services/auth_service.py` - User CRUD, JWT, password hashing
- `/app/api/sync.py` - Backup upload, conflict endpoints
- `/app/api/encryption.py` - HE context, metrics upload, aggregation

**Infrastructure**:
- `/app/main.py` - App initialization, router registration, CORS
- `/app/database.py` - PostgreSQL session management
- `/app/models/models.py` - SQLAlchemy ORM models
- `/alembic/env.py` - Migration environment

**Testing**:
- `/tests/conftest.py` - Test fixtures and database setup
- `/tests/api/` - API integration tests
- `/tests/services/` - Service unit tests

