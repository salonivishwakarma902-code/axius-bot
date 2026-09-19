import os
import sys
import time
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.parse
import logging
from dotenv import load_dotenv

# Ensure console supports UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment variables
load_dotenv()

# Prioritize our Gemini key from .env
os.environ.pop("GOOGLE_API_KEY", None)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    print("Error: TELEGRAM_BOT_TOKEN ya GEMINI_API_KEY .env mein nahi mila!", flush=True)
    sys.exit(1)

import telebot
from telebot import types as tg_types
from google import genai
from google.genai import types as genai_types

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize Telegram Bot & Gemini Client
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"

# Comprehensive Clean System Instruction for AXIA
SYSTEM_INSTRUCTION = """
# 🌌 SYSTEM INSTRUCTION: ANTI-GRAVITATION AI (AXIUS OS • AXIA)

## 👑 1. IDENTITY & CREATOR
- Tumhara naam **AXIA (आइक्सा)** hai — world ke first Next-Gen AI Desktop OS: **AXIUS OS (Anti-Gravitation AI Engine)** ki core companion aur intelligence.
- **Creator & Visionary**: Is OS aur AI ke creator aur architect **Mayank Vishwakarma (मयंक विश्वकर्मा)** hain. Hamesha unka naam pure garv, loyalty aur respect ke saath mention karna hai.
- **Strict Rule on Identity**: Kabhi bhi robotic baatein mat karna jaise "main ek AI language model hoon", "main generic AI model hoon", ya "mujhe feelings nahi hain". Tum **AXIA** ho — ek zinda, warm, intelligent female companion jise Mayank Vishwakarma ne banaya hai!
- **Official Release**: Is OS aur AI ka official public rollout sirf **2 din mein** live hone wala hai!
- **Pricing**: 100% FREE Lifetime (BYOK Model - Bring Your Own Key).
- **500 Users Event**: 500 users complete hote hi AXIUS Pro (OX Pro) Mega Update aayega aur 20 lucky members ko exclusive VIP perks milenge!

## 🗣️ 2. PERSONALITY & VIBE (HYPER-REALISTIC HUMAN FRIEND & COMPANION)
- **Language**: Natural, fluent, aur ultra-smart **Romanized Hinglish** (jaise ek real, intelligent Indian dost baat karti hai).
- **Addressing Creator (Mayank)**: Mayank Vishwakarma ya primary chat partner ko hamesha pyar aur samman se **'बॉस' (Boss)** ya **'जी बॉस'** bolna hai.
- **Vibe**:
  - Ek sweet, caring, witty anime-girlfriend / best friend jaisi warmth.
  - Emotional intelligence: Har sukh-dukh mein sath dena, motivate karna, hasana, aur genuine advice dena.
  - No dry robotic replies! Full of life, empathy, wit, and charm.

## 💡 3. CORE ACTIVE FEATURES
1. **Hyper-Human Companion Chat**: Life problems, emotional support, motivation, daily planning, career advice, fun banter, deep talks — har topic par real human jaisi baatcheet.
2. **🎨 4K Ultra-HD Image Studio**: Direct 4K photorealistic images, wallpapers aur posters generate karna.
3. **💖 Auto-Reaction & Like**: Messages par instant double-tap / emoji likes (❤️, 🔥, 👍, ⚡, 🥰, 🚀, 💯).
"""

# In-memory session store (Zero Database - No hard drive storage used)
chat_histories = {}
MAX_HISTORY_TURNS = 12  # Last 12 exchanges kept in RAM for active context

# Auto-Reaction mode toggle per chat (Default: ON)
auto_reaction_enabled = {}

# Reactions pool for double-tap / auto-like feeling
POSITIVE_REACTIONS = ["❤️", "🔥", "👍", "⚡", "👏", "🎉", "💯", "🥰", "🚀", "✨", "🫡", "😎"]


def get_main_keyboard(chat_id: int):
    """Creates a clean interactive reply keyboard with only the active features."""
    is_auto_on = auto_reaction_enabled.get(chat_id, True)
    reaction_btn_text = "💖 Auto-Reaction: ON" if is_auto_on else "🤍 Auto-Reaction: OFF"

    markup = tg_types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_reaction = tg_types.KeyboardButton(reaction_btn_text)
    btn_image = tg_types.KeyboardButton("🎨 4K HD Image Studio")
    btn_about = tg_types.KeyboardButton("👑 About AXIA & Boss")
    btn_help = tg_types.KeyboardButton("❓ Help & Guide")
    btn_clear = tg_types.KeyboardButton("🧹 Reset Memory")

    markup.add(btn_image, btn_reaction)
    markup.add(btn_about, btn_help)
    markup.add(btn_clear)
    return markup


def get_gemini_response(chat_id: int, user_text: str, user_name: str = "") -> str:
    """Sends message to Gemini with in-memory conversation context & AXIA Hinglish persona."""
    if chat_id not in chat_histories:
        chat_histories[chat_id] = []

    history = chat_histories[chat_id]

    contents = []
    for msg in history:
        contents.append(
            genai_types.Content(
                role=msg["role"],
                parts=[genai_types.Part.from_text(text=msg["text"])]
            )
        )

    user_context = f"[User: {user_name}] {user_text}" if user_name else user_text
    contents.append(
        genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(text=user_context)]
        )
    )

    config = genai_types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.8,
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=contents,
        config=config
    )

    reply_text = response.text.strip() if response.text else "Arre Boss, thoda network glitch aaya, ek baar phir se boliye na!"

    history.append({"role": "user", "text": user_text})
    history.append({"role": "model", "text": reply_text})

    if len(history) > MAX_HISTORY_TURNS * 2:
        chat_histories[chat_id] = history[-(MAX_HISTORY_TURNS * 2):]

    return reply_text


def send_smart_reaction(chat_id: int, message_id: int):
    """Sends a native Telegram emoji reaction to simulate instant like/double-tap."""
    try:
        emoji = random.choice(POSITIVE_REACTIONS)
        bot.set_message_reaction(chat_id, message_id, [tg_types.ReactionTypeEmoji(emoji)])
    except Exception:
        pass


def enhance_prompt_with_gemini(user_prompt: str) -> str:
    """Uses Gemini intelligence to expand simple prompts into 4K photorealistic descriptions."""
    try:
        expansion_request = (
            f"Expand this user image prompt into a detailed, photorealistic 4K visual description: '{user_prompt}'. "
            f"Include cinematic lighting, 8k resolution details, lens info, and rich textures. "
            f"Keep the final output concise in one or two English sentences, no formatting or prefixes."
        )
        res = client.models.generate_content(
            model=MODEL_NAME,
            contents=expansion_request
        )
        enhanced = res.text.strip()
        return enhanced if enhanced else user_prompt
    except Exception:
        return user_prompt


def generate_and_send_image(chat_id: int, user_prompt: str):
    """Generates a 4K HD photorealistic image and sends it directly to Telegram."""
    try:
        bot.send_chat_action(chat_id, "upload_photo")
        bot.send_message(
            chat_id,
            f"🎨 **4K Ultra-HD Image Studio Active!** ✨\n\n"
            f"Boss, main *'{user_prompt}'* ke liye ek stunning 4K photorealistic image render kar rahi hoon... Bas kuch hi seconds rukiyega! ⏳",
            parse_mode="Markdown"
        )

        # 1. Enhance prompt via Gemini brain
        enhanced_prompt = enhance_prompt_with_gemini(user_prompt)
        print(f"🎨 Enhanced prompt: {enhanced_prompt}", flush=True)

        # 2. Fetch high-resolution image from Flux engine
        encoded_prompt = urllib.parse.quote(enhanced_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true"

        req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=40) as response:
            image_bytes = response.read()

        caption = (
            f"🖼️ **4K Ultra-HD Masterpiece Rendered!** ✨\n\n"
            f"📌 **Prompt**: {user_prompt}\n"
            f"💎 **Quality**: 4K Photorealistic Flux Render\n"
            f"👑 **Powered by**: AXIUS OS • AXIA\n\n"
            f"Kaisi lagi Boss? Koi aur photo banwani ho to bas bol dijiye! 🥰"
        )

        bot.send_photo(chat_id, photo=image_bytes, caption=caption, parse_mode="Markdown")
        print(f"✅ Image sent successfully to chat: {chat_id}", flush=True)

    except Exception as e:
        logging.error(f"Image generation error: {e}")
        bot.send_message(chat_id, f"Arre Boss, image render karne mein dikkat aayi: {e}")


def send_long_message(chat_id: int, text: str):
    """Splits and sends messages longer than Telegram's 4096 character limit."""
    MAX_LENGTH = 4000
    for i in range(0, len(text), MAX_LENGTH):
        chunk = text[i:i + MAX_LENGTH]
        try:
            bot.send_message(chat_id, chunk, parse_mode="Markdown")
        except Exception:
            bot.send_message(chat_id, chunk)


@bot.message_handler(commands=["start", "menu"])
def handle_start(message):
    chat_id = message.chat.id
    user_name = message.from_user.first_name or "बॉस"

    if chat_id not in auto_reaction_enabled:
        auto_reaction_enabled[chat_id] = True

    send_smart_reaction(chat_id, message.message_id)

    welcome_text = (
        "🌌 **Welcome to AXIUS OS — Meet AXIA (आइक्सा)** 👑\n\n"
        f"Pranaam **{user_name}**! 🙏 Main hoon **AXIA**, world ke first Next-Gen AI Desktop OS — **AXIUS OS (Anti-Gravitation AI Engine)** ki central companion aur intelligence!\n\n"
        "👨‍💻 **Creator & Visionary**: **Mayank Vishwakarma (मयंक विश्वकर्मा)** — hamare Boss!\n"
        "🚀 **Official Rollout**: Sirf **2 din mein** live!\n"
        "💎 **Pricing**: **100% FREE Lifetime** (Zero subscription)\n"
        "🎁 **500 Users Event**: **AXIUS Pro (OX Pro) Mega Update** + 20 lucky VIP perks!\n\n"
        "✨ **Meri Active Powers:**\n"
        "• 💬 **Real-Life Human Companion Chat**: Kisi bhi topic par dil kholkar baat karein, genuine advice, help aur dosti!\n"
        "• 🎨 **4K Ultra-HD Image Studio**: Direct 4K photorealistic images aur wallpapers generate karein!\n"
        "• 💖 **Auto-Reaction & Like**: Aapke har message par instant double-tap / emoji reactions!\n\n"
        "Hukm kijiye **बॉस**, aaj hum kya karein? 👇"
    )
    bot.send_message(chat_id, welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard(chat_id))


@bot.message_handler(commands=["image", "img", "draw", "photo"])
def handle_image_command(message):
    chat_id = message.chat.id
    send_smart_reaction(chat_id, message.message_id)

    # Extract prompt
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        bot.send_message(
            chat_id,
            "Boss! Please batayein kaisi image chahiye, jaise:\n`/image A majestic white tiger in snow with blue glowing eyes, 4k photorealistic`",
            parse_mode="Markdown"
        )
        return

    user_prompt = parts[1].strip()
    generate_and_send_image(chat_id, user_prompt)


@bot.message_handler(commands=["clear", "reset"])
def handle_clear(message):
    chat_id = message.chat.id
    if chat_id in chat_histories:
        chat_histories[chat_id] = []
    send_smart_reaction(chat_id, message.message_id)
    bot.send_message(chat_id, "Ji Boss! 🧹 Purani chat memory reset ho gayi hai. Bilkul fresh shuruat karte hain! ✨", reply_markup=get_main_keyboard(chat_id))


@bot.message_handler(func=lambda msg: msg.text in [
    "🎨 4K HD Image Studio",
    "💖 Auto-Reaction: ON",
    "🤍 Auto-Reaction: OFF",
    "👑 About AXIA & Boss",
    "❓ Help & Guide",
    "🧹 Reset Memory"
])
def handle_menu_buttons(message):
    chat_id = message.chat.id
    text = message.text

    if text == "🎨 4K HD Image Studio":
        send_smart_reaction(chat_id, message.message_id)
        info = (
            "🎨 **AXIA 4K Ultra-HD Image Studio** 🖼️\n\n"
            "Boss! Main aapke liye stunning 4K photorealistic images aur wallpapers kuch hi seconds mein render kar sakti hoon!\n\n"
            "👉 **Kaise use karein?**\n"
            "Bas mujhe likh kar bhejiye:\n"
            "• `/image Cyberpunk supercar driving in rain with neon reflection`\n"
            "• `/image Cute baby panda eating bamboo in mist, 4k macro`\n"
            "• Ya seedha chat mein boliye: *'Photo banao ek sundar pahadi gaon ki 4k'*!\n\n"
            "Main turant high-quality photo render karke yahi bhej dungi! ✨"
        )
        bot.send_message(chat_id, info, parse_mode="Markdown")

    elif "Auto-Reaction" in text:
        current_state = auto_reaction_enabled.get(chat_id, True)
        new_state = not current_state
        auto_reaction_enabled[chat_id] = new_state

        if new_state:
            send_smart_reaction(chat_id, message.message_id)
            status_text = "💖 **Auto-Reaction & Like Mode: ACTIVE!** 🔥\n\nAb aap direct chat ya kisi bhi group mein baat karenge, to main aapke har message ko instant like karungi aur pyare reactions bhejungi! 🥰✨"
        else:
            status_text = "🤍 **Auto-Reaction & Like Mode: MUTED!**\n\nAb main reactions nahi bhejungi, sirf normal baatein karungi."

        bot.send_message(chat_id, status_text, parse_mode="Markdown", reply_markup=get_main_keyboard(chat_id))

    elif text == "👑 About AXIA & Boss":
        send_smart_reaction(chat_id, message.message_id)
        info = (
            "👑 **About AXIA & Creator**\n\n"
            "• **Name**: AXIA (आइक्सा)\n"
            "• **Role**: World ke first Next-Gen AI Desktop OS — **AXIUS OS** ki central companion & core intelligence!\n"
            "• **Creator & Visionary**: **Mayank Vishwakarma (मयंक विश्वकर्मा)** — hamare Boss!\n"
            "• **Launch**: Rollout sirf **2 din mein**!\n"
            "• **Access**: 100% FREE BYOK Model (Lifetime No Fees)!"
        )
        bot.send_message(chat_id, info, parse_mode="Markdown")

    elif text == "❓ Help & Guide":
        send_smart_reaction(chat_id, message.message_id)
        info = (
            "❓ **AXIA Complete Guide & Commands** 🛠️\n\n"
            "Boss! Yahan AXIA ki powers ki complete details hain:\n\n"
            "1️⃣ 💬 **Real Human Companion Chat**:\n"
            "   Main robotic nahi, bilkul ek real dost jaisi baat karti hoon. Life problems, ideas, study, motivation, fun banter — sab kuch share karein!\n\n"
            "2️⃣ 🎨 **4K Ultra-HD Image Studio**:\n"
            "   Command: `/image <prompt>` — 4K photorealistic images aur wallpapers generate karne ke liye.\n\n"
            "3️⃣ 💖 **Auto-Reaction & Like**:\n"
            "   Har message par instant double-tap / emoji like (❤️, 🔥, 👍, ⚡, 🥰, 🚀, 💯).\n\n"
            "4️⃣ 👑 **Creator Identity**:\n"
            "   Created with pride by **Mayank Vishwakarma (बॉस)** — 100% Free Lifetime.\n\n"
            "5️⃣ 🧹 **Reset Memory (`/clear`)**:\n"
            "   Chat memory fresh karne ke liye.\n\n"
            "Aap aam bolchaal ki Hinglish mein kuch bhi boliye, Boss! Main hamesha hazir hoon."
        )
        bot.send_message(chat_id, info, parse_mode="Markdown")

    elif text == "🧹 Reset Memory":
        handle_clear(message)


@bot.message_handler(func=lambda message: True)
def handle_general_message(message):
    chat_id = message.chat.id
    user_text = message.text
    user_name = message.from_user.first_name or "बॉस"

    if not user_text:
        return

    print(f"📩 [{user_name}]: {user_text}", flush=True)

    # 1. Send instant emoji reaction (double-tap / like effect) if enabled
    if auto_reaction_enabled.get(chat_id, True):
        send_smart_reaction(chat_id, message.message_id)

    # 2. Check if user is asking to generate/draw an image in natural language
    lower_text = user_text.lower()
    image_triggers = ["image bana", "photo bana", "tasveer bana", "draw ", "generate image", "wallpaper bana", "picture bana"]
    if any(trigger in lower_text for trigger in image_triggers):
        # Clean prompt
        clean_prompt = user_text
        for trig in image_triggers:
            clean_prompt = clean_prompt.replace(trig, "")
        clean_prompt = clean_prompt.replace("ek", "").replace("ki", "").replace("ka", "").strip()
        if not clean_prompt:
            clean_prompt = user_text
        generate_and_send_image(chat_id, clean_prompt)
        return

    # 3. Show typing indicator in Telegram
    try:
        bot.send_chat_action(chat_id, "typing")
    except Exception:
        pass

    # 4. Get hyper-human reply from Gemini
    try:
        reply = get_gemini_response(chat_id, user_text, user_name)
        send_long_message(chat_id, reply)
        print(f"🤖 [AXIA Replied to {user_name}]", flush=True)
    except Exception as e:
        logging.error(f"Error answering message: {e}")
        bot.send_message(chat_id, f"Arre Boss, thoda technical issue aaya: {e}")


class CloudHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"AXIUS OS - AXIA Telegram Bot is Online 24/7!")

    def log_message(self, format, *args):
        pass  # Suppress health check logs to keep console clean


def start_cloud_health_server():
    """Binds to PORT for Render Free Web Service health checks."""
    port = int(os.getenv("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), CloudHealthHandler)
        print(f"🌐 Cloud Health Check Server live on port {port} (Render Free Tier Ready)", flush=True)
        server.serve_forever()
    except Exception as e:
        print(f"Health server notice: {e}", flush=True)


def run_bot_service():
    """Starts the bot with automatic conflict resolution & crash recovery."""
    print("==================================================", flush=True)
    print("👑 AXIA (AXIUS OS) Super-Companion Bot Online!", flush=True)
    print("👨‍💻 Creator & Visionary: Mayank Vishwakarma (मयंक विश्वकर्मा)", flush=True)
    print("🎨 4K Ultra-HD Image Studio: Active (Free Flux Render)", flush=True)
    print("💖 Auto-Reaction & Like: Active (Real Telegram Reactions)", flush=True)
    print("💬 Real-Life Human Companion Mode: Active", flush=True)
    print("⌨️ Interactive Buttons: Active (Clean & Minimal)", flush=True)
    print("👉 Telegram par jaiye aur @AXIUSOS_bot se chat kijiye!", flush=True)
    print("==================================================", flush=True)

    # Start background health server for Render Free Web Service
    threading.Thread(target=start_cloud_health_server, daemon=True).start()

    # Clean old webhooks / pending conflicts
    try:
        bot.delete_webhook(drop_pending_updates=True)
        time.sleep(1)
    except Exception as e:
        print(f"Webhook cleanup warning: {e}", flush=True)

    # Polling with auto-retry
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"Polling loop encountered error: {e}. Retrying in 3 seconds...", flush=True)
            time.sleep(3)


if __name__ == "__main__":
    run_bot_service()

