import os, sys, json, time, asyncio, subprocess, random, requests
import edge_tts

GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip().strip()
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
    import re as _re, random as _rnd
    dur_val = round(max(total_dur + 1.0, (words[-1]["e"] if words else 15.0) + 1.0), 2)
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    safe_topic = topic.replace('"', "'")

    # Compact, exact 3d-video-studio API cheat sheet (<2,500 tokens total -> zero 413 TPM errors!)
    compact_api = """EXACT ENGINE IMPORTS & SIGNATURES (ONLY USE THESE):
import { THREE, V3, clamp, lerp, smooth, ease, DEG, rng, canvas, ctex, table, track, run } from "engine/core.js";
import { makeStage } from "engine/stage.js";
import { addHighway } from "engine/sets/highway.js";
import { addHouse } from "engine/sets/house.js";
import { addRoom } from "engine/sets/room.js";
import { point, box, plateTex, blobShadow, lacquer } from "engine/materials.js";
import { makeCar, addInterior, tintGlass, rollWheels, brakeLights, COUPE, SUV, IC, IS } from "engine/cars.js";
import { makeChar, exprAt, stand, sit, sitOn, talkAt } from "engine/chars.js";
import { sign, desk, chair, laptop, shelf, safe, cashPile, camBox, screen, counter, panel } from "engine/props.js";
import { forest, houseRow, guardrail, grassTufts, bushRow, paintedTree } from "engine/scenery.js";
import { puffs, tyreSmoke, skids, skid, debris } from "engine/fx.js";
import { captionsFromWords, sentenceStarts } from "engine/captions.js";
import WORDS from "./audio/vo.words.json" with { type: "json" };

STAGE & SETS:
- const st = makeStage({ mood: "day" | "dusk" | "night" | "rain" }); const { scene, camera } = st;
- Indoor room: addRoom(scene, { kind: "office" | "kitchen" | "living" | "shop", x: 0, z: 0, d: 8, w: 8, h: 3.4, wall: 0xd8d2c5, floor: "wood" | "tile" | "carpet", view: "trees" | "street" | "skyline", plate: "TOPIC TITLE", sign: "SHORT SIGN" });
- Suburban house/street: addHouse(scene, { x: 0, z: 0, depth: 8, storeys: 2, roof: "front", siding: 0xc9b99a, doorColor: 0x7a3b2e, garage: "left" }); houseRow(scene, { x0: -24, x1: 24, z: -14, facing: 1 });
- Highway: addHighway(scene); // lanes at z = -5.55, -1.85, 1.85, 5.55
- Props (add to scene): desk(), chair(), laptop(), safe(), cashPile(r, h, n), camBox(loc), sign(text, { key: true }), screen(w, h, lines, draw), counter(label, n).

CHARACTERS & ANIMATION (MUST BE PURE FUNCTIONS OF t):
- const c1 = makeChar({ R: 0.2, shirt: 0x2b5b84, hair: 0x2b1d14, style: "part", glasses: true }); scene.add(c1);
- Inside update(t):
  1. Position camera FIRST: camera.position.set(px, py, pz); camera.up.set(0, 1, 0); camera.lookAt(lx, ly, lz); camera.updateMatrixWorld(true); st.frame();
  2. Pose characters AFTER camera:
     stand(c1, { x: 0, z: 1.5, arms: "down" | "hips" | "wave" | "point" | "phone" | "cross" | "shrug", lean: 0.05, walk: t * 3, face: camera, expr: exprAt([[0, "smug"], [4, "shock"], [8, "grin"]], t) });
     talkAt(expr, words, t); // animates mouth to WORDS!
     sitOn(c1, { x: 0, z: 0, seat: 0.45, arms: "point", lean: 0.1, face: camera, expr });

SHOTS & RUN:
- const S = sentenceStarts(WORDS);
- Every shot MUST have pure `update(t)` and continuous `start` / `end` from 0 to DUR (last shot end: DUR):
  run({
    shots: [
      { start: 0, end: S[1] || 4, stage: st1, update: update1, grade: st1.grade },
      { start: S[1] || 4, end: S[2] || 8, stage: st2, update: update2, grade: st2.grade, in: { type: "dissolve", frames: 8 } },
      ...
      { start: S[S.length - 1] || (DUR - 4), end: DUR, stage: stLast, update: updateLast, grade: stLast.grade }
    ],
    captions: captionsFromWords(WORDS),
    samples: (t) => 1
  });"""

    prompt = f"""Write a complete, valid ES-module `video.js` for 3d-video-studio (9:16 vertical Short).
Topic: "{safe_topic}"
Duration: const DUR = {dur_val};
Narration sentences: {json.dumps(sentences)}

REQUIREMENTS:
1. Build 2 or 3 distinct stages (`st1`, `st2`, `st3`) matching "{safe_topic}" (for example: an indoor `addRoom` office/shop/living room for the scheme/invention, plus an outdoor `addHouse` street or `addHighway` scene—do NOT copy the car crash template!).
2. Create 6 shots (one per sentence using `const S = sentenceStarts(WORDS);`) spanning `start: 0` all the way to `end: DUR` so the camera, characters (`stand`/`sitOn`/`talkAt`/`exprAt`), and props move continuously across the ENTIRE {dur_val} seconds (zero freezing!).
3. Place a `sign(...)` or `addRoom(..., sign: "...")` prop with short 2-3 word text directly about "{safe_topic}".
4. Use ONLY the exact imports and functions listed below. Output ONLY raw valid JavaScript (no markdown fences).

{compact_api}
"""

    candidate_models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
    try:
        m_resp = requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20,
        ).json()
        avail = [m["id"] for m in m_resp.get("data", [])]
        skip = ("whisper", "tts", "guard", "orpheus", "playai", "safeguard", "allam")
        filtered = [m for m in avail if not any(s in m.lower() for s in skip)]
        if filtered:
            candidate_models = [m for m in candidate_models if m in filtered] + [m for m in filtered if m not in candidate_models]
    except Exception:
        pass

    for model in candidate_models[:3]:
        messages = [{"role": "user", "content": prompt}]
        for attempt in range(2):
            try:
                print(f"Generating custom multi-stage 3D scene with {model} (attempt {attempt + 1})...")
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": messages, "temperature": 0.4, "max_tokens": 3500},
                    timeout=90,
                )
                if r.status_code != 200:
                    print(f"Scene HTTP {r.status_code} ({model}): {r.text[:160]}")
                    break
                code = (r.json()["choices"][0]["message"].get("content") or "").strip()
                if "<think>" in code and "</think>" in code:
                    code = code.split("</think>", 1)[1].strip()
                if "```" in code:
                    blocks = _re.findall(r"```(?:javascript|js)?\s*([\s\S]*?)```", code)
                    if blocks:
                        code = blocks[0].strip()
                code = code.replace(", NightMats", "").replace("NightMats, ", "").replace("NightMats", "")
                if "window.samplesAt" not in code:
                    code += "\nwindow.samplesAt = () => 1;\n"
                with open(f"{proj}/video.js", "w", encoding="utf-8") as f:
                    f.write(code)
                chk = subprocess.run(["node", "--check", f"{proj}/video.js"], capture_output=True, text=True)
                if chk.returncode == 0 and "captionsFromWords" in code and "run(" in code:
                    print(f"SUCCESS: Custom multi-stage video.js passed syntax check ({model})!")
                    return
                err_msg = (chk.stderr or "Missing captionsFromWords or run()")[-500:]
                print(f"Syntax check failed ({model} attempt {attempt + 1}): {err_msg}")
                messages = [{"role": "user", "content": f"Fix this JavaScript syntax error and output ONLY valid JS (no markdown):\nERROR: {err_msg}\n\nCODE:\n{code}"}]
            except Exception as e:
                print(f"Scene gen error ({model}): {e}")
                break

    # Rich Multi-Stage Procedural Fallback (3 distinct rooms/streets + 6 animated shots across 0..DUR - NEVER car crash, NEVER freezes!)
    print("Building custom multi-stage 3D scene via procedural director...")
    short_label = " ".join(safe_topic.split()[:3]).upper()
    room_kind = _rnd.choice(["office", "shop", "living"])
    procedural_js = f'''import {{ THREE, V3, clamp, lerp, smooth, ease, DEG, run }} from "engine/core.js";
import {{ makeStage }} from "engine/stage.js";
import {{ addRoom }} from "engine/sets/room.js";
import {{ addHouse }} from "engine/sets/house.js";
import {{ houseRow, bushRow }} from "engine/scenery.js";
import {{ makeChar, exprAt, stand, sitOn, talkAt }} from "engine/chars.js";
import {{ desk, chair, laptop, safe, cashPile, sign }} from "engine/props.js";
import {{ captionsFromWords, sentenceStarts }} from "engine/captions.js";
import WORDS from "./audio/vo.words.json" with {{ type: "json" }};

const DUR = {dur_val};
const S = sentenceStarts(WORDS);
const t1 = S[1] || +(DUR * 0.18).toFixed(2);
const t2 = S[2] || +(DUR * 0.36).toFixed(2);
const t3 = S[3] || +(DUR * 0.54).toFixed(2);
const t4 = S[4] || +(DUR * 0.72).toFixed(2);
const t5 = S[5] || +(DUR * 0.86).toFixed(2);

// Stage 1: Indoor HQ where the schemer plots
const st1 = makeStage({{ mood: "day" }});
addRoom(st1.scene, {{ kind: "{room_kind}", x: 0, z: 0, d: 8, w: 8, h: 3.4, wall: 0xd9d2c5, floor: "wood", view: "trees", sign: "{short_label}" }});
const d1 = desk(); d1.position.set(0, 0, -0.8); st1.scene.add(d1);
const lp = laptop(); lp.position.set(0, 0.76, -0.8); st1.scene.add(lp);
const cp = cashPile(0.35, 0.25, 18); cp.position.set(0.7, 0.76, -0.7); st1.scene.add(cp);
const schemer1 = makeChar({{ R: 0.2, shirt: 0x1f4e78, hair: 0x221810, style: "part", glasses: true }}); st1.scene.add(schemer1);
const victim1 = makeChar({{ R: 0.195, shirt: 0x8c3b2b, hair: 0x4a3219, style: "bowl" }}); st1.scene.add(victim1);

// Stage 2: Outdoor Street / House confrontation
const st2 = makeStage({{ mood: "dusk" }});
addHouse(st2.scene, {{ x: 0, z: -4, depth: 8, storeys: 2, roof: "front", siding: 0xc8b89a, doorColor: 0x6e2c20, garage: "left" }});
houseRow(st2.scene, {{ x0: -24, x1: 24, z: -14, facing: 1 }});
bushRow(st2.scene, {{ area: [-12, 12, 2, 5], count: 10 }});
const banner = sign("{short_label}", {{ key: true }}); banner.position.set(0, 1.6, -1.2); st2.scene.add(banner);
const schemer2 = makeChar({{ R: 0.2, shirt: 0x1f4e78, hair: 0x221810, style: "part", glasses: true }}); st2.scene.add(schemer2);
const hero2 = makeChar({{ R: 0.205, shirt: 0x2e6f40, hair: 0x1b1b1b, style: "spiky" }}); st2.scene.add(hero2);

// Stage 3: Vault / Reveal Room
const st3 = makeStage({{ mood: "day" }});
addRoom(st3.scene, {{ kind: "office", x: 0, z: 0, d: 8, w: 8, h: 3.4, wall: 0xcbd5e1, floor: "tile", view: "skyline", sign: "THE TRUTH" }});
const sf = safe(); sf.position.set(-1.1, 0, -1.4); st3.scene.add(sf);
const hero3 = makeChar({{ R: 0.205, shirt: 0x2e6f40, hair: 0x1b1b1b, style: "spiky" }}); st3.scene.add(hero3);
const schemer3 = makeChar({{ R: 0.2, shirt: 0x1f4e78, hair: 0x221810, style: "part", glasses: true }}); st3.scene.add(schemer3);

function camMove(st, p0, p1, l0, l1, u) {{
  st.camera.position.set(lerp(p0[0], p1[0], u), lerp(p0[1], p1[1], u), lerp(p0[2], p1[2], u));
  st.camera.up.set(0, 1, 0);
  st.camera.lookAt(lerp(l0[0], l1[0], u), lerp(l0[1], l1[1], u), lerp(l0[2], l1[2], u));
  st.camera.updateMatrixWorld(true);
  st.frame();
}}

function up1(t) {{
  const u = clamp(t / Math.max(0.1, t1), 0, 1);
  camMove(st1, [-1.4, 1.55, 2.6], [0.6, 1.45, 2.0], [0, 1.25, -0.6], [0, 1.25, -0.6], smooth(u));
  const ex = talkAt(exprAt([[0, "smug"], [t1 * 0.5, "grin"]], t), WORDS, t);
  sitOn(schemer1, {{ x: 0, z: -1.35, seat: 0.45, arms: "point", lean: 0.08, face: st1.camera, expr: ex }});
  stand(victim1, {{ x: 1.15, z: 0.4, arms: "shrug", face: schemer1, expr: exprAt([[0, "innocent"], [t1 * 0.6, "worried"]], t) }});
}}

function up2(t) {{
  const u = clamp((t - t1) / Math.max(0.1, t2 - t1), 0, 1);
  camMove(st1, [0.9, 1.4, 1.7], [-0.4, 1.35, 1.45], [0, 1.25, -1.0], [0.2, 1.2, -0.8], smooth(u));
  const ex = talkAt(exprAt([[t1, "grin"], [(t1 + t2) * 0.5, "smug"]], t), WORDS, t);
  sitOn(schemer1, {{ x: 0, z: -1.35, seat: 0.45, arms: "wave", lean: 0.12, face: st1.camera, expr: ex }});
  stand(victim1, {{ x: 1.0, z: 0.3, arms: "hips", face: schemer1, expr: exprAt([[t1, "shock"]], t) }});
}}

function up3(t) {{
  const u = clamp((t - t2) / Math.max(0.1, t3 - t2), 0, 1);
  camMove(st2, [-2.2, 1.6, 3.8], [1.8, 1.5, 3.2], [0, 1.3, 0.5], [0, 1.3, 0.5], smooth(u));
  const ex = talkAt(exprAt([[t2, "smug"], [(t2 + t3) * 0.6, "jolt"]], t), WORDS, t);
  stand(schemer2, {{ x: -0.7 + u * 0.4, z: 0.8, arms: "point", walk: t * 3.5, face: st2.camera, expr: ex }});
  stand(hero2, {{ x: 0.85, z: 0.9, arms: "cross", face: schemer2, expr: exprAt([[t2, "stern"], [(t2 + t3) * 0.5, "grin"]], t) }});
}}

function up4(t) {{
  const u = clamp((t - t3) / Math.max(0.1, t4 - t3), 0, 1);
  camMove(st2, [1.2, 1.45, 2.4], [0.3, 1.38, 1.75], [0.6, 1.3, 0.8], [0.75, 1.32, 0.85], smooth(u));
  const ex = talkAt(exprAt([[t3, "grin"], [(t3 + t4) * 0.5, "smug"]], t), WORDS, t);
  stand(hero2, {{ x: 0.75, z: 0.85, arms: "point", lean: 0.06, face: st2.camera, expr: ex }});
  stand(schemer2, {{ x: -0.45, z: 0.8, arms: "shrug", face: hero2, expr: exprAt([[t3, "shock"], [(t3 + t4) * 0.5, "dazed"]], t) }});
}}

function up5(t) {{
  const u = clamp((t - t4) / Math.max(0.1, t5 - t4), 0, 1);
  camMove(st3, [-1.6, 1.55, 2.8], [1.4, 1.5, 2.5], [0, 1.25, 0], [0, 1.25, 0], smooth(u));
  const ex = talkAt(exprAt([[t4, "shock"], [(t4 + t5) * 0.5, "pain"]], t), WORDS, t);
  stand(schemer3, {{ x: -0.5, z: 0.2, arms: "hips", face: st3.camera, expr: ex }});
  stand(hero3, {{ x: 0.7, z: 0.3, arms: "wave", face: st3.camera, expr: exprAt([[t4, "grin"]], t) }});
}}

function up6(t) {{
  const u = clamp((t - t5) / Math.max(0.1, DUR - t5), 0, 1);
  camMove(st3, [1.1, 1.42, 2.2], [0.2, 1.36, 1.55], [0.4, 1.3, 0.2], [0.55, 1.32, 0.25], smooth(u));
  const ex = talkAt(exprAt([[t5, "grin"], [(t5 + DUR) * 0.5, "smug"]], t), WORDS, t);
  stand(hero3, {{ x: 0.6, z: 0.25, arms: "point", lean: 0.08, face: st3.camera, expr: ex }});
  stand(schemer3, {{ x: -0.6, z: 0.2, arms: "shrug", face: hero3, expr: exprAt([[t5, "dazed"]], t) }});
}}

run({{
  shots: [
    {{ start: 0, end: t1, stage: st1, update: up1, grade: st1.grade }},
    {{ start: t1, end: t2, stage: st1, update: up2, grade: st1.grade, in: {{ type: "dissolve", frames: 6 }} }},
    {{ start: t2, end: t3, stage: st2, update: up3, grade: st2.grade, in: {{ type: "dissolve", frames: 8 }} }},
    {{ start: t3, end: t4, stage: st2, update: up4, grade: st2.grade, in: {{ type: "dissolve", frames: 6 }} }},
    {{ start: t4, end: t5, stage: st3, update: up5, grade: st3.grade, in: {{ type: "dissolve", frames: 8 }} }},
    {{ start: t5, end: DUR, stage: st3, update: up6, grade: st3.grade, in: {{ type: "dissolve", frames: 6 }} }}
  ],
  captions: captionsFromWords(WORDS),
  samples: (t) => 1
}});
window.samplesAt = () => 1;
'''
    with open(f"{proj}/video.js", "w", encoding="utf-8") as f:
        f.write(procedural_js)
    chk = subprocess.run(["node", "--check", f"{proj}/video.js"], capture_output=True, text=True)
    if chk.returncode != 0:
        raise RuntimeError(f"Procedural video.js syntax error: {chk.stderr}")
    print(f"Built 3-stage 6-shot full-duration ({dur_val}s) 3D scene in {room_kind} + street + vault!")

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
    subprocess.run(["node", "3d-video-studio/engine/film.mjs", "cues", proj], check=False)
    mix_res = subprocess.run(["python3", "3d-video-studio/engine/audio/mix.py", proj], capture_output=True, text=True)
    final_audio = f"{proj}/audio/mix.wav" if (mix_res.returncode == 0 and os.path.exists(f"{proj}/audio/mix.wav")) else f"{proj}/audio/vo.wav"
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
