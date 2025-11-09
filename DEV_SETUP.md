# Development Setup Guide

## Quick Start: Reset & Test Environment

When testing the frontend, you'll often need to reset your development environment to a clean state with test users. Use the `dev_reset.py` utility for this.

### Basic Usage

```bash
# Full reset with basic test users (recommended for most testing)
python dev_reset.py

# Full reset with rich journal data (for testing search, themes, etc.)
python dev_reset.py --rich

# Only create users without resetting databases
python dev_reset.py --skip-reset

# Create a single custom test user
python dev_reset.py --user-only your.email@example.com
```

## Test User Credentials

### Quick Test User (Empty Account)
Perfect for testing account creation, first-time user experience, etc.

```
Email:    test@example.com
Password: testpass123
```

### Persona Accounts (With Rich Journal Data)

Each persona has **10 diverse entries** designed to test different features:

#### Food Lover (Culinary Explorer)
```
Email:    love@food.com
Password: foodlover123
```

**10 entries covering:**
- Restaurant discoveries (Italian trattoria, ramen shops, cafes)
- Home cooking successes and failures (sourdough disaster → pizza success)
- Farmer's market experiences
- Family cooking memories (Portuguese grandmother's soup)
- Fine dining critiques
- Cooking experiments (Thai curry from scratch)
- Food philosophy reflections

**Test scenarios:**
- Semantic search: "best restaurants", "cooking disasters", "Italian food"
- Sentiment: joy, frustration, nostalgia, disappointment
- Progression: evolution from novice to confident home cook
- Entry variety: short reviews (50 words) to long reflections (300+ words)

#### Cell Biology Researcher
```
Email:    cell@apoptosis.com
Password: researcher123
```

**10 entries covering:**
- Lab breakthroughs and experiment failures
- Imposter syndrome and self-doubt
- Conference experiences and networking
- Writing struggles (first paper)
- Work-life balance reflections
- Qualifying exam success
- Research collaboration
- First publication acceptance
- Future career planning

**Test scenarios:**
- Semantic search: "research breakthroughs", "feeling stressed", "academic pressure"
- Sentiment: imposter syndrome → growing confidence
- Technical language: apoptosis, mitochondria, CRISPR, cell biology
- PhD journey: from anxious student to confident scientist

#### Mountain Wanderer (Hiker)
```
Email:    hike@man.com
Password: hiker123
```

**10 entries covering:**
- Epic summits (Half Dome, Mount Russell)
- Failed attempts and safety decisions (winter Mount Baldy)
- Solo wilderness reflection
- Group hikes and community
- Trail running for joy
- Technical scrambling
- Hiking in challenging weather
- Training for long-distance (JMT prep)
- Wildlife encounters (bear)
- Personal growth through hiking

**Test scenarios:**
- Semantic search: "difficult climbs", "peaceful moments", "winter hiking"
- Sentiment: awe, fear, accomplishment, serenity
- Progression: skill development over time
- Varied experiences: solo vs group, success vs failure, different seasons

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

### Create a Journal Entry

```bash
curl -X POST http://localhost:8000/api/logs/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Today was a great day! I learned so much about FastAPI and Vue.js.",
    "tags": ["learning", "coding"],
    "completion_status": "complete"
  }'
```

### Search Journal Entries

```bash
curl -X POST http://localhost:8000/api/search/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "what did I learn about coding?",
    "limit": 5
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

2. **Weaviate Vector Database**
   - Data directory deleted
   - Schema recreated
   - Empty Log and Query classes

3. **Test Users Created**
   - 4 users with consistent credentials
   - Optional: Rich journal data via API

## Workflow Examples

### Testing Frontend Authentication Flow
```bash
# 1. Reset to clean state
python dev_reset.py

# 2. Start backend server
uvicorn app.main:app --reload

# 3. Use test@example.com / testpass123 in your frontend
```

### Testing Search and Theme Detection
```bash
# 1. Reset and seed with rich data
python dev_reset.py --rich

# 2. Wait for rich data creation (takes ~2-3 minutes for 30 entries)
# 3. Login as love@food.com / foodlover123
# 4. Test semantic search with queries like "what restaurants did I visit?"
```

## Comprehensive Testing Scenarios

The rich seed data is specifically designed to test these features:

### Semantic Search Testing

**Food Lover account** - Test with:
- `"best restaurants I've been to"` → Should find Italian trattoria, mention failures
- `"cooking disasters"` → Should find sourdough failure entry
- `"what made me happy about food"` → Farmer's market, grandmother's soup
- `"Italian food experiences"` → Trattoria, comparing to fancy restaurants

**Researcher account** - Test with:
- `"times I felt like a fraud"` → Imposter syndrome entries
- `"successful experiments"` → Breakthrough, collaboration, paper acceptance
- `"stressful moments"` → Contamination, writing struggles, work-life balance
- `"academic achievements"` → Qualifying exam, publication, future planning

**Hiker account** - Test with:
- `"dangerous situations in the mountains"` → Bear encounter, winter turnback
- `"peaceful outdoor moments"` → Solo wilderness, rain hike
- `"difficult climbs"` → Half Dome cables, scrambling
- `"what I learned from hiking"` → Reflection entries

### Keyword/Tag Search Testing

Each persona has consistent tags:
- **Food:** italian, baking, restaurant, homecooking, farmersmarket
- **Researcher:** research, phdlife, lab, conference, publication
- **Hiker:** hiking, summit, mountains, wilderness, solo/grouphike

Test filtering by tags, combining tags, tag popularity.

### Sentiment Analysis Testing

Each persona has emotional range:
- **Positive:** Joy, excitement, pride, gratitude, awe
- **Negative:** Frustration, disappointment, anxiety, fear, defeat
- **Mixed:** Reflective, nostalgic, bittersweet, complex emotions

### Theme Detection Testing

Recurring themes to test AI clustering:
- **Food:** authenticity vs pretension, home cooking, family traditions
- **Researcher:** imposter syndrome, scientific process, work-life balance
- **Hiker:** solo vs community, safety decisions, personal growth

### Entry Length Variety

- **Very short** (50-100 words): Food lover's ramen review
- **Medium** (150-250 words): Trail running, coffee shop discovery
- **Long** (300-400 words): Lab breakthroughs, Half Dome summit, cooking reflections

### Temporal Progression Testing

Each account shows growth over time:
- **Food:** Novice → confident home cook
- **Researcher:** Anxious student → emerging scientist
- **Hiker:** Casual hiker → technical mountaineer

Test "show me my progress" or "how have I changed" queries.

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

### "Error resetting Weaviate"
- Ensure Weaviate is running: `curl http://localhost:8080/v1/.well-known/ready`
- Check `weaviate-data` directory permissions
- Try manually deleting: `rm -rf weaviate-data`

### Rich data seeding fails
- Ensure backend server is running: `uvicorn app.main:app --reload`
- Check API is accessible: `curl http://localhost:8000/docs`
- Verify all required services are up (PostgreSQL, Weaviate, Ollama)

## Environment Variables

Required in `.env`:

```env
# Database
DATABASE_URL=postgresql://user@localhost/reflective

# Authentication
SECRET_KEY=your_secret_key_here

# Weaviate
WEAVIATE_URL=http://localhost:8080

# Optional: For rich data seeding with embeddings
OLLAMA_BASE_URL=http://localhost:11434
```

## Advanced: Manual Database Operations

If you need finer control:

```bash
# Reset databases only (no user creation)
python -c "from tests.db.reset_dbs import reset_databases; reset_databases()"

# Create rich data only (requires server running)
python tests/db/rich_seed_data.py
```

## Development Tools

Additional utilities are available in the `tools/` directory:

```bash
# Inspect Weaviate vector database contents
python tools/preview_weaviate.py
```

See [tools/README.md](tools/README.md) for more information.

## Tips for Efficient Testing

1. **Use the quick test user** for most frontend testing (test@example.com)
2. **Use --skip-reset** when you just need to add more test users
3. **Use --rich** when testing NLP features, search, or themes
4. **Create custom users** when testing specific email formats or edge cases

## Next Steps

- Read the [API documentation](http://localhost:8000/docs) (when server is running)
- Explore the [test files](tests/) for more usage examples
- Check [README.md](README.md) for overall project documentation
