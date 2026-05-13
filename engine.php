<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);

echo "--- STARTING CLOUD GENERATION ---\n";

// 1. AUDIO GENERATION
$text = "He found a black coin. It felt warm. He flipped it. Heads he gained a million. Tails he lost a year. He kept flipping. He got richer. But his hair turned grey. His skin wrinkled. One last flip. He won the gold. But he was too old to hold it. He closed his eyes. The coin vanished.";
$audio_url = "https://translate.google.com/translate_tts?ie=UTF-8&q=" . urlencode($text) . "&tl=en&client=tw-ob";

echo "Generating Audio... ";
$ch = curl_init($audio_url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0');
$audio_data = curl_exec($ch);
curl_close($ch);

if($audio_data) {
    file_put_contents("audio.mp3", $audio_data);
    echo "✅\n";
} else {
    die("❌ Audio Generation Failed. Stopping to save credits.");
}

// 2. IMAGE DOWNLOADER
$prompts = ["young man finding coin", "glowing coin macro", "man flipping coin", "stacks of money", "grey hair man mirror", "coin spinning blur", "old man face wrinkles", "gold bars treasure", "old man throne", "hand flipping coin", "old man closing eyes", "dust vanishing"];

for ($i = 1; $i <= 12; $i++) {
    $file = "p$i.jpg";
    if (file_exists($file) && filesize($file) > 10000) {
        echo "Scene $i: ✅ Existing.\n";
        continue;
    }
    $url = "https://image.pollinations.ai/prompt/" . urlencode($prompts[$i-1] . ", 3d render, 9:16") . "?nologo=true&seed=" . rand(1, 999);
    echo "Downloading Scene $i... ";
    $data = @file_get_contents($url);
    if ($data) {
        file_put_contents($file, $data);
        echo "✅. Waiting 30s...\n";
        sleep(30);
    } else {
        echo "⚠️ Busy. Copying p1.\n";
        copy("p1.jpg", $file);
    }
}

// 3. FFMPEG RENDER
echo "Starting Final Render...\n";
$inputs = "";
for($j=1; $j<=12; $j++) { $inputs .= "-loop 1 -t 2.5 -i p$j.jpg "; }

$filter = "-filter_complex \"";
for($k=0; $k<12; $k++) { 
    $filter .= "[$k:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v$k];"; 
}
$filter .= "[v0][v1][v2][v3][v4][v5][v6][v7][v8][v9][v10][v11]concat=n=12:v=1:a=0[v]\"";

// THE FIX: We use a more direct shell command for GitHub Linux
$full_cmd = "ffmpeg -y $inputs -i audio.mp3 $filter -map '[v]' -map 12:a -c:v libx264 -preset ultrafast -pix_fmt yuv420p -shortest final_video.mp4 2>&1";

echo "Running Command...\n";
passthru($full_cmd); // This will stream the FFmpeg progress directly to the GitHub log

if(file_exists("final_video.mp4")) {
    echo "\n🚀 SUCCESS! Video file created.\n";
} else {
    echo "\n❌ ERROR: Video file was not created.\n";
}
?>
