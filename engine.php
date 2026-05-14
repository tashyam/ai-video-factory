// --- 1. STORY ---
$text = "He found a black coin. It felt warm. He flipped it. Heads he gained a million. Tails he lost a year."; 
// (Keep your full text, just showing the split logic below)

echo "Generating High-Quality Audio... ";
$words = explode(" ", $text);
$chunks = array_chunk($words, 15); // Split text into small bits
$combined_audio = "";

foreach($chunks as $index => $chunk) {
    $sentence = implode(" ", $chunk);
    $audio_url = "https://translate.google.com/translate_tts?ie=UTF-8&q=" . urlencode($sentence) . "&tl=en&client=tw-ob";
    
    $ch = curl_init($audio_url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0');
    $data = curl_exec($ch);
    curl_close($ch);
    
    if($data) {
        $combined_audio .= $data;
        echo "."; 
    }
    sleep(1); // Small pause to be polite to the server
}

file_put_contents("audio.mp3", $combined_audio);
echo " ✅ Done.\n";
