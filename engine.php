<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);

echo "--- 🤖 STARTING SUPREME INDIAN STORY ENGINE V2 ---\n";

// 1. AI STORY GENERATION WITH ENGAGING HOOK
echo "AI is writing an engaging story... ";
$topic = ["cursed antique", "glitch in reality", "mysterious forest", "abandoned hospital", "dark sea secret", "haunted haveli", "urban legend"][rand(0,6)];
// We explicitly ask for a HOOK in the first sentence
$sys = "Write a creepy 12-sentence story about a $topic. Sentence 1 MUST be a shocking hook that makes people stop scrolling. Each sentence is a separate scene. Use simple, clear English.";
$text = @file_get_contents("https://text.pollinations.ai/" . urlencode($sys));

if (!$text || strlen($text) < 100) {
    $text = "You won't believe what they found at the bottom of the sea. It was a golden door that shouldn't exist. He touched the handle. It was warm. The door opened slowly. A cold hand reached out. He was pulled inside. The door slammed shut. No one heard his screams. Only the waves remained. The sea keeps its secrets. Don't go near the water.";
    echo "⚠️ Using backup story.\n";
} else {
    echo "✅ Story Created.\n";
}

// 2. CLEAR INDIAN ENGLISH AUDIO (Stabilized)
echo "Generating Clear Audio... ";
$sentences = explode(".", $text);
$sentences = array_filter(array_map('trim', $sentences));
$audio_data = "";

foreach($sentences as $s) {
    if(empty($s)) continue;
    // Added 'ie=UTF-8' and a cleaner client string to reduce noise
    $url = "https://translate.google.com/translate_tts?ie=UTF-8&q=" . urlencode($s) . "&tl=en-IN&client=tw-ob";
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    $audio_data .= curl_exec($ch);
    curl_close($ch);
    usleep(500000); // Wait 0.5s between chunks to ensure clarity
}
file_put_contents("audio.mp3", $audio_data);
echo "✅ Audio Ready.\n";

// 3. MULTI-SEED IMAGE DOWNLOADER (To bypass "Busy" blocks)
$prompts = array_values($sentences);
$total_scenes = count($prompts);
for ($i = 1; $i <= $total_scenes; $i++) {
    $file = "p$i.jpg";
    $p_text = trim($prompts[$i-1]);
    // Added random 'seed' and 'nologo' to make every request look unique to the server
    $url = "https://image.pollinations.ai/prompt/" . urlencode($p_text . ", cinematic 3d render, horror lighting, 9:16") . "?nologo=true&seed=" . rand(1, 99999);
    
    echo "Scene $i: ";
    $ctx = stream_context_create(['http' => ['timeout' => 20]]);
    $data = @file_get_contents($url, false, $ctx);
    
    if ($data && strlen($data) > 20000) {
        file_put_contents($file, $data);
        echo "✅ Downloaded. Waiting 45s (Cooldown)...\n";
        sleep(45); // Longer sleep to ensure the server doesn't flag the GitHub IP
    } else {
        echo "⚠️ Busy. Using variant...\n";
        if($i > 1) copy("p1.jpg", $file);
    }
}

// 4. THE ASSEMBLY (WITH CAPTIONS & DYNAMIC LENGTH)
echo "🎬 Building Masterpiece with Captions...\n";
$audio_duration = shell_exec("ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 audio.mp3");
$scene_duration = (float)$audio_duration / $total_scenes;

$inputs = "";
$drawtext = "";
for($j=1; $j<=$total_scenes; $j++) { 
    $inputs .= "-loop 1 -t $scene_duration -i p$j.jpg "; 
    
    // CAPTION LOGIC: Calculates timing for each sentence
    $start = ($j-1) * $scene_duration;
    $end = $j * $scene_duration;
    $msg = addslashes(strtoupper($prompts[$j-1] ?? ""));
    // Uses the font you uploaded to GitHub
    $drawtext .= "drawtext=fontfile='myfont.ttf':text='$msg':fontcolor=yellow:fontsize=45:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h*0.75:enable='between(t,$start,$end)',";
}
$drawtext = rtrim($drawtext, ",");

$filter = "-filter_complex \"";
for($k=0; $k<$total_scenes; $k++) { 
    $filter .= "[$k:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v$k];"; 
}
$concat_parts = "";
for($l=0; $l<$total_scenes; $l++) { $concat_parts .= "[v$l]"; }
$filter .= $concat_parts . "concat=n=$total_scenes:v=1:a=0, $drawtext [outv]\"";

$final_cmd = "ffmpeg -y $inputs -i audio.mp3 $filter -map '[outv]' -map $total_scenes:a -c:v libx264 -preset ultrafast -pix_fmt yuv420p final_video.mp4 2>&1";

passthru($final_cmd);
echo "\n🏆 SUCCESS! Check Artifacts for your viral video.";
?>
