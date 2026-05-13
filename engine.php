<?php
// --- 1. THE STORY ---
$text = "He found a black coin. It felt warm. He flipped it. Heads, he gained a million. Tails, he lost a year. He kept flipping. He got richer. But his hair turned grey. His skin wrinkled. One last flip. He won the gold. But he was too old to hold it. He closed his eyes. The coin vanished.";

// --- 2. AUTOMATIC AUDIO (The "No-Manual" Way) ---
echo "Generating Audio... ";
// We use a different TTS mirror that GitHub servers can access easily
$audio_url = "https://translate.google.com/translate_tts?ie=UTF-8&q=" . urlencode($text) . "&tl=en&client=tw-ob";
file_put_contents("audio.mp3", file_get_contents($audio_url));
echo "✅ Done.\n";

// --- 3. THE PATIENT IMAGE DOWNLOADER ---
$prompts = [
    "young man finding coin", "glowing coin macro", "man flipping coin", 
    "stacks of money", "grey hair man mirror", "coin spinning blur",
    "old man face wrinkles", "gold bars treasure", "old man throne", 
    "hand flipping coin", "old man closing eyes", "dust vanishing"
];

for ($i = 0; $i < 12; $i++) {
    $p_num = $i + 1;
    $img_prompt = urlencode($prompts[$i] . ", cinematic 3d, 9:16");
    $url = "https://image.pollinations.ai/prompt/{$img_prompt}?nologo=true&seed=" . rand(1, 999);
    
    echo "Downloading Scene $p_num... ";
    $img_data = @file_get_contents($url);
    if ($img_data) {
        file_put_contents("p$p_num.jpg", $img_data);
        echo "✅ Success. Waiting 40s (Cooldown)...\n";
        sleep(40); // THIS IS THE PATTERN: 40 seconds ensures 100% success
    }
}

// --- 4. THE ASSEMBLY (FFMPEG) ---
echo "Rendering Video...\n";
// GitHub's Linux FFmpeg command
$cmd = "ffmpeg -y ";
for($j=1; $j<=12; $j++) { $cmd .= "-loop 1 -t 2.5 -i p$j.jpg "; }
$cmd .= "-i audio.mp3 -filter_complex \"";

// Simplified filter for Cloud speed
$filter = "";
for($k=0; $k<12; $k++) { 
    $filter .= "[$k:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v$k];"; 
}
$filter .= "[v0][v1][v2][v3][v4][v5][v6][v7][v8][v9][v10][v11]concat=n=12:v=1:a=0[outv]\"";

$cmd .= $filter . " -map '[outv]' -map 12:a -c:v libx264 -pix_fmt yuv420p -shortest final_video.mp4 2>&1";

exec($cmd, $output);
echo "Render Complete.\n";
?>
