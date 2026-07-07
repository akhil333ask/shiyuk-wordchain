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

# 🔥 PRIORITY FILE INJECTION (y.txt, e.txt, x.txt)
PRIORITY_WORDS = set()
for txt_file in ["y.txt", "e.txt", "x.txt"]:
    if os.path.exists(txt_file):
        try:
            with open(txt_file, "r", encoding="utf-8") as f:
                count = 0
                for line in f:
                    w = line.strip().lower()
                    if w.isalpha():
                        PRIORITY_WORDS.add(w)
                        VALID_WORDS.add(w) # Ensure they also exist in master dictionary
                        count += 1
            print(f"🌾 Loaded {count} harvested priority words from {txt_file}.", flush=True)
        except Exception as e:
            print(f"⚠️ Failed to load {txt_file}: {e}", flush=True)

# ==========================================
# 🌐 KEEP-ALIVE SERVER
# ==========================================
app = Flask(__name__)
latest_diagnostic_report = "Bot is running. No games have been lost yet! 🚀"

@app.route('/')
def home():
    return "SHIYUK Multi-Agent Bot is running! Go to /logs to view diagnostics."

@app.route('/logs')
def logs():
    return f"<body style='background-color:#1e1e1e; color:#00ff00; font-family:monospace; padding:20px;'><pre style='font-size:16px;'>{latest_diagnostic_report}</pre></body>"

def run_server():
    try:
        port = int(os.environ.get('PORT', 8080)) 
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"ℹ️ Local Port Note: Web server paused locally.", flush=True)

Thread(target=run_server, daemon=True).start()

# ==========================================
# 🤖 BOT CONFIGURATION & API KEYS
# ==========================================
API_ID = 27611951
API_HASH = '16c265ac1d31f819b7dd53ce3b3602af'
MY_USERNAME = "SHIYUK"  

# Target Game Bots
CHAIN_GAME_BOT = "on9wordchainbot"   
SEEK_GAME_BOT = "WordSeekBot"

# 🔑 HARDCODED TELEGRAM SESSION
SESSION_STRING = "1BVtsOKEBu0AVWVtl2fKdRp1gA6lzqaY6g15MJceNrHGsSeYq0IH3XFgfKcb6bceBSoClGz3d5VJxiOzhxeIpAB-kTxOi71OlqYnVCdJAF0LFFsZLT9OlJ7ycbb9dfAbkaSQK7a5HOPyhrXn3-63EW2cXe19n2JQlQGH4Q6OvDtC7t8aUAN4_oja8DYJs1PspwEExlX5LjBG09sHpxoYQwPaHwp1oABxWgbOrG8flgKfljYmLDGaWvWsXb7RwCoFeC--OmJvUyaqwjE7wwrKQb1KNJCNNhNsXxMxwlQ4luzbvRq6WFV5_5sIfnYW0EdSsvMZO6pl6jldaLhh7uWYK6sxzP0HghuQ="
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# ==========================================
# 🟩 AGENT 1: WORDSEEK (PERFECT MEMORY)
# ==========================================
wordseek_state = {}

def get_wordseek_state(chat_id):
    if chat_id not in wordseek_state:
        wordseek_state[chat_id] = {
            "active": False,
            "length": 5,
            "pool": [],
            "processed_feedback": set() 
        }
    return wordseek_state[chat_id]

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
        length = int(start_match.group(1))
        state["active"] = True
        state["length"] = length
        state["pool"] = [w for w in VALID_WORDS if len(w) == length]
        state["processed_feedback"] = set()
        print(f"🧩 WordSeek Started! Target Length: {length}. Possible Words: {len(state['pool'])}")
        
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

        if '🟩'*state["length"] in text:
            print("🏆 WordSeek Solved!")
            state["active"] = False
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
            state["active"] = False
            
    if "Game over" in text or "won the game" in text.lower():
        state["active"] = False


# ==========================================
# ⛓️ AGENT 2: WORDCHAIN ENGINE (Y-E-X PRIORITY)
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
            valid_options.sort(key=len)
            preferred_len_limit = min_len + 2
            
            # 🔥 1. CHECK HARVESTED FILES FIRST
            # Extracts only valid words that came from your .txt files
            priority_options = [w for w in valid_options if w in PRIORITY_WORDS]
            
            # If priority words exist, use them exclusively. Otherwise, fall back to the dictionary.
            active_pool = priority_options if priority_options else valid_options
            
            # 🔥 2. RANDOMIZED Y-E-X ATTACK
            killer_letters = ['y', 'e', 'x']
            random.shuffle(killer_letters) # Mix up the attack order (e.g., e -> y -> x)
            
            tier_1 = []
            tier_2 = []
            
            # Search the pool for the randomly shuffled letters
            for letter in killer_letters:
                options = [w for w in active_pool if w[-1] == letter]
                if options:
                    short_options = [w for w in options if len(w) <= preferred_len_limit]
                    if short_options:
                        tier_1 = short_options
                        break 
                    elif not tier_2:
                        tier_2 = options 
                        
            tier_3 = [w for w in active_pool if len(w) <= preferred_len_limit]
            
            if tier_1: word = random.choice(tier_1)
            elif tier_2: word = tier_2[0]
            elif tier_3: word = random.choice(tier_3)
            else: word = active_pool[0]

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
                source_log = "🌾 [TXT]" if word in PRIORITY_WORDS else "📚 [DICT]"
                print(f"🏹 PLAYED {source_log}: {word} (Len: {len(word)}, Ends: {word[-1].upper()})", flush=True)
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

print(f"V36 Y-E-X Priority Engine ({MY_USERNAME}) is running!", flush=True)
client.start()
client.run_until_disconnected()
