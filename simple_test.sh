#!/bin/sh

if [ -z "$1" ]; then
    echo "Need host."
    exit 1
fi

HOST="$1"

# 1. Check service health
curl "http://$HOST/health"

# 2. Check model status
curl "http://$HOST/models/status"

# 3. Test synthesis with proper headers
curl -X POST \
     -H "Authorization: Bearer token" \
     -H "Content-Type: application/json" \
     -d '{"text": "Esto es una prueba. Mátame camión", "language": "ES", "speaker": "ES"}' \
     "http://$HOST/synthesize" \
     | jq -r '.audio_base64' | base64 -d > output.mp3

