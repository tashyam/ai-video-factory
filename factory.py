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
                        words.append([t0, t1, chunk["text"]])
            if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1000:
                subprocess.run(["ffmpeg", "-y", "-i", mp3_path, "-ar", "24000", "-ac", "1", wav_path], check=True)
                if not words:
                    raw_words = full_text.split()
                    step = 0.28
                    words = [[round(i * step, 3), round((i + 1) * step, 3), w] for i, w in enumerate(raw_words)]
                with open(words_path, "w") as f:
                    json.dump(words, f)
                print(f"TTS succeeded with {voice} ({words[-1][1]}s)")
                return words[-1][1]
        except Exception as e:
            print(f"TTS attempt {attempt+1} ({voice}) failed: {e}")
            await asyncio.sleep(2 ** min(attempt, 3))
    raise RuntimeError("edge-tts failed after 6 retries across 4 voices")

def build_deterministic_video_js(proj, num_sentences, total_dur):
    js = f"""import {{ V3, clamp, lerp, ease, DEG, track, run }} from '/_engine/core.js';
import {{ makeStage }} from '/_engine/stage.js';
import {{ addHighway }} from '/_engine/sets/highway.js';
import {{ addRoom }} from '/_engine/sets/room.js';
import {{ makeChar, pose, exprAt, talkAt }} from '/_engine/chars.js';
import {{ makeCar, addInterior, tintGlass, rollWheels, brakeLights, COUPE, SUV }} from '/_engine/cars.js';
import {{ captionsFromWords, sentenceStarts }} from '/_engine/captions.js';
import CAST from './cast.json' with {{ type: 'json' }};
import WORDS from './audio/vo.words.json' with {{ type: 'json' }};

const S = sentenceStarts(WORDS);
const TOTAL = Math.max({total_dur:.2f}, (WORDS.at(-1)?.[1] || 50) + 1.2);
const N = S.length;
const tAt = (i) => i < N ? S[i] : TOTAL;

const st1 = makeStage({{ mood: 'day' }});
addHighway(st1.scene);
const carA = makeCar(COUPE, 0xffbf0a); addInterior(carA, CAST.cars.schemer.interior, true); st1.scene.add(carA);
const carB = makeCar(SUV, 0xbfe9dc); addInterior(carB, false, false); st1.scene.add(carB);
const schemer1 = makeChar(CAST.characters.schemer); carA.body.add(schemer1);
const victim1 = makeChar(CAST.characters.victim); carB.body.add(victim1);

function updateAct1(t) {{
  const x = t * 14;
  carA.position.set(x, 0, 5.55);
  carB.position.set(x - 9.5 + Math.sin(t * 2.2) * 1.4, 0, 5.55);
  rollWheels(carA, x); rollWheels(carB, x);
  brakeLights(carA, Math.sin(t * 3) > 0.2);
  const camSide = Math.floor(t / 3.2) % 2 === 0;
  if (camSide) {{
    st1.camera.position.set(x + 0.35, 1.28, 5.55 - 0.38);
    st1.camera.lookAt(x + 0.15, 1.18, 5.55 + 0.2);
  }} else {{
    st1.camera.position.set(x - 4.5, 2.2 + 0.15 * Math.sin(t), 5.55 - 3.6);
    st1.camera.lookAt(x - 2.0, 1.1, 5.55);
  }}
  st1.frame(); st1.follow(x - 4, 0, 5.55);
  pose(schemer1, {{ hip: V3(-0.2, 0.53, -0.30), neck: V3(-0.18, 0.83, -0.30), face: schemer1.headWorld(), expr: exprAt([[0,'smug'],[3,'grin'],[6,'jolt']], t),
    arms: [[V3(0.12, 0.62, -0.58), V3(0.28, 0.72, -0.52)], [V3(0.12, 0.62, -0.16), V3(0.28, 0.72, -0.22)]],
    legs: [[V3(0.06, 0.40, -0.50), V3(0.45, 0.20, -0.52)], [V3(0.06, 0.40, -0.36), V3(0.45, 0.20, -0.34)]] }}, st1.camera);
  pose(victim1, {{ hip: V3(-0.22, 0.88, -0.40), neck: V3(-0.20, 1.18, -0.40), face: victim1.headWorld(), expr: exprAt([[0,'calm'],[4,'shock'],[8,'dazed']], t),
    arms: [[V3(0.08, 0.95, -0.65), V3(0.26, 1.05, -0.58)], [V3(0.08, 0.95, -0.15), V3(0.26, 1.05, -0.22)]],
    legs: [[V3(0.05, 0.72, -0.55), V3(0.42, 0.50, -0.55)], [V3(0.05, 0.72, -0.25), V3(0.42, 0.50, -0.25)]] }}, st1.camera);
}}

const st2 = makeStage({{ mood: 'dusk' }});
addRoom(st2.scene, {{ kind: 'office' }});
const schemer2 = makeChar(CAST.characters.schemer); st2.scene.add(schemer2);
const officer2 = makeChar(CAST.characters.officer); st2.scene.add(officer2);

function updateAct2(t) {{
  const push = (t % 4.0) * 0.14;
  const flip = Math.floor(t / 3.5) % 2 === 0;
  if (flip) {{
    st2.camera.position.set(-0.9, 1.48, 2.35 - push);
    st2.camera.lookAt(-0.75, 1.32, 0.2);
  }} else {{
    st2.camera.position.set(0.95, 1.52, 2.35 - push);
    st2.camera.lookAt(0.75, 1.35, 0.2);
  }}
  st2.frame();
  pose(schemer2, {{ hip: V3(-0.85, 0.92, 0.2), neck: V3(-0.85, 1.24, 0.2), face: schemer2.headWorld(), expr: exprAt([[0,'smug'],[5,'worried'],[10,'panic']], t),
    arms: [[V3(-1.05, 1.15, 0.2), V3(-0.65, 1.05, 0.45)], [V3(-0.65, 1.15, 0.2), V3(-0.45, 1.10, 0.45)]],
    legs: [[V3(-0.95, 0.52, 0.2), V3(-0.95, 0.05, 0.22)], [V3(-0.75, 0.52, 0.2), V3(-0.75, 0.05, 0.18)]] }}, st2.camera);
  pose(officer2, {{ hip: V3(0.85, 0.96, 0.2), neck: V3(0.85, 1.30, 0.2), face: officer2.headWorld(), expr: exprAt([[0,'stern'],[6,'angry'],[12,'grin']], t),
    arms: [[V3(0.65, 1.20, 0.2), V3(0.45, 1.18, 0.48)], [V3(1.05, 1.20, 0.2), V3(1.12, 0.95, 0.25)]],
    legs: [[V3(0.75, 0.54, 0.2), V3(0.75, 0.05, 0.2)], [V3(0.95, 0.54, 0.2), V3(0.95, 0.05, 0.2)]] }}, st2.camera);
}}

const st3 = makeStage({{ mood: 'rain' }});
addHighway(st3.scene, {{ wet: true }});
const carC = makeCar(SUV, 0x3b82f6); addInterior(carC, true, true); st3.scene.add(carC);
const quiet3 = makeChar(CAST.characters.quiet); carC.body.add(quiet3);

function updateAct3(t) {{
  const x = t * 11;
  carC.position.set(x, 0, 1.85);
  rollWheels(carC, x);
  st3.camera.position.set(x + 0.28, 1.36, 1.85 - 0.34);
  st3.camera.lookAt(x + 0.85, 1.28, 1.85 + 0.12);
  st3.frame(); st3.follow(x - 3, 0, 1.85);
  pose(quiet3, {{ hip: V3(-0.22, 0.88, -0.40), neck: V3(-0.20, 1.18, -0.40), face: quiet3.headWorld(), expr: exprAt([[0,'calm'],[4,'innocent'],[8,'grin']], t),
    arms: [[V3(0.08, 0.95, -0.65), V3(0.32, 1.15, -0.42)], [V3(0.08, 0.95, -0.15), V3(0.28, 1.05, -0.22)]],
    legs: [[V3(0.05, 0.72, -0.55), V3(0.42, 0.50, -0.55)], [V3(0.05, 0.72, -0.25), V3(0.42, 0.50, -0.25)]] }}, st3.camera);
}}

const cut1 = tAt(Math.max(1, Math.floor(N * 0.38)));
const cut2 = tAt(Math.max(2, Math.floor(N * 0.72)));

run({{
  shots: [
    {{ start: 0, end: cut1, stage: st1, update: updateAct1, grade: st1.grade, type: 'interior', dof: {{ clnf: 0, focus: 2 }} }},
    {{ start: cut1, end: cut2, stage: st2, update: updateAct2, grade: st2.grade, type: 'twoshot', dof: {{ clnf: 0, focus: 2 }} }},
    {{ start: cut2, end: TOTAL, stage: st3, update: updateAct3, grade: st3.grade, type: 'interior', dof: {{ clnf: 0, focus: 2 }} }}
  ],
  captions: captionsFromWords(WORDS),
  sound: [],
  music: []
}});
"""
    with open(f"{proj}/video.js", "w") as f:
        f.write(js)

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
