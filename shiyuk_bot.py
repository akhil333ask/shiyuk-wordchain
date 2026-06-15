import asyncio
import os
import re
import random
import urllib.request
import json
import time
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from flask import Flask
from threading import Thread

# ==========================================
# 📚 DICTIONARY & JSON INJECTION
# ==========================================
print("📚 Downloading English dictionary for SHIYUK...", flush=True) 
try:
    url = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    VALID_WORDS = {w.decode('utf-8').strip().lower() for w in response.read().splitlines() if w.decode('utf-8').strip().isalpha()}
    print(f"✅ Loaded {len(VALID_WORDS)} base words into memory.", flush=True)
except Exception as e:
    print(f"⚠️ Failed to download dictionary: {e}", flush=True)
    VALID_WORDS = set()

# 🧠 INJECT CUSTOM VERIFIED JSON
JSON_DB_FILE = "verified_database.json"
if os.path.exists(JSON_DB_FILE):
    try:
        with open(JSON_DB_FILE, "r") as f:
            custom_data = json.load(f)
            added_count = 0
            for word, is_valid in custom_data.items():
                if is_valid and word not in VALID_WORDS:
                    VALID_WORDS.add(word)
                    added_count += 1
        print(f"🧬 Injected {added_count} custom verified words from {JSON_DB_FILE}.", flush=True)
    except Exception as e:
        print(f"⚠️ Failed to load custom JSON: {e}", flush=True)
else:
    print("ℹ️ No verified_database.json found. Running on base dictionary only.", flush=True)

# ==========================================
# 🌐 KEEP-ALIVE SERVER & WEB DASHBOARD
# ==========================================
app = Flask(__name__)
latest_diagnostic_report = "Bot is running. No games have been lost yet! 🚀"

@app.route('/')
def home():
    return "SHIYUK WordChain Algorithmic Bot is running! Go to /logs to view diagnostics."

@app.route('/logs')
def logs():
    return f"<body style='background-color:#1e1e1e; color:#00ff00; font-family:monospace; padding:20px;'><pre style='font-size:16px;'>{latest_diagnostic_report}</pre></body>"

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

# 🔑 HARDCODED SESSION STRING
SESSION_STRING = "1BVtsOG8Buw8lZYldaorQCkkSxpqRMUDxrn1qqCvHzlQfNsypt72Hy8W30MtCkC911vo60Jse-h8R3TU7w3-2bE9OOWAkPNtsQ6H_N7ueBRT_4yysTfxixPklujH-uD_hCY-VjCnojsAARmHLzsq-Vij_T5q2ZWqx-Le07TRWrjHLHhIBeRyEDIiMje_yLKerclONxzvfxlUFaKGYzD2Two9MOiDYidlAB8wshOqEpYFAACk1nziicGyx4Y9RyuNWk-9CuR_oJt62JwcpiLrPNilZnsWkK2jjdTgPZA_EqN_K1_7SNiM9sIynlPRbSQi30eiQRTJzngUkpvpKy2D9A4p1kpKSmNo="

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

active_games = {}

def get_game_state(chat_id):
    if chat_id not in active_games:
        active_games[chat_id] = {
            "current_constraints": "",
            "used_words": set(),
            "last_submitted_word": "",
            "my_turn": False,
            "turn_start_time": 0,
            "diagnostic_reason": "Waiting for a game to start...", 
            "word_ledger": {} 
        }
    return active_games[chat_id]

def update_dashboard(chat_id, state):
    global latest_diagnostic_report
    
    report = f"==================================================\n"
    report += f"💀 ELIMINATION DIAGNOSTIC REPORT\n"
    report += f"==================================================\n\n"
    report += f"❌ CAUSE OF DEATH:\n> {state['diagnostic_reason']}\n\n"
    
    report += f"📊 WORD LEDGER (History for this match):\n"
    if not state["word_ledger"]:
        report += "> No words were successfully played.\n"
    else:
        for letter in sorted(state["word_ledger"].keys()):
            words_played = ", ".join(state["word_ledger"][letter])
            report += f"- [{letter.upper()}]: {words_played}\n"
            
    report += f"\n==================================================\n"
    
    latest_diagnostic_report = report
    print(report, flush=True)

# ==========================================
# ⚙️ ADVANCED DIAGNOSTIC SOLVER (V25 OFFENSIVE PIPELINE)
# ==========================================
async def submit_word(chat_id, constraints, state, is_retry=False):
    if not is_retry:
        state["turn_start_time"] = time.time()
        
    try:
        state["diagnostic_reason"] = "Processing rules and scanning local dictionaries."
        
        start_match = re.search(r'start with ([a-z])', constraints, re.IGNORECASE)
        length_matches = re.findall(r'at least (\d+) letters', constraints, re.IGNORECASE)
        include_match = re.search(r'(?:include|contain) ([a-z])', constraints, re.IGNORECASE)

        s_char = start_match.group(1).lower() if start_match else ""
        min_len = int(length_matches[-1]) if length_matches else 1
        i_char = include_match.group(1).lower() if include_match else ""
        
        # Filter pool strictly by game rules first
        valid_options = []
        for w in VALID_WORDS:
            if s_char and not w.startswith(s_char): continue
            if len(w) < min_len: continue
            if i_char and i_char not in w: continue
            if w in state["used_words"]: continue
            valid_options.append(w)
            
        if valid_options:
            # 🎯 OFFENSIVE TARGET ENDINGS (Ordered by trapping difficulty)
            KILLER_ENDINGS = ['x', 'j', 'q', 'z', 'k', 'v', 'y']
            
            # Sort array ascending by length to guarantee ammo conservation baseline
            valid_options.sort(key=len)
            preferred_len_limit = min_len + 2
            
            # Categorize options into specific strategic tiers
            tier_1 = [w for w in valid_options if len(w) <= preferred_len_limit and w[-1] in KILLER_ENDINGS]
            tier_2 = [w for w in valid_options if w[-1] in KILLER_ENDINGS]
            tier_3 = [w for w in valid_options if len(w) <= preferred_len_limit]
            
            # Execution Routing
            if tier_1:
                # Short, lethal word available within length window. Random choice keeps it unpredictable.
                word = random.choice(tier_1)
                status_log = f"🔥 ATTACK TIER 1: Found short trap word '{word}' ending in '{word[-1]}'."
            elif tier_2:
                # Trap word exists but requires going past window. Take the absolute shortest one to save ammo.
                word = tier_2[0]
                status_log = f"💥 ATTACK TIER 2: Scaling length to {len(word)} for trap ending '{word[-1]}' with '{word}'."
            elif tier_3:
                # No offensive options available. Rollback to tight standard defense window.
                word = random.choice(tier_3)
                status_log = f"🛡️ ROLLBACK TIER 3: No trap vectors. Playing safe short word '{word}'."
            else:
                # Absolute fallback: take shortest valid word remaining
                word = valid_options[0]
                status_log = f"⚠️ FALLBACK TIER 4: Forced survival play with shortest option '{word}'."

            delay = 1.0 if is_retry else random.uniform(3.0, 4.5)
            elapsed = time.time() - state["turn_start_time"]
            
            state["diagnostic_reason"] = f"TIMEOUT: Selected '{word}', but the engine ran out of time during typing ({elapsed:.1f}s elapsed)."
            
            try:
                async with client.action(chat_id, 'typing'):
                    await asyncio.sleep(delay)
            except FloodWaitError as fwe:
                state["diagnostic_reason"] = f"TELEGRAM RATE LIMIT: Blocked by Telegram FloodWait for {fwe.seconds}s during typing."
                return

            state["last_submitted_word"] = word 
            state["diagnostic_reason"] = f"DELIVERY FAILURE: Sent '{word}', but Telegram failed to deliver."
            
            try:
                await client.send_message(chat_id, word)
                print(status_log, flush=True)
            except FloodWaitError as fwe:
                state["diagnostic_reason"] = f"TELEGRAM RATE LIMIT: Blocked by FloodWait for {fwe.seconds}s while sending '{word}'."
                return
                
            # Log to Ledger upon transmission
            letter_key = word[0].upper()
            if letter_key not in state["word_ledger"]:
                state["word_ledger"][letter_key] = []
            state["word_ledger"][letter_key].append(f"{word} (→{word[-1].upper()})")
            
            state["diagnostic_reason"] = f"GAME BOT DELAY: Sent '{word}' successfully. Waiting for validation."
        else:
            state["diagnostic_reason"] = f"DICT EXHAUSTION: No valid words remain matching: Start='{s_char}', Min={min_len}."
            
    except Exception as e:
        state["diagnostic_reason"] = f"INTERNAL ENGINE CRASH: {e}"

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
        
    if "turn:" in bot_text:
        state["current_constraints"] = bot_text 
        target_phrase = f"turn: {MY_USERNAME.lower()}"
        
        if target_phrase in bot_text:
            state["my_turn"] = True
            asyncio.create_task(submit_word(chat_id, bot_text, state, is_retry=False))
        else:
            if state["my_turn"]:
                state["diagnostic_reason"] = "TURN LOST: Passed to another player before execution."
            else:
                state["diagnostic_reason"] = "IDLE: Waiting for opponent turn."
            state["my_turn"] = False

    error_phrases = [
        "has been used", "not a valid word", "invalid", 
        "not in my list of words", "has less than",      
        "does not include", "does not contain"
    ]
    
    if any(phrase in bot_text for phrase in error_phrases):
        last_word = state.get("last_submitted_word", "").lower()
        
        if state["my_turn"] and last_word and last_word in bot_text:
            new_len_match = re.search(r'less than (\d+)', bot_text)
            if new_len_match:
                new_len = new_len_match.group(1)
                state["current_constraints"] += f" at least {new_len} letters"

            state["used_words"].add(last_word)
            state["diagnostic_reason"] = f"REJECTION LOOP: Bot rejected '{last_word}'. Attempting recovery."
            state["last_submitted_word"] = "" 
            
            asyncio.create_task(submit_word(chat_id, state["current_constraints"], state, is_retry=True))

    if "eliminated" in bot_text or "game over" in bot_text or "winner" in bot_text:
        if MY_USERNAME.lower() in bot_text or "game over" in bot_text:
            if state["diagnostic_reason"] in ["IDLE: Waiting for opponent turn.", "Waiting for a game to start..."]:
                state["diagnostic_reason"] = "SILENT TIMEOUT: Eliminated while idle. Missed turn event due to lag."
            update_dashboard(chat_id, state)
            
        state["used_words"].clear()
        state["last_submitted_word"] = ""
        state["word_ledger"].clear()
        state["my_turn"] = False

print(f"V25 Offensive Engine ({MY_USERNAME}) is running!", flush=True)
client.start()
client.run_until_disconnected()