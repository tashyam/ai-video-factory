import os, sys, json, asyncio, subprocess, urllib.request
import edge_tts

GROQ_KEY = os.environ["GROQ_API_KEY"]
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
TOPIC = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].strip() else "Why drivers started filming the road"

def groq_chat(prompt, json_mode=False):
    body = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]

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
    proj = "3d-video-studio/project_out"
    subprocess.run(["rm", "-rf", proj], check=True)
    subprocess.run(["cp", "-r", "3d-video-studio/engine/template", proj], check=True)
    os.makedirs(f"{proj}/audio", exist_ok=True)
    os.makedirs(f"{proj}/out", exist_ok=True)

    with open("3d-video-studio/story/script-template.md") as f:
        tpl = f.read()
    with open("3d-video-studio/engine/API.md") as f:
        api_doc = f.read()

    script_prompt = f"""Write a 60-second viral comedy fake-origin script about: "{TOPIC}".
Follow this exact structure & rules:
{tpl}
Return ONLY valid JSON: {{"title": "...", "sentences": ["sentence 1", "sentence 2", ...]}} (16 to 19 short punchy sentences, ~230 words total)."""
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
        subprocess.run([
            "curl", "-s", "-F", f"chat_id={TG_CHAT}",
            "-F", f"caption=🎬 {script_data.get('title', TOPIC)}",
            "-F", f"video=@{final_mp4}",
            f"[https://api.telegram.org/bot](https://api.telegram.org/bot){TG_TOKEN}/sendVideo"
        ], check=True)

if __name__ == "__main__":
    main()
