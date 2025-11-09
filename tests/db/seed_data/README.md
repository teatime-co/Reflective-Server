# Seed Data Files

This directory contains journal entry data for creating test users with rich, realistic content.

## Structure

Each JSON file represents a persona with their journal entries:

```
seed_data/
├── food_lover.json
├── researcher.json
├── hiker.json
└── README.md
```

## JSON File Format

Each persona file follows this structure:

```json
{
  "persona": {
    "name": "Display Name",
    "email": "user@example.com",
    "description": "Brief description of the persona",
    "test_scenarios": [
      "List of testing scenarios this persona enables",
      "e.g., 'Semantic search: specific query examples'",
      "e.g., 'Sentiment: emotional range covered'"
    ]
  },
  "entries": [
    {
      "title": "Entry Title (optional, for documentation)",
      "content": "Full journal entry text with hashtags",
      "tags": ["tag1", "tag2", "tag3"],
      "test_purpose": "What this entry is designed to test (documentation only)"
    }
  ]
}
```

## Fields Explained

### Persona Object
- **name**: Display name for the user account
- **email**: Login email (must match in rich_seed_data.py config)
- **description**: Brief persona description
- **test_scenarios**: Array of strings describing what this persona tests

### Entry Object
- **title**: (Optional) Short title for documentation/reference
- **content**: Full journal entry text
  - Can be multi-paragraph
  - Include hashtags (e.g., #tag) which will be extracted as tags
  - Length can vary (50-500 words for variety)
- **tags**: Array of tag strings to associate with this entry
- **test_purpose**: (Optional) Documentation explaining what this entry tests

## Current Personas

### Food Lover (`food_lover.json`)
- **Email**: love@food.com
- **Password**: foodlover123 (defined in rich_seed_data.py)
- **Entries**: 10
- **Theme**: Restaurant reviews, home cooking, culinary journey
- **Tests**: Semantic search, sentiment variety, progression narrative

### Researcher (`researcher.json`)
- **Email**: cell@apoptosis.com
- **Password**: researcher123 (defined in rich_seed_data.py)
- **Entries**: 10
- **Theme**: PhD journey, lab work, academic life
- **Tests**: Technical language, imposter syndrome → confidence arc, academic milestones

### Hiker (`hiker.json`)
- **Email**: hike@man.com
- **Password**: hiker123 (defined in rich_seed_data.py)
- **Entries**: 10
- **Theme**: Mountain hiking, wilderness experiences, outdoor growth
- **Tests**: Adventure variety, seasonal experiences, solo vs group, skill progression

## Adding a New Persona

1. Create a new JSON file in this directory (e.g., `musician.json`)
2. Follow the JSON structure above
3. Add configuration to `rich_seed_data.py`:

```python
personas_config = [
    # ... existing personas
    {
        "filename": "musician.json",
        "password": "musician123"
    }
]
```

4. Run the seed script: `python tests/db/rich_seed_data.py`

## Editing Entries

To modify existing entries:

1. Edit the JSON file directly
2. The `title` and `test_purpose` fields are for documentation only
3. Make sure `tags` array matches hashtags in content
4. Test by running: `python dev_reset.py --rich`

## Design Guidelines

When creating seed data, consider:

### Variety
- **Length**: Mix short (50-100 words) and long (300-500 words) entries
- **Sentiment**: Include positive, negative, neutral, and mixed emotions
- **Tone**: Vary between excited, reflective, frustrated, analytical

### Testing Features
- **Semantic Search**: Include entries that discuss similar concepts with different words
  - Example: "lab breakthrough" and "research success" should be semantically similar
- **Keyword Search**: Use consistent tags across related entries
- **Sentiment Analysis**: Cover full emotional spectrum
- **Theme Detection**: Create recurring topics/themes across multiple entries

### Narrative Arc
- **Progression**: Show growth or change over time
  - Food Lover: novice → confident home cook
  - Researcher: imposter syndrome → emerging scientist
  - Hiker: casual hiker → technical mountaineer
- **Callbacks**: Reference previous entries
  - Example: "After the sourdough failure from last week, I tried pizza..."

### Realism
- **Specific Details**: Use real locations, brands, techniques
- **Natural Language**: Write as people actually journal, not formally
- **Hashtags**: Include relevant hashtags naturally in content

## Usage

The seed data is loaded by `rich_seed_data.py`:

```bash
# Through dev_reset utility (recommended)
python dev_reset.py --rich

# Directly (requires server running)
python tests/db/rich_seed_data.py
```

## Benefits of JSON Format

- **Maintainable**: Easy to edit entries without touching Python code
- **Readable**: Non-programmers can add/modify content
- **Versioned**: Track changes to seed data in git
- **Portable**: Can be used by other tools or scripts
- **Clean Code**: Keeps data separate from logic

## Example: Adding a New Entry

To add a new entry to an existing persona:

```json
{
  "title": "My New Entry",
  "content": "Today I discovered something amazing... #discovery #joy",
  "tags": ["discovery", "joy"],
  "test_purpose": "Tests positive sentiment and discovery theme"
}
```

Add it to the `"entries"` array in the appropriate JSON file, then re-run the seed script.
