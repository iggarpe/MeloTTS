#!/bin/sh

# 1. Check service health
curl http://localhost:8000/health

# 2. Check model status
curl http://localhost:8000/models/status

# 3. Test synthesis with proper headers
curl -X POST \
     -H "Authorization: Bearer token" \
     -H "Content-Type: application/json" \
     -d '{"text": "Esto es una prueba. Mátame camión", "language": "ES", "speaker": "ES"}' \
     http://localhost:8000/synthesize \
     | jq -r '.audio_base64' | base64 -d > output.mp3

