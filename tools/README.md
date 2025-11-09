# Development Tools

This directory contains utility scripts for debugging and development.

## Available Tools

### `preview_weaviate.py`

Utility for inspecting the Weaviate vector database contents.

**Usage:**
```bash
python tools/preview_weaviate.py
```

This script helps you:
- View all entries in the Weaviate Log class
- Inspect embeddings and metadata
- Debug semantic search issues
- Verify data synchronization between PostgreSQL and Weaviate

**Prerequisites:**
- Weaviate must be running (default: `http://localhost:8080`)
- Database must contain data (use `python dev_reset.py --rich` to seed)

## Related Scripts

For database management and testing, see:
- `dev_reset.py` (project root) - Reset and seed development databases
- `tests/db/reset_dbs.py` - Low-level database reset functions
- `tests/db/rich_seed_data.py` - Create users with rich journal data

See [DEV_SETUP.md](../DEV_SETUP.md) for complete development workflow documentation.
