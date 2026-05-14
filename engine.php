<?php
echo "--- 🤖 STARTING FULLY AUTONOMOUS ENGINE ---\n";

// --- 1. AI STORY GENERATION (The "Magic" Part) ---
echo "AI is writing a new story... ";
// We use a free text-generation API (Pollinations Text)
$system_prompt = "Write a creepy, high-retention 12-sentence story for a YouTube Short. No intro, just the story. Each sentence should be a new scene.";
$api_url = "https://text.pollinations.ai/" . urlencode($system_prompt);

$generated_text = @file_get_contents($api_url);

if ($generated_text && strlen($generated_text) > 100) {
    $text = $generated_text;
    echo "✅ Story Created.\n";
} else {
    // Fallback if the AI is busy
    $text = "He found a black coin. It felt warm. He flipped it. Heads he gained a million. Tails he lost a year. He kept flipping. He got richer. But his hair turned grey. His skin wrinkled. One last flip. He won the gold. But he was too old to hold it. He closed his eyes. The coin vanished.";
    echo "⚠️ Using fallback story.\n";
}

// --- 2. HIGH-QUALITY AUDIO CHUNKING ---
echo "Generating Audio... ";
$sentences = explode(".", $text);
$combined_audio = "";

foreach($sentences as $sentence) {
    if(trim($sentence) == "") continue;
    $audio_url = "https://translate.google.com/translate_tts?ie=UTF-8&q=" . urlencode(trim($sentence)) . "&tl=en&client=tw-ob";
    
    $ch = curl_init($audio_url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0');
    $combined_audio .= curl_exec($ch);
    curl_close($ch);
    usleep(300000); 
}
file_put_contents("audio.mp3", $combined_audio);
echo "✅ Done.\n";

// --- 3. IMAGE DOWNLOADER (Using the AI's own words) ---
for ($i = 1; $i <= 12; $i++) {
    $file = "p$i.jpg";
    $scene_prompt = isset($sentences[$i-1]) ? trim($sentences[$i-1]) : "creepy cinematic atmosphere";
    $url = "https://image.pollinations.ai/prompt/" . urlencode($scene_prompt . ", cinematic 3d, horror style, 9:16") . "?nologo=true&seed=" . rand(1, 9999);
    
    echo "Downloading Scene $i... ";
    $data = @file_get_contents($url);
    if ($data) {
        file_put_contents($file, $data);
        echo "✅. Waiting 35s...\n";
        sleep(35);
    } else {
        echo "⚠️ Copying p1.\n";
        copy("p1.jpg", $file);
    }
}

// --- 4. THE ASSEMBLY ---
echo "Final Rendering...\n";
$inputs = "";
for($j=1; $j<=12; $j++) { $inputs .= "-loop 1 -t 2.5 -i p$j.jpg "; }
$filter = "-filter_complex \"";
for($k=0; $k<12; $k++) { 
    $filter .= "[$k:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v$k];"; 
}
$filter .= "[v0][v1][v2][v3][v4][v5][v6][v7][v8][v9][v10][v11]concat=n=12:v=1:a=0[v]\"";
$cmd = "ffmpeg -y $inputs -i audio.mp3 $filter -map '[v]' -map 12:a -c:v libx264 -preset ultrafast -pix_fmt yuv420p -shortest final_video.mp4 2>&1";
passthru($cmd);
?>
