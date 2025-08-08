#!/usr/bin/env python3
"""
Rich seed script to create users and diverse journal entries for NLP testing.
This script uses the actual API endpoints to ensure proper backend processing.
Usage: python rich_seed_data.py
"""

import sys
import os
import requests
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import time

# Add the app directory to the Python path
current_dir = Path(__file__).parent
app_dir = current_dir / "app"
sys.path.insert(0, str(app_dir))

# API Configuration
BASE_URL = "http://localhost:8000/api"
HEADERS = {"Content-Type": "application/json"}

def register_user(email: str, password: str, display_name: str) -> dict:
    """Register a new user via API"""
    user_data = {
        "email": email,
        "password": password,
        "display_name": display_name
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=user_data, headers=HEADERS)
    if response.status_code == 201:
        print(f"✓ Created user: {email}")
        return response.json()
    elif response.status_code == 400 and "already registered" in response.json().get("detail", ""):
        print(f"⚠ User {email} already exists")
        return None
    else:
        print(f"✗ Failed to create user {email}: {response.status_code} - {response.text}")
        return None

def login_user(email: str, password: str) -> str:
    """Login and get access token"""
    login_data = {
        "username": email,  # FastAPI OAuth2PasswordRequestForm uses 'username' field
        "password": password
    }
    
    response = requests.post(f"{BASE_URL}/auth/token", data=login_data)
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✓ Logged in as {email}")
        return token
    else:
        print(f"✗ Failed to login {email}: {response.status_code} - {response.text}")
        return None

def create_log_entry(token: str, content: str, tags: list = None, completion_status: str = "complete") -> dict:
    """Create a log entry via API"""
    if tags is None:
        tags = []
    
    log_data = {
        "id": str(uuid.uuid4()),
        "content": content,
        "tags": tags,
        "completion_status": completion_status,
        "target_word_count": 750
        # Note: NOT setting mood_score - let backend compute it if needed
    }
    
    auth_headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/logs/", json=log_data, headers=auth_headers)
    
    if response.status_code == 201:
        log = response.json()
        print(f"  ✓ Created log entry ({len(content.split())} words)")
        return log
    else:
        print(f"  ✗ Failed to create log: {response.status_code} - {response.text}")
        return None

def process_linguistic_metrics(token: str, log_id: str):
    """Process linguistic metrics for a log entry"""
    auth_headers = {**HEADERS, "Authorization": f"Bearer {token}"}
    response = requests.post(f"{BASE_URL}/linguistic/process/{log_id}", headers=auth_headers)
    
    if response.status_code == 200:
        print(f"  ✓ Processed linguistic metrics")
        return response.json()
    else:
        print(f"  ⚠ Could not process linguistics: {response.status_code}")
        return None

def seed_foodie_data(token: str):
    """Create rich journal entries for the foodie user"""
    print("🍴 Creating foodie journal entries...")
    
    entries = [
        {
            "content": """Today I discovered the most incredible little ramen shop tucked away in a narrow alley downtown. The moment I stepped inside, the rich aroma of tonkotsu broth enveloped me like a warm hug. The chef, an elderly Japanese man with weathered hands, worked with such precision and grace that I couldn't help but watch in awe.

The ramen itself was transcendent. The broth had been simmering for 18 hours, creating layers of complexity that unfolded with each spoonful. The chashu pork melted on my tongue, and the handmade noodles had just the right amount of chew. But what really moved me was the chef's dedication to his craft - every bowl was a work of art.

I spent two hours there, savoring not just the food but the entire experience. This is why I love food so much - it's not just sustenance, it's culture, art, and human connection all rolled into one beautiful moment. #ramen #authentic #craftsmanship #downtown #discovery""",
            "tags": ["ramen", "authentic", "craftsmanship", "downtown", "discovery"]
        },
        {
            "content": """Attempted to recreate my grandmother's apple pie recipe today, and wow, was that humbling. I thought I remembered everything perfectly, but there are so many little details that make the difference between good and extraordinary.

The crust was my biggest challenge. Grandma always said 'cold hands, cold butter, hot oven' but she never explained the feel of the dough when it's just right. After three attempts, I finally got that perfect flaky texture that shatters delicately under your fork.

The filling was another story entirely. I realized I'd been measuring the spices wrong all these years. It's not about the exact amounts - it's about tasting as you go, adjusting based on the sweetness of the apples, the humidity in the air, even your own mood that day.

When I finally pulled that golden-brown pie from the oven, the kitchen smelled exactly like Grandma's house on Sunday afternoons. I may not have her recipe perfectly memorized, but I think I'm finally understanding her approach to cooking: it's not about following rules, it's about feeling your way through with love and intuition. #baking #family #tradition #applepie #memories #learning""",
            "tags": ["baking", "family", "tradition", "applepie", "memories", "learning"]
        },
        {
            "content": """Had the most frustrating dining experience tonight at what was supposed to be an upscale fusion restaurant. The reviews were glowing, the ambiance was Instagram-perfect, but the food was such a disappointment.

They took beautiful, high-quality ingredients and completely missed the mark. The 'Korean-Mexican fusion tacos' sounded innovative on paper, but in reality, the kimchi overpowered everything else, and the bulgogi was underseasoned and overcooked. It felt like they were trying so hard to be different that they forgot to make it delicious.

What really bothered me wasn't just the poor execution - it was the disconnect between the restaurant's pretensions and the actual care put into the food. The server couldn't even explain what was in half the dishes. Compare that to the ramen chef from last week who could tell you the story behind every ingredient.

This experience reminded me that good food isn't about complexity or trends. It's about understanding flavors, respecting ingredients, and cooking with genuine passion. Sometimes the simplest dishes, made with care and skill, are infinitely more satisfying than elaborate creations that lack soul. #fusion #disappointment #authentic #overhyped #trends #foodculture""",
            "tags": ["fusion", "disappointment", "authentic", "overhyped", "trends", "foodculture"]
        },
        {
            "content": """Spent the morning at the farmer's market and I'm still buzzing with excitement! There's something magical about connecting directly with the people who grow your food. I talked with Maria, who's been growing heirloom tomatoes for thirty years, and she taught me how to select the perfect ones - look for the star-shaped pattern at the bottom, she said.

Brought home a bounty: purple Cherokee tomatoes, Japanese cucumbers, wild fennel, and the most fragrant basil I've ever encountered. For lunch, I made the simplest possible caprese salad, letting each ingredient shine on its own. The tomatoes were so sweet and complex, nothing like the flavorless ones from the supermarket.

The farmers here aren't just vendors, they're artisans. They understand their plants intimately, know exactly when each variety reaches peak flavor, and they're passionate about sharing that knowledge. It makes me want to start my own garden, to be part of this beautiful cycle of growth and nourishment.

Food tastes different when you know its story, when you can shake hands with the person who nurtured it from seed to harvest. This is what I want more of in my life - real connections to real food. #farmersmarket #heirloom #local #seasonal #connections #gardening #fresh""",
            "tags": ["farmersmarket", "heirloom", "local", "seasonal", "connections", "gardening", "fresh"]
        }
    ]
    
    for entry in entries:
        log = create_log_entry(token, entry["content"], entry["tags"])
        if log:
            # Process linguistic metrics
            time.sleep(1)  # Brief pause between requests
            process_linguistic_metrics(token, log["id"])

def seed_phd_data(token: str):
    """Create rich journal entries for the PhD student"""
    print("🔬 Creating PhD student journal entries...")
    
    entries = [
        {
            "content": """Breakthrough day in the lab! After six months of failed experiments, I finally got the cell culture conditions right for observing apoptosis in real-time. The fluorescent markers are lighting up exactly as predicted by the theoretical model, showing the cascade of caspase activation that leads to programmed cell death.

What fascinates me most is how elegant this process is at the molecular level. Cells don't just die randomly - they follow an intricate protocol, methodically dismantling themselves in a way that protects neighboring cells. It's like watching a perfectly choreographed dance of destruction and renewal.

Today's success validates months of troubleshooting. The pH buffer was too alkaline, the temperature gradient was inconsistent, and I was using the wrong concentration of growth factors. Science is humbling that way - one tiny variable can derail everything, but when you get it right, the beauty of natural systems reveals itself.

My advisor Dr. Chen was thrilled when I showed her the time-lapse footage. She said this could be the foundation for my dissertation. More importantly, this research could lead to better cancer therapies by understanding how to trigger apoptosis in tumor cells while protecting healthy tissue. #research #apoptosis #breakthrough #cellbiology #cancer #labwork #phd""",
            "tags": ["research", "apoptosis", "breakthrough", "cellbiology", "cancer", "labwork", "phd"]
        },
        {
            "content": """Defending my research proposal next week and I'm a nervous wreck. Spent the entire weekend refining my presentation, trying to anticipate every possible question the committee might ask. The impostor syndrome is hitting hard - who am I to think I can contribute something meaningful to cellular biology?

But then I look at my data, at the countless hours of careful observation and meticulous documentation, and I remember why I fell in love with science in the first place. There's something profoundly satisfying about asking questions that no one has asked before, about pushing the boundaries of human knowledge, even if it's just by a tiny increment.

My research on mitochondrial dysfunction in neurodegenerative diseases might seem narrow to outsiders, but I see it as part of a much larger puzzle. Every piece of data, every failed experiment, every unexpected result brings us closer to understanding how life works at its most fundamental level.

The committee includes some intimidating minds - Dr. Rodriguez published the seminal paper on oxidative stress that got me interested in this field in the first place. But I have to trust that my passion for this work will come through, that the long nights and weekend lab sessions have prepared me for this moment. #phdlife #defense #research #neuroscience #mitochondria #impostersyndrome #science""",
            "tags": ["phdlife", "defense", "research", "neuroscience", "mitochondria", "impostersyndrome", "science"]
        },
        {
            "content": """Conference season is exhausting but exhilarating. Just returned from the International Cell Biology Symposium in Boston, and my head is spinning with new ideas and potential collaborations. The keynote on CRISPR applications in studying developmental biology was mind-blowing - we're living in a golden age of molecular tools.

Met Dr. Sarah Kim from Stanford who's working on similar pathways but in plant cells. We spent two hours over coffee discussing the evolutionary conservation of apoptotic mechanisms across kingdoms. It's amazing how the fundamental processes of life transcend species boundaries - a dying human cell and a leaf cell preparing for autumn follow remarkably similar molecular scripts.

The poster session was both humbling and inspiring. Seeing the breadth of research happening worldwide reminds me that science is truly a collaborative endeavor. That graduate student from São Paulo studying programmed cell death in cancer stem cells might hold the key to questions I haven't even thought to ask yet.

Came home with a notebook full of ideas, three potential collaboration opportunities, and renewed enthusiasm for my own research. Sometimes you need to step back from the daily grind of pipettes and data analysis to remember that you're part of something much bigger - humanity's quest to understand the universe, one cell at a time. #conference #collaboration #CRISPR #evolution #networking #inspiration #cellbiology""",
            "tags": ["conference", "collaboration", "CRISPR", "evolution", "networking", "inspiration", "cellbiology"]
        },
        {
            "content": """The ethics committee approved my clinical trial proposal today, which is both thrilling and terrifying. We'll be testing whether our lab-developed compound can selectively induce apoptosis in melanoma cells while sparing healthy melanocytes. It's the culmination of four years of research moving from petri dish to actual human treatment.

The weight of responsibility is immense. Real patients will be trusting us with their lives based on our work. Every control experiment, every statistical analysis, every peer review comment suddenly feels monumentally important. There's no room for the kind of casual errors that you might overlook in basic research.

But there's also incredible excitement. If our hypothesis is correct, we could be offering hope to people facing one of the most aggressive forms of cancer. The molecular pathway we've identified - the interaction between p53 and the mitochondrial membrane during UV-induced DNA damage - could be the key to more targeted, less toxic treatments.

My labmates threw a small celebration, complete with cake decorated to look like a melanoma cell (morbid but endearing). Dr. Chen gave a toast about the responsibility we bear as translational researchers - to bridge the gap between scientific discovery and human healing. Tonight I feel the full weight and privilege of that calling. #clinicaltrial #melanoma #translation #ethics #responsibility #hope #cancerresearch""",
            "tags": ["clinicaltrial", "melanoma", "translation", "ethics", "responsibility", "hope", "cancerresearch"]
        }
    ]
    
    for entry in entries:
        log = create_log_entry(token, entry["content"], entry["tags"])
        if log:
            time.sleep(1)
            process_linguistic_metrics(token, log["id"])

def seed_hiker_data(token: str):
    """Create rich journal entries for the hiker"""
    print("🥾 Creating hiker journal entries...")
    
    entries = [
        {
            "content": """Completed the Mist Trail to Half Dome today - 16 miles of pure challenge and absolute beauty. Started at 4 AM under a canopy of stars that gradually gave way to the golden glow of sunrise over the Sierra Nevada. There's something magical about being in motion while the world wakes up around you.

The ascent through the mist from Vernal Falls was like walking through clouds. Every step forward revealed new perspectives - towering granite faces that have stood for millions of years, ancient trees that have weathered countless storms, wildflowers that somehow find purchase in seemingly impossible cracks in the rock.

But the real test came with the cable section up Half Dome's final face. Looking up at that nearly vertical wall of granite, cables stretching into the distance, I felt a familiar mix of terror and determination. Each step required complete focus - one hand over the other, one foot in front of the next, trusting in the worn metal cables and my own strength.

Reaching the summit was euphoric. The entire Yosemite Valley spread out below like a living map, the Merced River winding through emerald meadows, waterfalls cascading down granite walls. In that moment, all the effort, all the burning muscles and labored breathing, felt like a small price for this perspective. Nature has a way of putting human concerns into proper scale. #halfdome #yosemite #summit #granite #perspective #challenge #wilderness""",
            "tags": ["halfdome", "yosemite", "summit", "granite", "perspective", "challenge", "wilderness"]
        },
        {
            "content": """Got completely soaked on the Pacific Crest Trail today, but it was exactly what I needed. Sometimes you plan for sunshine and get storms instead, and that's when the real adventure begins. The rain started just as I reached the exposed ridge section - no shelter for miles, nothing to do but embrace it.

There's something liberating about being thoroughly drenched in the wilderness. All your careful gear planning, your attempts to stay dry and comfortable, suddenly become irrelevant. You're reduced to the essential experience of movement through landscape, of being a small, wet creature navigating the natural world on its own terms.

The trail became a rushing creek, my boots squelched with every step, and my supposedly waterproof jacket gave up the fight somewhere around mile eight. But the forest smelled incredible - that rich, earthy petrichor that only comes when rain awakens the sleeping scents of pine needles, wildflowers, and rich soil.

By the time I reached camp, I was laughing at my own soggy state. My hiking partner Jake looked like a drowned rat too, but we both had these huge grins. There's camaraderie in shared misery, and something deeply satisfying about discovering you can be uncomfortable and still completely happy. The mountains don't care about your comfort - they only care whether you're paying attention. #PCT #rain #embrace #discomfort #nature #camaraderie #wilderness""",
            "tags": ["PCT", "rain", "embrace", "discomfort", "nature", "camaraderie", "wilderness"]
        },
        {
            "content": """Today's solo hike up Mount Whitney reminded me why I need solitude in the mountains sometimes. No conversation, no shared pace to maintain, just me and the rhythm of my own breathing as I climbed through different elevation zones like ascending through separate worlds.

Started in the desert scrub at the trailhead - Joshua trees and scattered sage under a blazing California sun. Gradually climbed into pine forests where the air grew thinner and cooler, where every breath required more intention. Above treeline, the landscape became almost lunar - granite boulders and alpine lakes under an impossibly blue sky.

The final push to the summit at 14,505 feet was a meditation on persistence. Each step required conscious effort in the thin air. My mind quieted down to the essentials: breathe, step, breathe, step. No room for the usual mental chatter about work stress or relationship concerns or future plans.

Standing on the highest point in the continental US, looking out over hundreds of miles of peaks and valleys, I felt that familiar sense of being simultaneously significant and insignificant. Significant because I had carried myself to this place through my own effort and determination. Insignificant because the mountains were here long before me and will remain long after I'm gone. That paradox is one of the gifts the wilderness keeps giving me. #whitney #solo #altitude #meditation #perspective #effort #solitude #mountains""",
            "tags": ["whitney", "solo", "altitude", "meditation", "perspective", "effort", "solitude", "mountains"]
        },
        {
            "content": """Spent three days backpacking through the Olympic Peninsula rainforest, and I feel like I've been transported to another planet. The ecosystem here is unlike anything else - massive Sitka spruces draped in moss, ferns growing from every surface, streams that run crystal clear through valleys that see 12 feet of rain each year.

The silence here is different from desert silence or mountain silence. It's thick and alive, punctuated by the distant crash of Pacific waves, the call of ravens in the canopy, the whisper of wind through moss-laden branches. Every surface is soft - even the rocks are cushioned with inches of moss and lichen.

I made camp beside the Hoh River, where salmon were running upstream in their ancient migration. Watched them fight against the current with such determination, their bodies already beginning the transformation that will end in death but ensure the continuation of their species. There's something deeply moving about witnessing these primal cycles that have repeated for millennia.

The rain fell steadily each night, a gentle percussion on my tent that lulled me into the deepest sleep I've experienced in months. Woke each morning to mist rising from the river, shafts of sunlight piercing the canopy, and the profound sense that this place operates by rhythms far older and deeper than human time. The rainforest strips away the illusion that we control anything - here, you simply move at the pace nature allows. #olympic #rainforest #moss #salmon #cycles #ancient #pacific #rivers""",
            "tags": ["olympic", "rainforest", "moss", "salmon", "cycles", "ancient", "pacific", "rivers"]
        }
    ]
    
    for entry in entries:
        log = create_log_entry(token, entry["content"], entry["tags"])
        if log:
            time.sleep(1)
            process_linguistic_metrics(token, log["id"])

def main():
    """Main seeding function"""
    print("🌱 Starting rich data seeding...")
    print(f"API Base URL: {BASE_URL}")
    
    # Define users to create
    users = [
        {
            "email": "love@food.com",
            "password": "123456",
            "display_name": "Culinary Explorer",
            "seed_function": seed_foodie_data
        },
        {
            "email": "cell@apoptosis.com",
            "password": "123456", 
            "display_name": "Cell Biology Researcher",
            "seed_function": seed_phd_data
        },
        {
            "email": "hike@man.com",
            "password": "123456",
            "display_name": "Mountain Wanderer", 
            "seed_function": seed_hiker_data
        }
    ]
    
    # Process each user
    for user in users:
        print(f"\n👤 Processing user: {user['email']}")
        
        # Register user (or skip if exists)
        register_user(user["email"], user["password"], user["display_name"])
        
        # Login to get token
        token = login_user(user["email"], user["password"])
        if not token:
            print(f"⚠ Skipping data creation for {user['email']} - couldn't login")
            continue
        
        # Create rich journal entries
        try:
            user["seed_function"](token)
            print(f"✓ Completed data seeding for {user['email']}")
        except Exception as e:
            print(f"✗ Error seeding data for {user['email']}: {e}")
    
    print(f"\n🎉 Rich data seeding completed!")
    print(f"📊 Created users with diverse, semantically rich journal entries")
    print(f"🔍 All entries processed for linguistic metrics and semantic search")

if __name__ == "__main__":
    main() 