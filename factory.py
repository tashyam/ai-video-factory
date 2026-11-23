import os, sys, json, asyncio, subprocess, random, requests
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

def groq_chat(prompt, json_mode=False):
    if not GROQ_KEY:
        raise RuntimeError("GROQ_API_KEY secret is empty!")
    models = [m["id"] for m in requests.get(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {GROQ_KEY}"}
    ).json().get("data", []) if not any(x in m["id"] for x in ["whisper", "tts", "guard", "embed"])]
    model = next((m for m in ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "qwen/qwen3-32b", "llama-3.1-8b-instant"] if m in models), models[0])
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.75
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; VideoFactory/1.0)"
        },
        json=body,
        timeout=60
    )
    if not r.ok:
        raise RuntimeError(f"Groq API {r.status_code}: {r.text}")
    return r.json()["choices"][0]["message"]["content"]

def pick_topic():
    if RAW_TOPIC and RAW_TOPIC.lower() != "auto":
        return RAW_TOPIC
    used_file = "used_topics.json"
    used = json.load(open(used_file)) if os.path.exists(used_file) else []
    remaining = [t for t in CURIOSITY_TOPICS if t not in used]
    if not remaining:
        ask = f"""Generate 1 viral YouTube Shorts curiosity-gap title following the exact pattern:
'Why [everyday group] started [weird behavior]' (never name the invention).
Do NOT repeat any of these: {json.dumps(used)}.
Return ONLY JSON: {{"topic": "..."}}"""
        topic = json.loads(groq_chat(ask, json_mode=True))["topic"]
    else:
        topic = random.choice(remaining)
    used.append(topic)
    with open(used_file, "w") as f:
        json.dump(used, f, indent=2)
    return topic

async def build_voice(sentences, wav_path, words_path):
    full_text = " ".join(sentences)
    communicate = edge_tts.Communicate(full_text, "en-US-AndrewMultilingualNeural", rate="+6%")
    mp3_path = wav_path.replace(".wav", ".mp3")
    words = []
    with open(mp3_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                t0 = round(chunk["offset"] / 10_000_000, 3)
                t1 = round((chunk["offset"] + chunk["duration"]) / 10_000_000, 3)
                words.append([t0, t1, chunk["text"]])
    subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "24000", "-ac", "1", wav_path], check=True)
    with open(words_path, "w") as f:
        json.dump(words, f)
    return words[-1][1] if words else 55.0

def main():
    topic = pick_topic()
    print(f"Selected topic: {topic}")
    proj = "3d-video-studio/project_out"
    subprocess.run(["rm", "-rf", proj], check=True)
    subprocess.run(["cp", "-r", "3d-video-studio/engine/template", proj], check=True)
    os.makedirs(f"{proj}/audio", exist_ok=True)
    os.makedirs(f"{proj}/out", exist_ok=True)

    with open("3d-video-studio/story/script-template.md") as f:
        tpl = f.read()
    with open("3d-video-studio/engine/API.md") as f:
        api_doc = f.read()

    script_prompt = f"""Write a 60-second viral comedy fake-origin script about: "{topic}".
Follow this exact structure & rules:
{tpl}
Return ONLY valid JSON: {{
  "title": "Curiosity-gap YouTube Shorts title (never name the invention)",
  "description": "2-line engaging YouTube Shorts description with 4 viral hashtags",
  "sentences": ["sentence 1", "sentence 2", "..."]
}} (16 to 19 short punchy sentences, ~230 words total)."""
    script_data = json.loads(groq_chat(script_prompt, json_mode=True))
    sentences = script_data["sentences"]
    with open(f"{proj}/script.json", "w") as f:
        json.dump(sentences, f, indent=2)

    dur = asyncio.run(build_voice(sentences, f"{proj}/audio/vo.wav", f"{proj}/audio/vo.words.json"))

    subprocess.run(["node", "3d-video-studio/engine/cast.mjs", "new", proj,
                    "--chars", "schemer,quiet,victim,officer",
                    "--cars", "schemer,quiet,traffic"], check=True)

    code_prompt = f"""You are writing `video.js` for a Three.js 3D animated Short.
Total duration: {dur:.2f} seconds across {len(sentences)} sentences: {json.dumps(sentences)}
Engine API reference:
{api_doc[:11000]}

Write a complete, valid ES module `video.js` that:
1. Imports `run`, `track`, `V3`, `DEG`, `ease`, `clamp` from '../engine/core.js', `makeStage` from '../engine/stage.js', `addHighway` from '../engine/sets/highway.js', `addRoom` from '../engine/sets/room.js', `makeChar`, `pose`, `exprAt`, `talkAt` from '../engine/chars.js', `makeCar`, `addInterior`, `rollWheels` from '../engine/cars.js', `captionsFromWords`, `sentenceStarts` from '../engine/captions.js', and `CAST` from './cast.json' with `{{ type: 'json' }}` and `WORDS` from './audio/vo.words.json' with `{{ type: 'json' }}`.
2. Builds 3 mood acts (`day`, `dusk`, `rain`) with `makeStage`, `addHighway` / `addRoom`, `makeChar` + `pose` + `talkAt` + `exprAt` for all {len(sentences)} sentence shots synced via `sentenceStarts(WORDS)`.
3. Calls `run({{ shots, captions: captionsFromWords(WORDS), sound: [], music: [] }})`.
Output ONLY raw JavaScript code (no markdown fences)."""
    video_js = groq_chat(code_prompt).strip()
    if video_js.startswith("```"):
        video_js = "\n".join(video_js.split("\n")[1:-1])
    with open(f"{proj}/video.js", "w") as f:
        f.write(video_js)

    subprocess.run(["node", "3d-video-studio/engine/film.mjs", "render", proj, f"{proj}/out/silent.mp4"], check=True)
    final_mp4 = f"{proj}/out/final_short.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-i", f"{proj}/out/silent.mp4", "-i", f"{proj}/audio/vo.wav",
        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-af", "apad,loudnorm=I=-14:TP=-1.5", "-shortest", final_mp4
    ], check=True)

    if TG_TOKEN and TG_CHAT and os.path.exists(final_mp4):
        caption = f"🎬 {script_data.get('title', topic)}\n\n{script_data.get('description', '')}"
        with open(final_mp4, "rb") as vid:
            requests.post(
                f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TG_TOKEN}/sendVideo",
                data={"chat_id": TG_CHAT, "caption": caption[:1024]},
                files={"video": vid},
                timeout=120
            )

if __name__ == "__main__":
    main()
