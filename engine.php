<?php
// --- 1. THE STORY ---
$text = "He found a black coin. It felt warm. He flipped it. Heads he gained a million. Tails he lost a year. He kept flipping. He got richer. But his hair turned grey. His skin wrinkled. One last flip. He won the gold. But he was too old to hold it. He closed his eyes. The coin vanished.";

echo "--- STARTING CLOUD GENERATION ---\n";

// --- 2. AUTOMATIC AUDIO (Fixed URL) ---
echo "Generating Audio... ";
// We use a simpler URL to avoid the 400 Bad Request error
$audio_url = "https://translate.google.com/translate_tts?ie=UTF-8&q=" . urlencode($text) . "&tl=en&client=tw-ob";

$ch = curl_init($audio_url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0');
$audio_data = curl_exec($ch);
curl_close($ch);

if($audio_data && strlen($audio_data) > 1000) {
    file_put_contents("audio.mp3", $audio_data);
    echo "✅ Done.\n";
} else {
    echo "❌ Audio Failed. Creating silent backup.\n";
    // Create 30s silent audio so FFmpeg doesn't crash
    exec("ffmpeg -f lavfi -i anullsrc=r=44100:cl=mono -t 30 -q:a 9 -acodec libmp3lame audio.mp3");
}

// --- 3. THE PATIENT IMAGE DOWNLOADER ---
$prompts = [
    "young man finding coin", "glowing coin macro", "man flipping coin", 
    "stacks of money", "grey hair man mirror", "coin spinning blur",
    "old man face wrinkles", "gold bars treasure", "old man throne", 
    "hand flipping coin", "old man closing eyes", "dust vanishing"
];

for ($i = 1; $i <= 12; $i++) {
    $filename = "p$i.jpg";
    if (file_exists($filename) && filesize($filename) > 10000) {
        echo "Scene $i: ✅ Already exists.\n";
        continue;
    }

    $img_prompt = urlencode($prompts[$i-1] . ", cinematic 3d, 9:16");
    $url = "https://image.pollinations.ai/prompt/{$img_prompt}?nologo=true&seed=" . rand(1, 999);
    
    echo "Downloading Scene $i... ";
    $img_data = @file_get_contents($url);
    if ($img_data && strlen($img_data) > 10000) {
        file_put_contents($filename, $img_data);
        echo "✅ Success. Waiting 40s...\n";
        sleep(40);
    } else {
        echo "⚠️ Busy. Using placeholder.\n";
        if($i > 1) copy("p1.jpg", $filename);
    }
}

// --- 4. THE ASSEMBLY (FFMPEG) ---
echo "Starting Final Render...\n";

$in = "";
for($j=1; $j<=12; $j++) { $in .= "-loop 1 -t 2.5 -i p$j.jpg "; }

$filter = "-filter_complex \"";
for($k=0; $k<12; $k++) { 
    $filter .= "[$k:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v$k];"; 
}
$filter .= "[v0][v1][v2][v3][v4][v5][v6][v7][v8][v9][v10][v11]concat=n=12:v=1:a=0[outv]\"";

// Added specific flags to ensure it works on Linux/GitHub
$cmd = "ffmpeg -y $in -i audio.mp3 $filter -map '[outv]' -map 12:a -c:v libx264 -preset ultrafast -pix_fmt yuv420p -shortest final_video.mp4 2>&1";

exec($cmd, $output_log, $return_var);

echo implode("\n", $output_log);
echo "\nRender Process Finished with code: $return_var\n";
?>
