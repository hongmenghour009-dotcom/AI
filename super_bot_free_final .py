import os
import re
import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from groq import Groq
from pydub import AudioSegment
from gtts import gTTS

# ================= CONFIG =================
TELEGRAM_BOT_TOKEN = ""
GROQ_API_KEY = ""
HF_TOKEN = ""

groq_client = Groq(api_key=GROQ_API_KEY)

HF_HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}"
}

# ================= CLEAN TEXT FOR TTS =================
def clean_text_for_tts(text: str) -> str:
    text = re.sub(r"\*\*||\*|_", "", text)
    text = re.sub(r"[-•●▪️►]+", " ", text)
    text = re.sub(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "]+",
        "",
        text,
        flags=re.UNICODE
    )
    text = re.sub(r"[#@|<>]", "", text)
    return re.sub(r"\s+", " ", text).strip()

# ================= KEYBOARD =================
def main_keyboard(lang="kh"):
    if lang == "en":
        keys = [
            ["💬 Chat AI", "🎨 Create Image"],
            ["🎤 Talk to AI", "🔊 Voice ON/OFF"],
            ["🌐 Language", "🧹 Clear"]
        ]
    else:
        keys = [
            ["💬 ជជែក AI", "🎨 បង្កើតរូបភាព"],
            ["🎤 និយាយជាមួយ AI", "🔊 សំឡេង បិទ/បើក"],
            ["🌐 ប្ដូរភាសា", "🧹 លុប"]
        ]
    return ReplyKeyboardMarkup(keys, resize_keyboard=True)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.update({
        "lang": "kh",
        "mode": "chat",
        "voice_reply": True
    })
    await update.message.reply_text(
        "🚀 AI SUPER BOT (FREE)\nសូមជ្រើសរើសមុខងារ 👇",
        reply_markup=main_keyboard("kh")
    )

# ================= TEXT TO VOICE =================
async def text_to_voice(update, text, lang):
    text = clean_text_for_tts(text)

    try:
        tts_lang = "en" if lang == "en" else "km"
        tts = gTTS(text=text, lang=tts_lang)
        tts.save("reply.mp3")
        await update.message.reply_voice(open("reply.mp3", "rb"))
    except Exception as e:
        print("TTS error:", e)
        await update.message.reply_text(text)

# ================= CHAT AI =================
async def chat_ai(update, user_text, context):
    lang = context.user_data["lang"]
    voice_reply = context.user_data["voice_reply"]

    system_prompt = (
        "Always reply in Khmer language using clear Khmer."
        if lang == "kh"
        else
        "Always reply in English."
    )

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ],
        max_tokens=300
    )

    reply = response.choices[0].message.content.strip()

    if voice_reply:
        await text_to_voice(update, reply, lang)
    else:
        await update.message.reply_text(reply)

# ================= IMAGE =================
async def generate_image(update, prompt):
    url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-2"
    r = requests.post(url, headers=HF_HEADERS, json={"inputs": prompt})

    if r.status_code != 200:
        await update.message.reply_text("❌ បង្កើតរូបភាពមិនបាន")
        return

    with open("image.png", "wb") as f:
        f.write(r.content)

    await update.message.reply_photo(photo=open("image.png", "rb"))

# ================= TEXT HANDLER =================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    lang = context.user_data["lang"]

    if text in ["🌐 ប្ដូរភាសា", "🌐 Language"]:
        context.user_data["lang"] = "en" if lang == "kh" else "kh"
        await update.message.reply_text(
            "Language switched",
            reply_markup=main_keyboard(context.user_data["lang"])
        )
        return

    if text in ["🔊 សំឡេង បិទ/បើក", "🔊 Voice ON/OFF"]:
        context.user_data["voice_reply"] = not context.user_data["voice_reply"]
        await update.message.reply_text(
            f"🔊 Voice reply: {'ON' if context.user_data['voice_reply'] else 'OFF'}"
        )
        return

    if text in ["🎨 បង្កើតរូបភាព", "🎨 Create Image"]:
        context.user_data["mode"] = "image"
        await update.message.reply_text("✍️ វាយ prompt សម្រាប់រូបភាព")
        return

    if text in ["💬 ជជែក AI", "💬 Chat AI"]:
        context.user_data["mode"] = "chat"
        await update.message.reply_text("💬 Chat mode")
        return

    if context.user_data["mode"] == "image":
        await generate_image(update, text)
        return

    await chat_ai(update, text, context)

# ================= VOICE INPUT (FIXED) =================
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.voice.get_file()
    await file.download_to_drive("voice.ogg")

    sound = AudioSegment.from_ogg("voice.ogg")
    sound.export("voice.wav", format="wav")

    url = "https://api-inference.huggingface.co/models/openai/whisper-base"
    r = requests.post(url, headers=HF_HEADERS, data=open("voice.wav", "rb"))

    if r.status_code != 200:
        await update.message.reply_text("❌ Voice recognition failed")
        return

    try:
        data = r.json()
        text = data.get("text", "")
    except Exception:
        await update.message.reply_text("❌ Whisper response error")
        return

    if not text.strip():
        await update.message.reply_text("❌ មិនស្គាល់សំឡេង")
        return

    await chat_ai(update, text, context)

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    print("🤖 SUPER BOT FINAL running...")
    app.run_polling()

if __name__ == "__main__":
    main()