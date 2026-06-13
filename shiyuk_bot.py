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
# 📚 LOCAL DICTIONARY DOWNLOADER 
# ==========================================
print("📚 Downloading English dictionary for SHIYUK...", flush=True) 
try:
    url = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req)
    VALID_WORDS = {w.decode('utf-8').strip().lower() for w in response.read().splitlines() if w.decode('utf-8').strip().isalpha()}
    print(f"✅ Loaded {len(VALID_WORDS)} valid words into memory.", flush=True)
except Exception as e:
    print(f"⚠️ Failed to download dictionary: {e}. Bot will rely entirely on cloud APIs.", flush=True)
    VALID_WORDS = set()

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

SESSION_STRING = "1BVtsOG8Bu0vGTorGeN8Su6IfvnUvKT3UssOn1xiZZHdTAUS8VsKWJYykuKanuG3xpyBbtukjORI0SYVhyJvaLavuZg62dJttLaIfwDalOdVSN8IwKiYq-JgWjoUMLyVPJPytHY427yPQPDXLlo9ncDJt3iRTYxMygSGGb0Twvm8hp_ecjDMSfOupjNifZqzQ2X9QQFkTF76JOrqpECPDabl8zP5NQUNq_kkts6Q0t1XNUkialllZyZJmmS5LjGvq2l2YJjyIVurQi8u0-V-BDaxVIA3sxNhb_xdCCs2-YIBOHjjBY_y86KwKeERofz7TR1ikL4HWHfjCe017QKJknZKVvXWOSgs="

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
# ⚙️ ADVANCED DIAGNOSTIC SOLVER
# ==========================================
async def submit_word(chat_id, constraints, state, is_retry=False):
    if not is_retry:
        state["turn_start_time"] = time.time()
        
    try:
        state["diagnostic_reason"] = "Processing rules and scanning local 370k dictionary."
        
        start_match = re.search(r'start with ([a-z])', constraints, re.IGNORECASE)
        length_matches = re.findall(r'at least (\d+) letters', constraints, re.IGNORECASE)
        include_match = re.search(r'(?:include|contain) ([a-z])', constraints, re.IGNORECASE)

        s_char = start_match.group(1).lower() if start_match else ""
        min_len = int(length_matches[-1]) if length_matches else 1
        i_char = include_match.group(1).lower() if include_match else ""
        
        valid_options = []
        for w in VALID_WORDS:
            if s_char and not w.startswith(s_char): continue
            if len(w) < min_len: continue
            if i_char and i_char not in w: continue
            if w in state["used_words"]: continue
            valid_options.append(w)
            
        if len(valid_options) < 15:
            state["diagnostic_reason"] = "Local database depleted. Querying Datamuse API."
            try:
                query_sp = (s_char if s_char else "") + ('?' * max(0, min_len - 1)) + '*'
                api_url = f"https://api.datamuse.com/words?sp={query_sp}&max=1000"
                
                # Added explicit 5-second timeout to prevent infinite hanging
                req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    api_data = json.loads(response.read().decode('utf-8'))
                
                for item in api_data:
                    w = item['word'].lower()
                    if w.isalpha() and (not i_char or i_char in w) and w not in state["used_words"] and w not in valid_options:
                        valid_options.append(w)
                        
            except asyncio.TimeoutError:
                state["diagnostic_reason"] = "NETWORK FAILURE: Datamuse API stalled and timed out."
            except Exception as e:
                state["diagnostic_reason"] = f"API FAILURE: Datamuse cloud returned an error ({e}). Local pool exhausted."
            
        if valid_options:
            preferred_options = [w for w in valid_options if len(w) <= min_len + 2]
            word = random.choice(preferred_options) if preferred_options else random.choice(valid_options)
            
            delay = 1.0 if is_retry else random.uniform(3.0, 4.5)
            elapsed = time.time() - state["turn_start_time"]
            
            state["diagnostic_reason"] = f"TIMEOUT: Selected '{word}', but the engine ran out of time during the simulated typing phase ({elapsed:.1f}s elapsed)."
            
            try:
                async with client.action(chat_id, 'typing'):
                    await asyncio.sleep(delay)
            except FloodWaitError as fwe:
                state["diagnostic_reason"] = f"TELEGRAM RATE LIMIT: Blocked by Telegram FloodWait for {fwe.seconds}s during typing simulation."
                return

            state["last_submitted_word"] = word 
            
            state["diagnostic_reason"] = f"DELIVERY FAILURE: Sent '{word}', but Telegram failed to deliver the message to the group."
            
            try:
                await client.send_message(chat_id, word)
            except FloodWaitError as fwe:
                state["diagnostic_reason"] = f"TELEGRAM RATE LIMIT: Blocked by Telegram FloodWait for {fwe.seconds}s while attempting to send '{word}'."
                return
                
            # Log to Ledger upon transmission
            letter_key = word[0].upper()
            if letter_key not in state["word_ledger"]:
                state["word_ledger"][letter_key] = []
            state["word_ledger"][letter_key].append(f"{word} (≥{min_len})")
            
            state["diagnostic_reason"] = f"GAME BOT DELAY: Sent '{word}' successfully. Waiting for game bot validation."
        else:
            state["diagnostic_reason"] = f"DICT EXHAUSTION: No valid words exist in local storage or cloud databases matching constraints: Start='{s_char}', Min={min_len}, Contain='{i_char}'."
            
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
                state["diagnostic_reason"] = "TURN LOST: Turn passed to another player before execution completed."
            else:
                state["diagnostic_reason"] = "IDLE: Waiting for opponent turn to conclude."
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
            state["diagnostic_reason"] = f"REJECTION LOOP TIMEOUT: Bot rejected '{last_word}'. Attempting recovery."
            state["last_submitted_word"] = "" 
            
            asyncio.create_task(submit_word(chat_id, state["current_constraints"], state, is_retry=True))

    if "eliminated" in bot_text or "game over" in bot_text or "winner" in bot_text:
        if MY_USERNAME.lower() in bot_text or "game over" in bot_text:
            # Check if the text implies a silent drop
            if state["diagnostic_reason"] in ["IDLE: Waiting for opponent turn to conclude.", "Waiting for a game to start..."]:
                state["diagnostic_reason"] = "SILENT TIMEOUT: Eliminated while idle. The bot likely missed its turn event due to network lag or dropped Telethon event."
            update_dashboard(chat_id, state)
            
        state["used_words"].clear()
        state["last_submitted_word"] = ""
        state["word_ledger"].clear()
        state["my_turn"] = False

print(f"V23 Comprehensive Diagnostic Bot ({MY_USERNAME}) is running!", flush=True)
client.start()
client.run_until_disconnected()