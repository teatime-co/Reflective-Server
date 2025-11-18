# Development Setup Guide

## Quick Start: Reset & Test Environment

When testing the frontend, you'll often need to reset your development environment to a clean state with test users. Use the `dev_reset.py` utility for this.

### Basic Usage

```bash
# Full reset with test users (recommended for most testing)
python dev_reset.py

# Only create users without resetting databases
python dev_reset.py --skip-reset

# Create a single custom test user
python dev_reset.py --user-only your.email@example.com
```

## Test User Credentials

All test accounts start **empty** with no journal entries. They're useful for testing authentication, privacy tiers, tag management, and encrypted sync features.

### Test Accounts

```
Email:    test@example.com
Password: testpass123
```

```
Email:    love@food.com
Password: foodlover123
```

```
Email:    cell@apoptosis.com
Password: researcher123
```

```
Email:    hike@man.com
Password: hiker123
```

**Note**: All accounts have `local_only` privacy tier by default. You can test privacy tier upgrades (to `analytics_sync` or `full_sync`) through the API.

## API Testing Examples

### Login and Get Token

```bash
curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=testpass123"
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbG...",
  "token_type": "bearer"
}
```

### Check Privacy Settings

```bash
curl -X GET http://localhost:8000/api/users/me/privacy \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

Response:
```json
{
  "current_tier": "local_only",
  "sync_enabled": false,
  "features_available": {
    "local_storage": true,
    "cloud_sync": false,
    "analytics_aggregation": false
  }
}
```

### Create a Tag

```bash
curl -X POST http://localhost:8000/api/tags \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "learning",
    "color": "#3A7FBD"
  }'
```

### Upgrade Privacy Tier

```bash
curl -X PUT http://localhost:8000/api/users/me/privacy \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "privacy_tier": "analytics_sync",
    "consent_timestamp": "2025-11-14T10:00:00Z",
    "he_public_key": "base64_encoded_public_key"
  }'
```

## Safety Features

The `dev_reset.py` script includes safety checks:

- **Database URL Check**: Only runs on localhost/127.0.0.1
- **Confirmation Prompt**: Asks before deleting data
- **Environment Variables**: Reads from `.env` file

This prevents accidental data deletion in production environments.

## What Gets Reset

When you run `python dev_reset.py`:

1. **PostgreSQL Database**
   - All tables dropped and recreated
   - Alembic migrations applied
   - Fresh schema
   - Tables: users, tags, encrypted_metrics, encrypted_backups, sync_conflicts

2. **Test Users Created**
   - 4 users with consistent credentials
   - All accounts start empty (no journal entries)

## Workflow Examples

### Testing Frontend Authentication Flow
```bash
# 1. Reset to clean state
python dev_reset.py

# 2. Start backend server (run this in a separate terminal)
uvicorn app.main:app --reload

# 3. Use test@example.com / testpass123 in your frontend
```

### Testing Privacy Tiers
```bash
# 1. Login as any test user
# 2. Test tier upgrade: local_only → analytics_sync
# 3. Upload encrypted metrics
# 4. Request aggregated analytics
# 5. Test tier upgrade: analytics_sync → full_sync
# 6. Test encrypted backup sync
# 7. Test conflict resolution with multiple devices
```

### Testing Tag Management
```bash
# 1. Create tags via API
# 2. List all user tags
# 3. Test tag cleanup (delete stale tags)
```

### Testing with Custom User
```bash
# Create a user with specific email for testing
python dev_reset.py --user-only alice@test.com

# Follow prompts to set password and display name
```

## Troubleshooting

### "DATABASE_URL does not appear to be localhost"
- Check your `.env` file
- Ensure `DATABASE_URL` contains `localhost` or `127.0.0.1`
- Example: `postgresql://user@localhost/reflective`

### "Failed to reset PostgreSQL"
- Make sure PostgreSQL is running: `pg_isready`
- Check database exists: `psql -l | grep reflective`
- Verify database permissions

### User creation fails
- Check PostgreSQL is accessible
- Verify DATABASE_URL is correct in `.env`
- Check Alembic migrations are up to date: `alembic current`

## Environment Variables

Required in `.env`:

```env
# Database
DATABASE_URL=postgresql://user@localhost/reflective

# Authentication
SECRET_KEY=your_secret_key_here
```

## Advanced: Manual Database Operations

If you need finer control:

```bash
# Run Alembic migrations
alembic upgrade head

# Check current migration version
alembic current

# Rollback one migration
alembic downgrade -1

# Create new migration
alembic revision --autogenerate -m "description"
```

## Tips for Efficient Testing

1. **Use the quick test user** for most frontend testing (test@example.com)
2. **Use --skip-reset** when you just need to add more test users without wiping the database
3. **Create custom users** when testing specific email formats or edge cases
4. **Test privacy tiers** to verify encrypted sync and analytics features work correctly
5. **Run pytest** to verify all 108 tests pass after making changes

## Next Steps

- Read the [API documentation](http://localhost:8000/docs) (when server is running)
- Check [README.md](README.md) for project overview and mission
- See [ARCHITECTURE.md](ARCHITECTURE.md) for technical implementation details
- Explore the [test files](tests/) for usage examples
