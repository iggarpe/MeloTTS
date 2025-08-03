# MeloTTS Secure API Service Deployment Guide

This guide explains how to deploy the MeloTTS text-to-speech model as a secure REST API service.

## Overview

The MeloTTS API service provides:
- **Secure REST API** with Bearer token authentication
- **HTTPS encryption** with SSL/TLS
- **Rate limiting** to prevent abuse
- **Multiple language support** (EN, ES, FR, ZH, JP, KR)
- **Docker containerization** for easy deployment
- **Health monitoring** and logging

## Architecture

```
┌─────────────────┐    HTTPS    ┌─────────────────┐    HTTP     ┌─────────────────┐
│   Client Apps   │ ──────────► │   Nginx Proxy   │ ──────────► │  MeloTTS API    │
│                 │             │   (SSL/TLS)     │             │   (FastAPI)     │
└─────────────────┘             └─────────────────┘             └─────────────────┘
                                        │                                │
                                        ▼                                ▼
                               ┌─────────────────┐              ┌─────────────────┐
                               │   Rate Limiting │              │   TTS Models    │
                               │   Security      │              │   (Lazy Loaded) │
                               └─────────────────┘              └─────────────────┘
```

**Lazy Loading:** Models are loaded on-demand when first requested, reducing startup time and memory usage.

## Prerequisites

- Docker and Docker Compose
- At least 4GB RAM available
- SSL certificates (for production)
- API token for authentication

## Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo>
cd MeloTTS
```

### 2. Set Environment Variables

Create a `.env` file:

```bash
# API Configuration
API_TOKEN=your-super-secure-api-token-here
PORT=8000
ENABLE_DOCS=true

# CORS Configuration
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Optional: SSL Configuration (for production)
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

### 3. Deploy with Docker Compose

#### Development (HTTP only)
```bash
docker-compose up -d melotts-api
```

#### Production (with HTTPS)
```bash
# Create SSL directory and add certificates
mkdir -p ssl
cp your-cert.pem ssl/cert.pem
cp your-key.pem ssl/key.pem

# Deploy with Nginx
docker-compose --profile production up -d
```

### 4. Verify Deployment

```bash
# Check service health
curl -H "Authorization: Bearer your-super-secure-api-token-here" \
     https://localhost/health

# Check API documentation
open https://localhost/docs
```

## API Endpoints

### Authentication
All endpoints require Bearer token authentication:
```
Authorization: Bearer your-api-token
```

### Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health check |
| GET | `/languages` | Get supported languages |
| GET | `/models/status` | Get detailed model loading status |
| GET | `/speakers/{language}` | Get speakers for language |
| POST | `/synthesize` | Convert text to speech (JSON response) |
| POST | `/synthesize/audio` | Convert text to speech (MP3 file) |

### Example Usage

#### Health Check
```bash
curl -H "Authorization: Bearer your-token" \
     https://api.example.com/health
```

#### Text-to-Speech
```bash
curl -X POST \
     -H "Authorization: Bearer your-token" \
     -H "Content-Type: application/json" \
     -d '{
       "text": "Hello, world!",
       "language": "EN",
       "speaker": "EN-US",
       "speed": 1.0
     }' \
     https://api.example.com/synthesize
```

## Security Features

### 1. Authentication
- Bearer token authentication required for all endpoints
- Tokens should be strong and rotated regularly

### 2. HTTPS/SSL
- All traffic encrypted with TLS 1.2/1.3
- HTTP to HTTPS redirect
- Secure cipher suites

### 3. Rate Limiting
- 10 requests per second per IP
- Burst allowance of 20 requests
- Configurable limits

### 4. Security Headers
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security
- Content-Security-Policy

### 5. Input Validation
- Text length limits (1-5000 characters)
- Parameter validation and sanitization
- SQL injection protection

## Production Deployment

### 1. SSL Certificates

For production, obtain SSL certificates:

```bash
# Using Let's Encrypt
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem
```

### 2. Environment Configuration

```bash
# Production .env
API_TOKEN=your-production-token
ENABLE_DOCS=false  # Disable in production
ALLOWED_ORIGINS=https://yourdomain.com
```

### 3. Monitoring and Logging

```bash
# View logs
docker-compose logs -f melotts-api

# Monitor resource usage
docker stats
```

### 4. Backup and Recovery

```bash
# Backup models and configuration
docker-compose exec melotts-api tar -czf /backup/models.tar.gz /app/cache

# Restore from backup
docker-compose exec melotts-api tar -xzf /backup/models.tar.gz -C /
```

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  melotts-api:
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

### Load Balancer Configuration

```nginx
upstream melotts_cluster {
    server melotts-api-1:8000;
    server melotts-api-2:8000;
    server melotts-api-3:8000;
}
```

## Troubleshooting

### Common Issues

1. **Out of Memory**
   ```bash
   # Increase Docker memory limit
   docker-compose down
   docker system prune
   # Restart with more memory
   ```

2. **Model Loading Failures**
   ```bash
   # Check model downloads
   docker-compose logs melotts-api | grep "Loading"
   ```

3. **SSL Certificate Issues**
   ```bash
   # Verify certificate paths
   ls -la ssl/
   # Check Nginx configuration
   docker-compose exec nginx nginx -t
   ```

### Performance Optimization

1. **GPU Acceleration** (if available)
   ```yaml
   services:
     melotts-api:
       runtime: nvidia
       environment:
         - NVIDIA_VISIBLE_DEVICES=all
   ```

2. **Model Caching**
   - Models are automatically cached in `/app/cache`
   - Mount as volume for persistence

3. **Connection Pooling**
   ```nginx
   upstream melotts_api {
       server melotts-api:8000 max_fails=3 fail_timeout=30s;
       keepalive 32;
   }
   ```

## Lazy Loading

The service uses lazy loading for language models, which provides several benefits:

### **How It Works:**
- Models are loaded only when first requested for a specific language
- Thread-safe loading prevents conflicts when multiple requests arrive simultaneously
- Once loaded, models stay in memory for subsequent requests

### **Benefits:**
- **Faster startup:** Service starts immediately without loading all models
- **Lower initial memory:** Only uses memory for models that are actually used
- **On-demand loading:** Models are loaded when first requested
- **Efficient resource usage:** Memory usage grows based on actual usage patterns

### **Memory Usage Examples:**

| Scenario | Memory Usage | Models Loaded |
|----------|--------------|---------------|
| **Service startup** | ~100MB | 0 |
| **First EN request** | ~1GB | EN |
| **First ES request** | ~2GB | EN, ES |
| **All languages used** | ~6GB | EN, ES, FR, ZH, JP, KR |

### **Monitoring Model Loading:**

```bash
# Check which models are currently loaded
curl -H "Authorization: Bearer your-token" \
     https://api.example.com/models/status

# Response example:
{
  "total_supported": 6,
  "currently_loaded": 2,
  "loaded_models": ["EN", "ES"],
  "unloaded_models": ["FR", "ZH", "JP", "KR"],
  "models_loaded": {
    "EN": true,
    "ES": true,
    "FR": false,
    "ZH": false,
    "JP": false,
    "KR": false
  },
  "device": "cuda"
}
```

## Client Integration

See `examples/client_example.py` for a complete Python client implementation.

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

const client = axios.create({
  baseURL: 'https://api.example.com',
  headers: {
    'Authorization': 'Bearer your-token'
  }
});

// Synthesize text
const response = await client.post('/synthesize', {
  text: 'Hello, world!',
  language: 'EN',
  speaker: 'EN-US'
});

// Decode and save audio
const audioData = Buffer.from(response.data.audio_base64, 'base64');
require('fs').writeFileSync('output.mp3', audioData);
```

## Support

For issues and questions:
1. Check the logs: `docker-compose logs melotts-api`
2. Verify configuration and environment variables
3. Test with the provided client example
4. Check the API documentation at `/docs` endpoint 