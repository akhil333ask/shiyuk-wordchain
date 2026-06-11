import asyncio
import os
import re
import random
import urllib.request
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from flask import Flask
from threading import Thread

# ==========================================
# 📚 DICTIONARY DOWNLOADER 
# ==========================================
print("📚 Downloading English dictionary for SHIYUK...", flush=True) 
try:
    url = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
    response = urllib.request.urlopen(url)
    VALID_WORDS = {w.decode('utf-8').strip().lower() for w in response.read().splitlines() if w.decode('utf-8').strip().isalpha()}
    print(f"✅ Loaded {len(VALID_WORDS)} valid words into memory.", flush=True)
except Exception as e:
    print(f"⚠️ Failed to download dictionary: {e}. Bot cannot function without it.", flush=True)
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
        port = int(os.environ.get('PORT', 8080)) 
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"ℹ️ Local Port Note: Web server paused locally ({e}).", flush=True)

Thread(target=run_server, daemon=True).start()

# ==========================================
# 🤖 BOT CONFIGURATION & CLOUD LOGIN
# ==========================================
API_ID = 34989469
API_HASH = '3d8e9f2619d7d993d1f943181eb4e8c3'
MY_USERNAME = "SHIYUK"  
GAME_BOT = "on9wordchainbot"   

SESSION_STRING = "1BVtsOG8Bu0vGTorGeN8Su6IfvnUvKT3UssOn1xiZZHdTAUS8VsKWJYykuKanuG3xpyBbtukjORI0SYVhyJvaLavuZg62dJttLaIfwDalOdVSN8IwKiYq-JgWjoUMLyVPJPytHY427yPQPDXLlo9ncDJt3iRTYxMygSGGb0Twvm8hp_ecjDMSfOupjNifZqzQ2X9QQFkTF76JOrqpECPDabl8zP5NQUNq_kkts6Q0t1XNUkialllZyZJmmS5LjGvq2l2YJjyIVurQi8u0-V-BDaxVIA3sxNhb_xdCCs2-YIBOHjjBY_y86KwKeERofz7TR1ikL4HWHfjCe017QKJknZKVvXWOSgs="

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# 🧠 MULTI-CHAT ISOLATION BANK
active_games = {}

def get_game_state(chat_id):
    if chat_id not in active_games:
        active_games[chat_id] = {
            "current_constraints": "",
            "used_words": set(),
            "last_submitted_word": ""
        }
    return active_games[chat_id]

# ==========================================
# ⚙️ PURE ALGORITHMIC SOLVER
# ==========================================
async def submit_word(chat_id, constraints, state, is_retry=False):
    try:
        if not VALID_WORDS:
            print("❌ Dictionary is empty. Cannot play.", flush=True)
            return

        print(f"[{chat_id}] 🔍 Scanning dictionary...", flush=True)
        
        start_match = re.search(r'start with ([a-z])', constraints, re.IGNORECASE)
        length_match = re.search(r'at least (\d+) letters', constraints, re.IGNORECASE)
        include_match = re.search(r'(?:include|contain) ([a-z])', constraints, re.IGNORECASE)

        s_char = start_match.group(1).lower() if start_match else ""
        min_len = int(length_match.group(1)) if length_match else 1
        i_char = include_match.group(1).lower() if include_match else ""
        
        valid_options = []
        for w in VALID_WORDS:
            if s_char and not w.startswith(s_char): continue
            if len(w) < min_len: continue
            if i_char and i_char not in w: continue
            if w in state["used_words"]: continue
            valid_options.append(w)
            
        if valid_options:
            # 🧠 NEW: Dynamic Length Buffer (Try to stay within +2 letters of the minimum)
            preferred_options = [w for w in valid_options if len(w) <= min_len + 2]
            
            if preferred_options:
                word = random.choice(preferred_options)
                print(f"[{chat_id}] 🎯 Smart Sizing Active: Chose '{word}' (Length: {len(word)}).", flush=True)
            else:
                word = random.choice(valid_options)
                print(f"[{chat_id}] ⚠️ Safety Net: No short words left. Falling back to '{word}'.", flush=True)
            
            delay = 2.0 if is_retry else 4.0
            print(f"[{chat_id}] ⏳ Waiting exactly {delay}s...", flush=True)
            
            await asyncio.sleep(delay)
            
            state["last_submitted_word"] = word 
            await client.send_message(chat_id, word)
        else:
            print(f"[{chat_id}] 💀 Game Over: The dictionary contains no remaining words for these rules!", flush=True)
            
    except Exception as e:
        print(f"❌ Error during dictionary search: {e}", flush=True)

# ==========================================
# 📡 GAME EVENT LISTENERS
# ==========================================
@client.on(events.NewMessage(from_users=GAME_BOT))
async def master_game_handler(event):
    chat_id = event.chat_id
    state = get_game_state(chat_id)
    bot_text = event.raw_text.lower().replace('\n', ' ').replace('\r', ' ')
    
    if "is accepted." in bot_text:
        accepted_word = bot_text.split(" is accepted.")[0].split()[-1].strip()
        accepted_word = ''.join(filter(str.isalpha, accepted_word))
        state["used_words"].add(accepted_word)
        print(f"[{chat_id}] 📝 Logged to Blacklist: '{accepted_word}'", flush=True)
        
    if "turn:" in bot_text:
        state["current_constraints"] = bot_text 
        target_phrase = f"turn: {MY_USERNAME.lower()}"
        
        if target_phrase in bot_text:
            print(f"[{chat_id}] 🎯 It's my turn! Turn Lock OPEN.", flush=True)
            asyncio.create_task(submit_word(chat_id, bot_text, state, is_retry=False))

    error_phrases = [
        "has been used", "not a valid word", "invalid", 
        "not in my list of words", "has less than",      
        "does not include", "does not contain"
    ]
    
    if any(phrase in bot_text for phrase in error_phrases):
        if MY_USERNAME.lower() in bot_text:
            if state["last_submitted_word"]:
                state["used_words"].add(state["last_submitted_word"])
                print(f"[{chat_id}] 🚫 Added REJECTED word to Blacklist: '{state['last_submitted_word']}'", flush=True)
            
            print(f"[{chat_id}] ❌ Word rejected! Forcing 2.0s retry...", flush=True)
            asyncio.create_task(submit_word(chat_id, state["current_constraints"], state, is_retry=True))

    if "eliminated" in bot_text or "game over" in bot_text or "winner" in bot_text:
        print(f"[{chat_id}] 🏁 Game over/Elimination detected. Wiping isolated memory.", flush=True)
        state["used_words"].clear()
        state["last_submitted_word"] = ""

print(f"V17 Smart Sizing Bot ({MY_USERNAME}) is running!", flush=True)
client.start()
client.run_until_disconnected()