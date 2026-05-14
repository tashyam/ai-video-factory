<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);

echo "--- 🤖 STARTING SUPREME INDIAN STORY ENGINE ---\n";

// 1. AI STORY GENERATION
echo "AI is writing a new story... ";
$topic = ["cursed antique", "glitch in reality", "mysterious forest", "abandoned hospital", "dark sea secret", "haunted haveli", "urban legend"][rand(0,6)];
$sys = "Write a creepy 12-sentence story about a $topic. No intro, no titles. Just the story. Each sentence is a scene.";
$text = @file_get_contents("https://text.pollinations.ai/" . urlencode($sys));

if (!$text || strlen($text) < 100) {
    $text = "He found a black coin. It felt warm. He flipped it. Heads he gained a million. Tails he lost a year. He kept flipping. He got richer. But his hair turned grey. His skin wrinkled. One last flip. He won the gold. But he was too old to hold it. He closed his eyes. The coin vanished.";
    echo "⚠️ Using backup story.\n";
} else {
    echo "✅ Story Created.\n";
}

// 2. HIGH-QUALITY INDIAN ENGLISH AUDIO
echo "Generating Indian English Audio... ";
$sentences = explode(".", $text);
$sentences = array_filter(array_map('trim', $sentences));
$audio_data = "";

foreach($sentences as $s) {
    if(empty($s)) continue;
    // Using 'en-IN' for Indian English accent
    $url = "https://translate.google.com/translate_tts?ie=UTF-8&q=" . urlencode($s) . "&tl=en-IN&client=tw-ob";
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0');
    $audio_data .= curl_exec($ch);
    curl_close($ch);
    usleep(200000); 
}
file_put_contents("audio.mp3", $audio_data);
echo "✅ Audio Ready.\n";

// 3. DYNAMIC IMAGE DOWNLOADER
$prompts = array_values($sentences);
$total_scenes = count($prompts);
for ($i = 1; $i <= $total_scenes; $i++) {
    $file = "p$i.jpg";
    $p_text = trim($prompts[$i-1]);
    $url = "https://image.pollinations.ai/prompt/" . urlencode($p_text . ", cinematic 3d, horror, 9:16") . "?nologo=true&seed=" . rand(1, 9999);
    
    echo "Scene $i: ";
    $data = @file_get_contents($url);
    if ($data && strlen($data) > 10000) {
        file_put_contents($file, $data);
        echo "✅ (Wait 30s)\n";
        sleep(30);
    } else {
        echo "⚠️ Copying backup.\n";
        if($i > 1) copy("p1.jpg", $file);
    }
}

// 4. THE ASSEMBLY (DYNAMIC LENGTH)
echo "🎬 Building Masterpiece...\n";
// Get the actual duration of the audio file
$audio_duration = shell_exec("ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 audio.mp3");
$scene_duration = (float)$audio_duration / $total_scenes;

$inputs = "";
for($j=1; $j<=$total_scenes; $j++) { $inputs .= "-loop 1 -t $scene_duration -i p$j.jpg "; }

$filter = "-filter_complex \"";
for($k=0; $k<$total_scenes; $k++) { 
    $filter .= "[$k:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v$k];"; 
}
$concat_parts = "";
for($l=0; $l<$total_scenes; $l++) { $concat_parts .= "[v$l]"; }
$filter .= $concat_parts . "concat=n=$total_scenes:v=1:a=0[v]\"";

$final_cmd = "ffmpeg -y $inputs -i audio.mp3 $filter -map '[v]' -map $total_scenes:a -c:v libx264 -preset ultrafast -pix_fmt yuv420p final_video.mp4 2>&1";

passthru($final_cmd);

if(file_exists("final_video.mp4")) {
    echo "\n🏆 SUCCESS! Your Indian AI Story is ready.";
} else {
    echo "\n❌ CRITICAL ERROR: FFmpeg did not create the file.";
}
?>
