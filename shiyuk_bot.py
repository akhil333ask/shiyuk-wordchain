import asyncio
import os
import re
import random
import urllib.request
import json
import time
import unicodedata 
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

JSON_DB_FILE = "verified_database.json"
if os.path.exists(JSON_DB_FILE):
    try:
        with open(JSON_DB_FILE, "r") as f:
            custom_data = json.load(f)
            added_count = 0
            if isinstance(custom_data, dict):
                words_to_add = [w for w, valid in custom_data.items() if valid]
            else:
                words_to_add = custom_data
                
            for word in words_to_add:
                if word not in VALID_WORDS:
                    VALID_WORDS.add(word)
                    added_count += 1
        print(f"🧬 Injected {added_count} custom verified words from {JSON_DB_FILE}.", flush=True)
    except Exception as e:
        print(f"⚠️ Failed to load custom JSON: {e}", flush=True)

# ==========================================
# 🌐 KEEP-ALIVE SERVER (MODIFIED FOR ALWAYSDATA IPv6)
# ==========================================
app = Flask(__name__)
latest_diagnostic_report = "Bot is running on Alwaysdata in Friendly Mode. 🤝"

@app.route('/')
def home():
    return "SHIYUK Multi-Agent Bot is running! Go to /logs to view diagnostics."

@app.route('/logs')
def logs():
    return f"<body style='background-color:#1e1e1e; color:#00ff00; font-family:monospace; padding:20px;'><pre style='font-size:16px;'>{latest_diagnostic_report}</pre></body>"

def run_server():
    try:
        # Alwaysdata injects the correct port into the environment variables
        port = int(os.environ.get('PORT', 8080)) 
        
        # We must explicitly tell Flask to bind to IPv6 (::) AND pass the dynamic port 
        app.run(host='::', port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"ℹ️ Local Port Note: Web server paused locally. Error: {e}", flush=True)

Thread(target=run_server, daemon=True).start()

# ==========================================
# 🤖 BOT CONFIGURATION & API KEYS
# ==========================================
API_ID = 27611951
API_HASH = '16c265ac1d31f819b7dd53ce3b3602af'
MY_USERNAME = "TankaJahari"  

# Target Game Bots
CHAIN_GAME_BOT = "on9wordchainbot"   
SEEK_GAME_BOT = "WordSeekBot"

# 🔑 HARDCODED TELEGRAM SESSION
SESSION_STRING = "1BVtsOKEBu7iyMHUsRmi_HG-Q2eBzYTT9lfB1BMJMj2sVLjD_zDNngrvq5RX6FSyVqGkp5ZPFvpN9wztZ7_Hk84Qi2jgw9_a8C_86y3RHgz0-NmgVg-_Tw8THYq5rQM3LdMgKZqTnSGfIBuf3ParvBLVGaYIJKlZfvy2E9GUxnWR1cVJBLsbCdN6BBAjCxc-672LrmeM2GS44LxpnP-KhDvshaTr65HvEoGnaHrfv3sWsXHE_cvFfpxxJEOsW-xVRXvlViCYSIqt1_6Q1UeJO8rvXbkLieyO4jBKp8SaNccPV9dargP_TOQHtXQ-prjcUY3KMI2_yY28RX7a_mrDV1_Fx731tTFQ="

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==========================================
# 🟩 AGENT 1: WORDSEEK (AUTO-WIPE GATE)
# ==========================================
wordseek_state = {}

def get_wordseek_state(chat_id):
    if chat_id not in wordseek_state:
        wordseek_state[chat_id] = {
            "active": False,
            "length": 5,
            "pool": [],
            "processed_feedback": set(),
            "authorized": False,
            "last_auth_time": 0
        }
    return wordseek_state[chat_id]

def wipe_wordseek_memory(chat_id):
    """Hard wipes the state to completely prevent memory leaks."""
    wordseek_state[chat_id] = {
        "active": False,
        "length": 5,
        "pool": [],
        "processed_feedback": set(),
        "authorized": False,
        "last_auth_time": 0
    }

@client.on(events.NewMessage(outgoing=True))
async def user_command_monitor(event):
    chat_id = event.chat_id
    text = event.raw_text.strip().lower()
    
    if text in ["wait", "play"] or text.startswith("/new"):
        state = get_wordseek_state(chat_id)
        state["authorized"] = True
        state["last_auth_time"] = time.time()
        print(f"🔓 WordSeek Gate Unlocked for chat {chat_id} via trigger: '{text}'", flush=True)

    if text.startswith("/end") or text.startswith("/lock"):
        wipe_wordseek_memory(chat_id)
        print(f"🔒 WordSeek Gate manually wiped & locked.", flush=True)

def filter_wordseek_pool(pool, guess, feedback):
    new_pool = []
    for word in pool:
        valid = True
        word_chars = list(word)
        
        for i, (g_char, f) in enumerate(zip(guess, feedback)):
            if f == 'G':
                if word[i] != g_char:
                    valid = False
                    break
                word_chars[i] = None 
        
        if not valid: continue
        
        for i, (g_char, f) in enumerate(zip(guess, feedback)):
            if f == 'Y':
                if word[i] == g_char: 
                    valid = False
                    break
                if g_char in word_chars:
                    word_chars[word_chars.index(g_char)] = None 
                else:
                    valid = False 
                    break
                    
        if not valid: continue
        
        for i, (g_char, f) in enumerate(zip(guess, feedback)):
            if f == 'R':
                if g_char in word_chars: 
                    valid = False
                    break
                    
        if valid:
            new_pool.append(word)
            
    return new_pool

async def execute_wordseek_guess(chat_id, guess, delay):
    try:
        async with client.action(chat_id, 'typing'):
            await asyncio.sleep(delay)
        await client.send_message(chat_id, guess)
    except Exception as e:
        pass

@client.on(events.NewMessage(from_users=SEEK_GAME_BOT))
async def wordseek_handler(event):
    chat_id = event.chat_id
    text = unicodedata.normalize('NFKC', event.raw_text)
    state = get_wordseek_state(chat_id)
    
    start_match = re.search(r'Guess the (\d+)-letter word', text, re.IGNORECASE)
    if start_match:
        time_since_auth = time.time() - state.get("last_auth_time", 0)
        if time_since_auth > 30:
            state["authorized"] = False

        length = int(start_match.group(1))
        state["active"] = True
        state["length"] = length
        state["pool"] = [w for w in VALID_WORDS if len(w) == length]
        state["processed_feedback"] = set()
        print(f"🧩 WordSeek Match Detected! Target Length: {length}.", flush=True)
        
        if not state["authorized"]:
            print("zzz Standing down. Match started by someone else. Type 'wait' or 'play' to join.", flush=True)
            return
            
        first_guess = random.choice(state["pool"])
        state["pool"].remove(first_guess)
        
        human_delay = random.choice([4.0, 5.0, 6.0])
        asyncio.create_task(execute_wordseek_guess(chat_id, first_guess, human_delay))
        return

    if "mode" in text.lower() and any(e in text for e in ['🟥', '🟨', '🟩']):
        if not state["active"]:
            lines = text.split('\n')
            for line in lines:
                if '🟥' in line or '🟨' in line or '🟩' in line:
                    words = re.findall(r'[a-zA-Z]+', line)
                    if words:
                        length = len(words[-1])
                        state["active"] = True
                        state["length"] = length
                        state["pool"] = [w for w in VALID_WORDS if len(w) == length]
                        state["processed_feedback"] = set()
                        break
        
        if not state["active"]: return
        if not state["authorized"]: return

        if '🟩'*state["length"] in text:
            print("🏆 WordSeek Solved! Wiping memory.")
            wipe_wordseek_memory(chat_id) 
            return

        lines = [line.strip() for line in text.split('\n') if any(e in line for e in ['🟥', '🟨', '🟩'])]
        
        for line in lines:
            feedback = []
            for char in line:
                if char == '🟩': feedback.append('G')
                elif char == '🟨': feedback.append('Y')
                elif char == '🟥': feedback.append('R')
                
            words = re.findall(r'[a-zA-Z]+', line)
            if not words: continue
            guess_word = words[-1].lower()
            
            if len(feedback) != state["length"] or len(guess_word) != state["length"]: continue
            if guess_word in state["processed_feedback"]: continue 
            
            state["processed_feedback"].add(guess_word)
            state["pool"] = filter_wordseek_pool(state["pool"], guess_word, feedback)

        if state["pool"]:
            next_guess = random.choice(state["pool"])
            print(f"🎯 WordSeek Thinking... Pool reduced to {len(state['pool'])}. Guessing: {next_guess}")
            
            state["pool"].remove(next_guess) 
            
            human_delay = random.choice([6.0, 8.0, 10.0, 12.0])
            asyncio.create_task(execute_wordseek_guess(chat_id, next_guess, human_delay))
        else:
            print("❌ WordSeek Dictionary Exhausted!")
            wipe_wordseek_memory(chat_id)
            
    end_triggers = [
        "game over", "won the game", "the word was", 
        "game ended", "ended the game", "time's up",
        "time is up", "guessed the word"
    ]
    if any(trigger in text.lower() for trigger in end_triggers):
        print("🛑 WordSeek Match Concluded. Wiping memory.", flush=True)
        wipe_wordseek_memory(chat_id)


# ==========================================
# ⛓️ AGENT 2: WORDCHAIN ENGINE (FRIENDLY MODE)
# ==========================================
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
    report = f"==================================================\n💀 ELIMINATION DIAGNOSTIC REPORT\n==================================================\n\n❌ CAUSE OF DEATH:\n> {state['diagnostic_reason']}\n\n📊 WORD LEDGER (History for this match):\n"
    if not state["word_ledger"]: report += "> No words were successfully played.\n"
    else:
        for letter in sorted(state["word_ledger"].keys()):
            report += f"- [{letter.upper()}]: {', '.join(state['word_ledger'][letter])}\n"
    report += f"\n==================================================\n"
    latest_diagnostic_report = report
    print(report, flush=True)

async def submit_word(chat_id, constraints, state, is_retry=False):
    if not is_retry: state["turn_start_time"] = time.time()
        
    try:
        state["diagnostic_reason"] = "Processing rules and scanning local dictionaries."
        
        start_match = re.search(r'start with ([a-z])', constraints, re.IGNORECASE)
        length_matches = re.findall(r'at least (\d+) letters', constraints, re.IGNORECASE)
        include_match = re.search(r'(?:include|contain)\s+(?!at\s+least)([a-z,\s]+?)(?:\s+and|\.|$)', constraints, re.IGNORECASE)
        exclude_match = re.search(r'exclude\s+([a-z,\s]+?)(?:\s+and|\.|$)', constraints, re.IGNORECASE)

        s_char = start_match.group(1).lower() if start_match else ""
        min_len = int(length_matches[-1]) if length_matches else 1
        i_chars = set(re.findall(r'\b([a-z])\b', include_match.group(1).lower())) if include_match else set()
        e_chars = set(re.findall(r'\b([a-z])\b', exclude_match.group(1).lower())) if exclude_match else set()
        
        valid_options = []
        for w in VALID_WORDS:
            if s_char and not w.startswith(s_char): continue
            if len(w) < min_len: continue
            if i_chars and not all(c in w for c in i_chars): continue
            if e_chars and any(c in w for c in e_chars): continue
            if w in state["used_words"]: continue
            valid_options.append(w)
                
        if valid_options:
            # 🤝 FRIENDLY MODE: No killer endings, just random selection
            preferred_len_limit = min_len + 3 
            
            # Try to pick a standard word to keep the game flowing casually
            casual_options = [w for w in valid_options if len(w) <= preferred_len_limit]
            
            if casual_options:
                word = random.choice(casual_options)
            else:
                word = random.choice(valid_options)

            # 🐢 RELAXED DELAY: Classic 4 to 6 seconds
            delay = 1.0 if is_retry else random.choice([4.0, 5.0, 6.0])
            elapsed = time.time() - state["turn_start_time"]
            
            state["diagnostic_reason"] = f"TIMEOUT: Selected '{word}', ran out of time ({elapsed:.1f}s elapsed)."
            
            try:
                async with client.action(chat_id, 'typing'):
                    await asyncio.sleep(delay)
            except FloodWaitError:
                return

            state["last_submitted_word"] = word 
            state["diagnostic_reason"] = f"DELIVERY FAILURE: Sent '{word}', but Telegram failed to deliver."
            
            try:
                await client.send_message(chat_id, word)
                print(f"🏹 PLAYED (Friendly): {word} (Len: {len(word)}, Ends: {word[-1].upper()})", flush=True)
            except FloodWaitError:
                return
                
            letter_key = word[0].upper()
            if letter_key not in state["word_ledger"]: state["word_ledger"][letter_key] = []
            state["word_ledger"][letter_key].append(f"{word} (≥{min_len})")
            
            state["diagnostic_reason"] = f"GAME BOT DELAY: Sent '{word}'. Waiting for validation."
        else:
            state["diagnostic_reason"] = f"DICT EXHAUSTION: No valid words remain. Constraints: Start='{s_char}', Min={min_len}, Inc={i_chars}, Exc={e_chars}."
            
    except Exception as e:
        state["diagnostic_reason"] = f"INTERNAL ENGINE CRASH: {e}"

@client.on(events.NewMessage(from_users=CHAIN_GAME_BOT))
async def chain_game_handler(event):
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
            state["my_turn"] = False

    error_phrases = [
        "has been used", "not a valid word", "invalid", 
        "not in my list of words", "has less than",      
        "does not include", "does not contain", "banned letters", "contains banned", "does not start with"
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
            update_dashboard(chat_id, state)
        state["used_words"].clear()
        state["last_submitted_word"] = ""
        state["word_ledger"].clear()
        state["my_turn"] = False

print(f"V41 Friendly Mode Engine ({MY_USERNAME}) is running!", flush=True)
client.start()
client.run_until_disconnected()
