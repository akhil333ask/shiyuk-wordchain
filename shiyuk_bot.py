import asyncio
import os
import re
import random
import urllib.request
from telethon import TelegramClient, events
from flask import Flask
from threading import Thread

# ==========================================
# 📚 DICTIONARY DOWNLOADER (The Brain)
# ==========================================
print("📚 Downloading English dictionary for SHIYUK...")
try:
    url = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
    response = urllib.request.urlopen(url)
    VALID_WORDS = {w.decode('utf-8').strip().lower() for w in response.read().splitlines() if w.decode('utf-8').strip().isalpha()}
    print(f"✅ Loaded {len(VALID_WORDS)} valid words into memory.")
except Exception as e:
    print(f"⚠️ Failed to download dictionary: {e}. Bot cannot function without it.")
    VALID_WORDS = set()

# ==========================================
# 🌐 KEEP-ALIVE SERVER
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "SHIYUK WordChain Algorithmic Bot is running!"

def run_server():
    try:
        # SHIYUK runs on Port 8080
        port = int(os.environ.get('PORT', 8080)) 
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"ℹ️ Local Port Note: Web server paused locally ({e}).")

Thread(target=run_server, daemon=True).start()

# ==========================================
# 🤖 BOT CONFIGURATION & CREDENTIALS
# ==========================================
API_ID = 34989469
API_HASH = '3d8e9f2619d7d993d1f943181eb4e8c3'

MY_USERNAME = "SHIYUK"  
GAME_BOT = "on9wordchainbot"   

client = TelegramClient(f'wordchain_{MY_USERNAME}', API_ID, API_HASH)

game_state = {
    "is_game_active": False,
    "my_turn": False,            
    "current_constraints": "",
    "used_words": set(),         
    "last_group_id": None,
    "last_submitted_word": "" 
}

# ==========================================
# ⚙️ PURE ALGORITHMIC SOLVER
# ==========================================
async def submit_word(chat_id, is_retry=False):
    try:
        if not VALID_WORDS:
            print("❌ Dictionary is empty. Cannot play.")
            return

        print("🔍 Scanning dictionary for the perfect word...")
        
        start_match = re.search(r'start with ([a-z])', game_state["current_constraints"], re.IGNORECASE)
        length_match = re.search(r'at least (\d+) letters', game_state["current_constraints"], re.IGNORECASE)
        include_match = re.search(r'(?:include|contain) ([a-z])', game_state["current_constraints"], re.IGNORECASE)

        s_char = start_match.group(1).lower() if start_match else ""
        min_len = int(length_match.group(1)) if length_match else 1
        i_char = include_match.group(1).lower() if include_match else ""
        
        valid_options = []
        for w in VALID_WORDS:
            if s_char and not w.startswith(s_char): continue
            if len(w) < min_len: continue
            if i_char and i_char not in w: continue
            if w in game_state["used_words"]: continue
            valid_options.append(w)
            
        if valid_options:
            word = random.choice(valid_options)
            
            # STRICT DELAY TIMERS: 4.0s for normal play, 2.0s for error retry
            delay = 2.0 if is_retry else 4.0
            
            print(f"🎯 Found {len(valid_options)} options. Chose: '{word}'. Waiting exactly {delay}s...")
            
            await asyncio.sleep(delay)
            
            if game_state["my_turn"]:
                game_state["last_submitted_word"] = word 
                await client.send_message(chat_id, word)
        else:
            print("💀 Game Over: The dictionary contains no remaining words for these rules!")
            
    except Exception as e:
        print(f"❌ Error during dictionary search: {e}")

# ==========================================
# 📡 GAME EVENT LISTENERS
# ==========================================
@client.on(events.NewMessage(from_users=GAME_BOT))
async def master_game_handler(event):
    bot_text = event.raw_text.lower().replace('\n', ' ').replace('\r', ' ')
    
    if "is accepted." in bot_text:
        accepted_word = bot_text.split(" is accepted.")[0].split()[-1].strip()
        accepted_word = ''.join(filter(str.isalpha, accepted_word))
        game_state["used_words"].add(accepted_word)
        print(f"📝 Logged to Blacklist: '{accepted_word}'")
        
    if "turn:" in bot_text:
        game_state["is_game_active"] = True
        game_state["last_group_id"] = event.chat_id
        
        target_phrase = f"turn: {MY_USERNAME.lower()}"
        
        if target_phrase in bot_text:
            print("🎯 It's my turn! Turn Lock OPEN. Scanning...")
            game_state["my_turn"] = True
            game_state["current_constraints"] = bot_text
            asyncio.create_task(submit_word(event.chat_id, is_retry=False))
        else:
            game_state["my_turn"] = False

    error_phrases = [
        "has been used", "not a valid word", "invalid", 
        "not in my list of words", "has less than",      
        "does not include", "does not contain"
    ]
    
    if any(phrase in bot_text for phrase in error_phrases):
        if game_state["my_turn"]:
            if game_state["last_submitted_word"]:
                game_state["used_words"].add(game_state["last_submitted_word"])
                print(f"🚫 Added REJECTED word to Blacklist: '{game_state['last_submitted_word']}'")
            
            print("❌ Word rejected by game rules! Forcing a 2.0-second retry loop...")
            asyncio.create_task(submit_word(event.chat_id, is_retry=True))
        else:
            pass

    if "eliminated" in bot_text or "game over" in bot_text or "winner" in bot_text:
        print("🏁 Game over/Elimination detected. Wiping memory bank.")
        game_state["is_game_active"] = False
        game_state["my_turn"] = False
        game_state["used_words"].clear()
        game_state["last_submitted_word"] = ""

print(f"V14 Algorithmic Bot ({MY_USERNAME}) is running with Custom Delays!")
client.start()
client.run_until_disconnected()