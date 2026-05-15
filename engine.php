<?php
echo "--- 🚀 STARTING SUPREME ENGINE V3 ---\n";

// 1. STORY (Auto-Thinking)
$sys = "Write a shocking 12-sentence story with a twist. Sentence 1 is a viral hook. Each sentence is a scene.";
$text = @file_get_contents("https://text.pollinations.ai/" . urlencode($sys));
if(!$text) $text = "He found a black coin. It felt warm. He flipped it. Heads he gained a million. Tails he lost a year. He kept flipping. He got richer. But his hair turned grey. His skin wrinkled. One last flip. He won the gold. But he was too old to hold it. He closed his eyes. The coin vanished.";

// 2. AUDIO (Indian English)
$sentences = array_filter(array_map('trim', explode(".", $text)));
$audio_data = "";
foreach($sentences as $s) {
    $url = "https://translate.google.com/translate_tts?ie=UTF-8&q=" . urlencode($s) . "&tl=en-IN&client=tw-ob";
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0');
    $audio_data .= curl_exec($ch);
    curl_close($ch);
    usleep(300000); 
}
file_put_contents("audio.mp3", $audio_data);

// 3. IMAGES (12 Unique)
for ($i = 1; $i <= 12; $i++) {
    $file = "p$i.jpg";
    $url = "https://image.pollinations.ai/prompt/" . urlencode($sentences[$i-1] ?? "mystery") . "?nologo=true&seed=" . rand(1,9999);
    $data = @file_get_contents($url);
    if($data) file_put_contents($file, $data); else copy("p1.jpg", $file);
    sleep(35);
}

// 4. ASSEMBLY (The Absolute Fix)
$audio_dur = (float)shell_exec("ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 audio.mp3");
$scene_dur = $audio_dur / 12;
$inputs = ""; $drawtext = "";
for($j=1; $j<=12; $j++) { 
    $inputs .= "-loop 1 -t $scene_dur -i p$j.jpg "; 
    $st = ($j-1)*$scene_dur; $en = $j*$scene_dur; $txt = addslashes(strtoupper($sentences[$j-1] ?? ""));
    $drawtext .= "drawtext=fontfile='myfont.ttf':text='$txt':fontcolor=yellow:fontsize=40:borderw=4:bordercolor=black:x=(w-text_w)/2:y=h-250:enable='between(t,$st,$en)',";
}
$drawtext = rtrim($drawtext, ",");

// WE FORCE THE PATH TO /home/runner/work/ai-video-factory/ai-video-factory/final_video.mp4
$cmd = "ffmpeg -y $inputs -i audio.mp3 -filter_complex \"";
for($k=0; $k<12; $k++) { $cmd .= "[$k:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v$k];"; }
$cmd .= "[v0][v1][v2][v3][v4][v5][v6][v7][v8][v9][v10][v11]concat=n=12:v=1:a=0, $drawtext [outv]\" ";
$cmd .= "-map '[outv]' -map 12:a -c:v libx264 -preset ultrafast -pix_fmt yuv420p final_video.mp4 2>&1";

echo "Rendering... \n";
exec($cmd);

// WAIT FOR DISK TO SYNC
sleep(5);

if(file_exists("final_video.mp4")) {
    echo "✅ VIDEO FOUND! Size: " . filesize("final_video.mp4") . " bytes\n";
} else {
    echo "❌ ERROR: final_video.mp4 was NOT created.\n";
}
?>
