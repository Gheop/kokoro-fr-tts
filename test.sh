#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:7860}"
ENDPOINT="$BASE_URL/v1/audio/speech"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

pass=0
fail=0

ok()   { pass=$((pass + 1)); printf "  \033[32mOK\033[0m   %s\n" "$1"; }
ko()   { fail=$((fail + 1)); printf "  \033[31mFAIL\033[0m %s\n" "$1"; }
section() { printf "\n\033[1m--- %s ---\033[0m\n" "$1"; }

post() {
    # $1 = JSON body (small) or @file (large), $2 = output file
    local body="$1" out="$2"
    curl -s -w "%{http_code}" -X POST "$ENDPOINT" \
        -H "Content-Type: application/json" \
        -d "$body" \
        --output "$out"
}

post_file() {
    # $1 = path to JSON file, $2 = output file
    local file="$1" out="$2"
    curl -s -w "%{http_code}" -X POST "$ENDPOINT" \
        -H "Content-Type: application/json" \
        -d @"$file" \
        --output "$out"
}

expect_status() {
    local desc="$1" json="$2" expected="$3"
    local code
    code=$(post "$json" /dev/null)
    if [ "$code" = "$expected" ]; then
        ok "$desc -> $expected"
    else
        ko "$desc -> got $code, expected $expected"
    fi
}

expect_status_file() {
    local desc="$1" file="$2" expected="$3"
    local code
    code=$(post_file "$file" /dev/null)
    if [ "$code" = "$expected" ]; then
        ok "$desc -> $expected"
    else
        ko "$desc -> got $code, expected $expected"
    fi
}

# ============================================================
section "Warm-up (chargement modele)"
printf "  Envoi d'une requete courte...\n"
start=$(date +%s%N)
code=$(post '{"input":"Bonjour."}' "$TMPDIR/warmup.wav")
elapsed=$(( ($(date +%s%N) - start) / 1000000 ))
if [ "$code" = "200" ]; then
    ok "warm-up ${elapsed}ms"
else
    ko "warm-up HTTP $code"
fi

# ============================================================
section "Validation des entrees"

expect_status "texte vide"             '{"input":""}' 200
expect_status "requete normale"        '{"input":"Bonjour le monde."}' 200
expect_status "speed trop basse (0.1)" '{"input":"Test","speed":0.1}' 422
expect_status "speed trop haute (10)"  '{"input":"Test","speed":10}' 422
expect_status "speed min (0.5)"        '{"input":"Test","speed":0.5}' 200
expect_status "speed max (2.0)"        '{"input":"Test","speed":2.0}' 200
expect_status "voice vide"             '{"input":"Test","voice":""}' 422
expect_status "format invalide"        '{"input":"Test","response_format":"flac"}' 422
expect_status "format wav"             '{"input":"Test","response_format":"wav"}' 200

# Texte trop long (750k + 1) — via fichier pour eviter ARG_MAX
python3 -c "import json; f=open('$TMPDIR/long.json','w'); json.dump({'input':'a'*750001},f); f.close()"
expect_status_file "texte > 750k chars" "$TMPDIR/long.json" 422

# ============================================================
section "Qualite audio WAV"

code=$(post '{"input":"Bonjour, ceci est un test de qualite audio."}' "$TMPDIR/quality.wav")
if [ "$code" = "200" ]; then
    # Verifier le header WAV
    magic=$(head -c4 "$TMPDIR/quality.wav" | od -An -tx1 | tr -d ' ')
    if [ "$magic" = "52494646" ]; then
        ok "header WAV RIFF valide"
    else
        ko "header WAV invalide: $magic"
    fi
    size=$(stat -c%s "$TMPDIR/quality.wav" 2>/dev/null || stat -f%z "$TMPDIR/quality.wav")
    if [ "$size" -gt 44 ]; then
        ok "audio non-vide (${size} octets)"
    else
        ko "audio vide ($size octets)"
    fi
else
    ko "requete qualite HTTP $code"
fi

# ============================================================
section "Benchmark performance"

SIZES=(1000 5000 10000)
for chars in "${SIZES[@]}"; do
    # Generer le JSON dans un fichier pour eviter ARG_MAX
    real_len=$(python3 -c "
import json
phrase = 'Ceci est une phrase de test pour mesurer les performances du moteur. '
text = phrase * ($chars // len(phrase) + 1)
with open('$TMPDIR/bench_${chars}.json', 'w') as f:
    json.dump({'input': text}, f)
print(len(text))
")

    start=$(date +%s%N)
    code=$(post_file "$TMPDIR/bench_${chars}.json" "$TMPDIR/bench_${chars}.wav")
    elapsed_ms=$(( ($(date +%s%N) - start) / 1000000 ))
    elapsed_s=$(python3 -c "print(f'{$elapsed_ms/1000:.1f}')")

    if [ "$code" = "200" ]; then
        wav_size=$(stat -c%s "$TMPDIR/bench_${chars}.wav" 2>/dev/null || stat -f%z "$TMPDIR/bench_${chars}.wav")
        # Audio duration: (wav_size - 44 header) / (24000 samples/s * 2 bytes/sample)
        audio_dur=$(python3 -c "print(f'{($wav_size - 44) / (24000 * 2):.1f}')")
        chars_per_sec=$(python3 -c "print(f'{$real_len / ($elapsed_ms / 1000):.0f}')")
        rtf=$(python3 -c "print(f'{float($audio_dur) / ($elapsed_ms / 1000):.1f}')")
        ok "${real_len} chars -> ${elapsed_s}s | ${audio_dur}s audio | ${chars_per_sec} chars/s | ${rtf}x temps reel"
    else
        ko "${chars} chars -> HTTP $code"
    fi
done

# ============================================================
section "Prononciation (spot check)"

# On verifie juste que les requetes avec des mots speciaux ne plantent pas
test_texts=(
    "L'API REST renvoie du JSON."
    "Envoyez un email avec le feedback."
    "Le GPU et le CPU sont au maximum."
    "Le machine learning et le deep learning."
    "J'ai mal au dos, je porte un pull."
)
for txt in "${test_texts[@]}"; do
    printf '%s' "$txt" | python3 -c "
import json, sys
text = sys.stdin.read()
with open('$TMPDIR/prononce.json', 'w') as f:
    json.dump({'input': text}, f)
"
    code=$(post_file "$TMPDIR/prononce.json" /dev/null)
    if [ "$code" = "200" ]; then
        ok "$txt"
    else
        ko "$txt -> HTTP $code"
    fi
done

# ============================================================
section "Resultats"

total=$((pass + fail))
printf "\n  %d/%d tests passes" "$pass" "$total"
if [ "$fail" -gt 0 ]; then
    printf " (\033[31m%d echecs\033[0m)" "$fail"
fi
printf "\n\n"

exit "$fail"
