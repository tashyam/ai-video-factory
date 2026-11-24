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
    if len(sentences) < 4:
        raise RuntimeError(f"Too few sentences parsed from Groq output:\n{raw_text}")
    return title, hashtags, sentences[:19]

async def build_voice(proj, sentences):
    import shutil
    text = " ".join(sentences)
    os.makedirs(f"{proj}/audio", exist_ok=True)
    with open(f"{proj}/script.json", "w", encoding="utf-8") as f:
        json.dump(sentences, f, indent=2)
    mp3_path = f"{proj}/audio/vo.mp3"
    wav_path = f"{proj}/audio/vo.wav"
    voices = ["en-US-AndrewMultilingualNeural", "en-US-GuyNeural", "en-US-ChristopherNeural"]
    tts_ok = False
    for v in voices:
        r = subprocess.run(
            ["edge-tts", "--voice", v, "--rate=+8%", "--text", text, "--write-media", mp3_path],
            capture_output=True, text=True
        )
        if r.returncode == 0 and os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1000:
            tts_ok = True
            break
    if not tts_ok:
        from gtts import gTTS
        gTTS(text=text, lang="en", tld="co.uk").save(mp3_path)
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path, "-af", "atempo=1.10,aresample=24000", "-ac", "1", wav_path],
        check=True
    )
    kit_py = "3d-video-studio/kit/.venv/bin/python"
    if not os.path.exists(kit_py):
        kit_py = "python3"
    align = subprocess.run(
        [kit_py, "3d-video-studio/kit/words.py", wav_path, f"{proj}/script.json"],
        capture_output=True, text=True
    )
    words_json = f"{proj}/audio/vo.words.json"
    if align.returncode == 0 and os.path.exists(words_json):
        words = json.load(open(words_json, encoding="utf-8"))
        dur = words[-1]["e"] if words else 25.0
        return words, dur
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", wav_path],
        capture_output=True, text=True
    )
    dur = float(probe.stdout.strip() or 25.0)
    raw_words = text.split()
    step = dur / max(len(raw_words), 1)
    words = [{"w": w, "s": round(i * step, 3), "e": round((i + 1) * step, 3)} for i, w in enumerate(raw_words)]
    with open(words_json, "w", encoding="utf-8") as f:
        json.dump(words, f, indent=2)
    return words, dur

def build_deterministic_video_js(proj, num_sentences, total_dur):
    tpl = open("3d-video-studio/engine/template/video.js").read()
    header = 'import { captionsFromWords } from "engine/captions.js";\nimport WORDS from "./audio/vo.words.json" with { type: "json" };\n'
    tpl = header + tpl
    tpl = "window.samplesAt = () => 1;\n" + tpl.replace("const DUR = 5;", f"const DUR = Math.max({total_dur:.2f}, (WORDS.at(-1)?.e || 45) + 1.2);")
    tpl = tpl.replace("end: 5,", "end: DUR,")
    c_start = tpl.index("captions: [")
    c_end = tpl.index("samples:")
    tpl = tpl[:c_start] + "captions: captionsFromWords(WORDS),\n  " + tpl[c_end:]
    tpl += "\nwindow.samplesAt = () => 1;\n"
    with open(f"{proj}/video.js", "w") as f:
        f.write(tpl)


def generate_custom_video_js(proj, topic, sentences, words, total_dur):
    tpl = open("3d-video-studio/engine/template/video.js", encoding="utf-8").read()
    api_doc = open("3d-video-studio/engine/API.md", encoding="utf-8").read()[:14000]
    dur_val = round(total_dur + 1.0, 2)
    prompt = f"""You are an expert Three.js choreographer for 3d-video-studio.
Write a complete, valid ES-module `video.js` for a 9:16 YouTube Short.
Topic: {topic}
Total Duration: {dur_val} seconds
Sentences: {json.dumps(sentences)}

CRITICAL RULES:
1. Follow the exact imports and structure of the template `video.js` below, and ONLY use functions documented in API.md.
2. Set `const DUR = {dur_val};` and load words from `./audio/vo.words.json` using:
   `import WORDS from "./audio/vo.words.json" with {{ type: "json" }};`
   and pass `captions: captionsFromWords(WORDS)` to `run(...)`.
3. Create 6 to 8 dynamic camera `shots` spanning from `t = 0` all the way to `t = {dur_val}` (never freeze the camera!). Use smooth camera glides (`track(...)`) across multiple angles (interior, wide tracking, close-up reaction, overhead/side push-in, final reveal).
4. Include expressive character animations (`talkAt`, `exprAt`, `stand`, `sit`) and props/signs (`plateTex`, `sign`) matching the story beats.
5. Output ONLY valid JavaScript code—no markdown fences, no explanations.

API REFERENCE:
{api_doc}

WORKING TEMPLATE REFERENCE:
{tpl}
"""
    for model in ["openai/gpt-oss-120b", "qwen/qwen3-32b", "llama-3.3-70b-versatile"]:
        try:
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4,
                    "max_tokens": 6000
                },
                timeout=90
            )
            if r.status_code != 200:
                continue
            code = r.json()["choices"][0]["message"]["content"].strip()
            if code.startswith("```"):
                code = "\n".join(line for line in code.splitlines() if not line.strip().startswith("```"))
            code += "\nwindow.samplesAt = () => 1;\n"
            with open(f"{proj}/video.js", "w", encoding="utf-8") as f:
                f.write(code)
            chk = subprocess.run(
                ["node", "3d-video-studio/engine/film.mjs", "check", proj],
                capture_output=True, text=True, timeout=45
            )
            if chk.returncode == 0:
                print(f"Custom multi-scene video.js passed film.mjs check ({model})")
                return
            print(f"Check failed for {model}: {chk.stdout[-300:]}")
        except Exception as e:
            print(f"Scene gen error ({model}): {e}")

    # Multi-shot dynamic camera fallback if LLM scene fails check
    print("Using multi-shot dynamic template fallback...")
    fallback = tpl.replace("const DUR = 5;", f"const DUR = {dur_val};")
    fallback = fallback.replace(
        "const WORDS = [",
        'import REAL_WORDS from "./audio/vo.words.json" with { type: "json" };\nconst WORDS = REAL_WORDS.length ? REAL_WORDS : ['
    )
    loop_shots = f"""
const _baseShots = shots.slice();
while (shots[shots.length - 1].end < DUR) {{
  const lastEnd = shots[shots.length - 1].end;
  const idx = shots.length % _baseShots.length;
  const span = Math.min(3.5, DUR - lastEnd);
  if (span <= 0.2) break;
  const s = Object.assign({{}}, _baseShots[idx], {{ start: lastEnd, end: +(lastEnd + span).toFixed(2) }});
  shots.push(s);
}}
window.samplesAt = () => 1;
"""
    fallback = fallback.replace("run({", loop_shots + "\nrun({")
    with open(f"{proj}/video.js", "w", encoding="utf-8") as f:
        f.write(fallback)

def main():
    topic = pick_topic()
    print(f"Selected topic: {topic}")
    proj = "3d-video-studio/project_out"
    subprocess.run(["rm", "-rf", proj], check=True)
    subprocess.run(["cp", "-r", "3d-video-studio/engine/template", proj], check=True)
    os.makedirs(f"{proj}/audio", exist_ok=True)
    os.makedirs(f"{proj}/out", exist_ok=True)

    script_prompt = f"""Write a 22-second ultra-punchy, fast-paced fake-origin YouTube Shorts narration about: "{topic}".
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
... (5 to 6 short punchy sentences total)"""

    raw_script = groq_chat(script_prompt)
    title, hashtags, sentences = parse_script_lines(raw_script, topic)
    print(f"Generated title: {title} ({len(sentences)} sentences)")

    with open(f"{proj}/script.json", "w") as f:
        json.dump(sentences, f, indent=2)

    words, dur = asyncio.run(build_voice(proj, sentences))

    subprocess.run(["node", "3d-video-studio/engine/cast.mjs", "new", proj,
                    "--chars", "schemer,quiet,victim,officer",
                    "--cars", "schemer,quiet,traffic"], check=True)

    generate_custom_video_js(proj, topic, sentences, words, dur)

    os.makedirs(f"{proj}/out", exist_ok=True)
    subprocess.run(["node", "3d-video-studio/engine/film.mjs", "render", proj, f"{proj}/out/silent.mp4", "0", f"{dur + 1.2:.2f}"], check=True)
    final_mp4 = f"{proj}/out/final_short.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", f"{proj}/out/silent.mp4", "-i", final_audio,
        "-map", "0:v", "-map", "1:a", "-vf", "scale=1080:1920:flags=lanczos", "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
        "-af", "apad,loudnorm=I=-14:TP=-1.5", "-shortest", final_mp4
    ], check=True)

    if TG_TOKEN and TG_CHAT and os.path.exists(final_mp4):
        caption = f"🎬 {title}\n\n{hashtags}"
        with open(final_mp4, "rb") as vid:
            resp = requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendVideo",
                data={"chat_id": TG_CHAT, "caption": caption[:1024]},
                files={"video": vid},
                timeout=120
            )
        print("Telegram response:", resp.status_code)

if __name__ == "__main__":
    main()
