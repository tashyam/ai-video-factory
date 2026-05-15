// --- 4. THE ASSEMBLY (FORCED AUDIO SYNC) ---
echo "🎬 Building Full Length Masterpiece...\n";

// We remove the '-shortest' flag and use '-af apad' to ensure audio doesn't cut
// We use '-shortest' ONLY if we want to cut the video to the audio, 
// but we must loop the images correctly first.

$inputs = "";
for($j=1; $j<=12; $j++) { 
    // We tell each image to loop for the required time
    $inputs .= "-loop 1 -t $scene_duration -i p$j.jpg "; 
}

$filter = "-filter_complex \"";
for($k=0; $k<12; $k++) { 
    $filter .= "[$k:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v$k];"; 
}
$filter .= "[v0][v1][v2][v3][v4][v5][v6][v7][v8][v9][v10][v11]concat=n=12:v=1:a=0, $drawtext [outv]\"";

// NEW COMMAND: No -shortest at the end of the global flags
// We use -fflags +shortest and -max_interleave_delta to force a clean cut at the END of the audio.
$final_cmd = "ffmpeg -y $inputs -i audio.mp3 $filter -map '[outv]' -map 12:a -c:v libx264 -preset ultrafast -pix_fmt yuv420p -fflags +shortest -max_interleave_delta 100M final_video.mp4 2>&1";

passthru($final_cmd);
