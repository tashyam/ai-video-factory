import os, sys, json, time, asyncio, subprocess, random, requests
import edge_tts

GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
RAW_TOPIC = sys.argv[1].strip() if len(sys.argv) > 1 else ""

CURIOSITY_TOPICS = [
    "Why drivers started filming the road",
    "Why banks stopped trusting handwritten signatures",
    "Why stores started putting black stripes on every box",
    "Why ATMs started swallowing debit cards",
    "Why delivery drivers started taking doorway photos",
    "Why parking lots started adding yellow speed bumps",
    "Why taxis started mounting glowing signs on the roof",
    "Why offices started locking doors with plastic keycards",
    "Why gas stations started making you pay before pumping",
    "Why hotels started putting tiny peepholes in every door"
]

def groq_chat(prompt):
    if not GROQ_KEY:
        raise RuntimeError("GROQ_API_KEY secret is empty!")
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; VideoFactory/1.0)"
    }
    models_resp = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=30).json()
    available = [m["id"] for m in models_resp.get("data", [])]
    skip = ("whisper", "tts", "guard", "embed", "orpheus", "playai", "distil-whisper", "safeguard")
    candidates = [m for m in available if not any(s in m.lower() for s in skip)]
    preferred = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "meta-llama/llama-4-scout-17b-16e-instruct", "qwen/qwen3-32b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    ordered = [m for m in preferred if m in candidates] + [m for m in candidates if m not in preferred]
    print(f"Candidate Groq models: {ordered}")

    last_err = ""
    for model in ordered:
        print(f"Trying Groq model: {model}")
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 4096
            },
            timeout=60
        )
        if r.ok:
            msg = r.json()["choices"][0]["message"]
            content = (msg.get("content") or "").strip()
            # Strip <think>...</think> blocks if a reasoning model responds
            if "</think>" in content:
                content = content.split("</think>", 1)[1].strip()
            if content:
                print(f"Success with model: {model}")
                return content
            last_err = f"{model} returned empty content"
        else:
            last_err = f"{model} -> {r.status_code}: {r.text[:160]}"
        print(f"Skipping {last_err}")
    raise RuntimeError(f"All Groq models failed. Last error: {last_err}")

def pick_topic():
    if RAW_TOPIC and RAW_TOPIC.lower() != "auto":
        return RAW_TOPIC
    used_file = "used_topics.json"
    used = json.load(open(used_file)) if os.path.exists(used_file) else []
    remaining = [t for t in CURIOSITY_TOPICS if t not in used]
    topic = random.choice(remaining if remaining else CURIOSITY_TOPICS)
    used.append(topic)
    with open(used_file, "w") as f:
        json.dump(used[-50:], f, indent=2)
    return topic

def parse_script_lines(raw_text, topic):
    lines = [ln.strip().lstrip("-•*0123456789. ") for ln in raw_text.splitlines() if ln.strip()]
    title = topic
    hashtags = "#shorts #animation #history #didyouknow"
    sentences = []
    for ln in lines:
        low = ln.lower()
        if low.startswith("title:"):
            title = ln.split(":", 1)[1].strip().strip('"')
        elif low.startswith("tags:") or low.startswith("hashtags:"):
            hashtags = ln.split(":", 1)[1].strip()
        elif not ln.startswith("{") and not ln.startswith("}") and not ln.startswith("```"):
            sentences.append(ln.strip('"'))
    if len(sentences) < 8:
        raise RuntimeError(f"Too few sentences parsed from Groq output:\n{raw_text}")
    return title, hashtags, sentences[:19]

async def build_voice(sentences, wav_path, words_path):
    import re
    clean_sentences = [re.sub(r"[^a-zA-Z0-9.,!?'\s-]", "", s).strip() for s in sentences]
    full_text = " ".join([s for s in clean_sentences if s])
    mp3_path = wav_path.replace(".wav", ".mp3")
    voices = ["en-US-GuyNeural", "en-US-AndrewMultilingualNeural", "en-US-ChristopherNeural", "en-US-AriaNeural"]
    for attempt in range(6):
        voice = voices[attempt % len(voices)]
        words = []
        try:
            communicate = edge_tts.Communicate(full_text, voice)
            with open(mp3_path, "wb") as f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        t0 = round(chunk["offset"] / 10_000_000, 3)
                        t1 = round((chunk["offset"] + chunk["duration"]) / 10_000_000, 3)
                        words.append({"w": chunk["text"], "s": t0, "e": t1})
            if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1000:
                subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "24000", "-ac", "1", wav_path], check=True)
                if not words:
                    raw_words = full_text.split()
                    step = 0.28
                    words = [{"w": w, "s": round(i * step, 3), "e": round((i + 1) * step, 3)} for i, w in enumerate(raw_words)]
                with open(words_path, "w") as f:
                    json.dump(words, f)
                print(f"TTS succeeded with {voice} ({words[-1][1]}s)")
                return words[-1]["e"]
        except Exception as e:
            print(f"TTS attempt {attempt+1} ({voice}) failed: {e}")
            await asyncio.sleep(2 ** min(attempt, 3))
    raise RuntimeError("edge-tts failed after 6 retries across 4 voices")

def build_deterministic_video_js(proj, num_sentences, total_dur):
    tpl = open("3d-video-studio/engine/template/video.js").read()
    header = 'import { captionsFromWords } from "engine/captions.js";\nimport WORDS from "./audio/vo.words.json" with { type: "json" };\n'
    tpl = header + tpl
    tpl = tpl.replace("const DUR = 5;", f"const DUR = Math.max({total_dur:.2f}, (WORDS.at(-1)?.e || 45) + 1.2);")
    tpl = tpl.replace("end: 5,", "end: DUR,")
    c_start = tpl.index("captions: [")
    c_end = tpl.index("samples:")
    tpl = tpl[:c_start] + "captions: captionsFromWords(WORDS),\n  " + tpl[c_end:]
    with open(f"{proj}/video.js", "w") as f:
        f.write(tpl)

def main():
    topic = pick_topic()
    print(f"Selected topic: {topic}")
    proj = "3d-video-studio/project_out"
    subprocess.run(["rm", "-rf", proj], check=True)
    subprocess.run(["cp", "-r", "3d-video-studio/engine/template", proj], check=True)
    os.makedirs(f"{proj}/audio", exist_ok=True)
    os.makedirs(f"{proj}/out", exist_ok=True)

    script_prompt = f"""Write a 60-second funny, fast-paced fake-origin YouTube Shorts narration about: "{topic}".
Rules:
- Hook in sentence 1: past tense, a bold schemer pulls a clever scam/loophole.
- Middle: he repeats it, escalates, makes easy money, until a quiet ordinary person uses a simple everyday object that ruins the whole trick.
- Reveal at the end: name the everyday invention humbly ("...and that's how the [invention] was invented.").
- Short punchy visual sentences (8 to 14 words each). No bullet symbols, no scene directions, no JSON.
Output format (strictly plain text lines):
TITLE: <Curiosity-gap Shorts YouTube invention naming the title without>
TAGS: <4 viral hashtags>
<Sentence 1>
<Sentence 2>
... (15 to 18 sentences total)"""

    raw_script = groq_chat(script_prompt)
    title, hashtags, sentences = parse_script_lines(raw_script, topic)
    print(f"Generated title: {title} ({len(sentences)} sentences)")

    with open(f"{proj}/script.json", "w") as f:
        json.dump(sentences, f, indent=2)

    dur = asyncio.run(build_voice(sentences, f"{proj}/audio/vo.wav", f"{proj}/audio/vo.words.json"))

    subprocess.run(["node", "3d-video-studio/engine/cast.mjs", "new", proj,
                    "--chars", "schemer,quiet,victim,officer",
                    "--cars", "schemer,quiet,traffic"], check=True)

    build_deterministic_video_js(proj, len(sentences), dur)

    subprocess.run(["node", "3d-video-studio/engine/film.mjs", "render", proj, f"{proj}/out/silent.mp4"], check=True)
    final_mp4 = f"{proj}/out/final_short.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", f"{proj}/out/silent.mp4", "-i", f"{proj}/audio/vo.wav",
        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-af", "apad,loudnorm=I=-14:TP=-1.5", "-shortest", final_mp4
    ], check=True)

    if TG_TOKEN and TG_CHAT and os.path.exists(final_mp4):
        caption = f"🎬 {title}\n\n{hashtags}"
        with open(final_mp4, "rb") as vid:
            resp = requests.post(
                f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TG_TOKEN}/sendVideo",
                data={"chat_id": TG_CHAT, "caption": caption[:1024]},
                files={"video": vid},
                timeout=120
            )
        print("Telegram response:", resp.status_code)

if __name__ == "__main__":
    main()
