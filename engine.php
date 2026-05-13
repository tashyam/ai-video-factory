<?php
echo "--- 🚀 STARTING PERMANENT AUTOMATION ENGINE ---\n";

// 1. STORY & AUDIO (STABLE METHOD)
$text = "He found a black coin. It felt warm. He flipped it. Heads he gained a million. Tails he lost a year. He kept flipping. He got richer. But his hair turned grey. His skin wrinkled. One last flip. He won the gold. But he was too old to hold it. He closed his eyes. The coin vanished.";
file_put_contents("story.txt", $text);

echo "Generating Stable Audio... ";
// We use 'espeak' which is a local Linux tool - No internet/blocking possible
exec("espeak -f story.txt -w audio.wav && ffmpeg -i audio.wav -codec:a libmp3lame -qscale:a 2 audio.mp3 2>&1", $audio_log);

if(file_exists("audio.mp3") && filesize("audio.mp3") > 5000) {
    echo "✅ Success.\n";
} else {
    echo "⚠️ Audio failed. Creating emergency silence.\n";
    exec("ffmpeg -f lavfi -i anullsrc=r=44100:cl=mono -t 30 audio.mp3");
}

// 2. IMAGE DOWNLOADER (WITH SMART BACKUP)
$prompts = ["young man finding coin", "glowing coin macro", "man flipping coin", "stacks of money", "grey hair man mirror", "coin spinning blur", "old man face wrinkles", "gold bars treasure", "old man throne", "hand flipping coin", "old man closing eyes", "dust vanishing"];

for ($i = 1; $i <= 12; $i++) {
    $file = "p$i.jpg";
    $img_prompt = urlencode($prompts[$i-1] . ", 3d render, high quality, 9:16");
    $url = "https://image.pollinations.ai/prompt/{$img_prompt}?nologo=true&seed=" . rand(1, 9999);
    
    echo "Scene $i: ";
    $data = @file_get_contents($url);
    if ($data && strlen($data) > 10000) {
        file_put_contents($file, $data);
        echo "✅ Downloaded. Waiting 30s...\n";
        sleep(30);
    } else {
        echo "⚠️ Server Busy. Using placeholder.\n";
        // If p1 exists, copy it. If not, we download a basic black background so FFmpeg won't fail.
        if (file_exists("p1.jpg")) {
            copy("p1.jpg", $file);
        } else {
            file_put_contents($file, file_get_contents("https://image.pollinations.ai/prompt/black_background?nologo=true"));
        }
    }
}

// 3. MASTER RENDER (THE ASSEMBLY)
echo "🎬 Building Masterpiece...\n";
$inputs = "";
for($j=1; $j<=12; $j++) { $inputs .= "-loop 1 -t 2.5 -i p$j.jpg "; }

$filter = "-filter_complex \"";
for($k=0; $k<12; $k++) { 
    $filter .= "[$k:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v$k];"; 
}
$filter .= "[v0][v1][v2][v3][v4][v5][v6][v7][v8][v9][v10][v11]concat=n=12:v=1:a=0[v]\"";

$cmd = "ffmpeg -y $inputs -i audio.mp3 $filter -map '[v]' -map 12:a -c:v libx264 -preset ultrafast -pix_fmt yuv420p -shortest final_video.mp4 2>&1";

echo "Rendering... ";
passthru($cmd);

if(file_exists("final_video.mp4")) {
    echo "\n🏆 ALL DONE! DOWNLOAD YOUR VIDEO BELOW.\n";
} else {
    echo "\n❌ Render Failed. Check logs above.\n";
}
?>
