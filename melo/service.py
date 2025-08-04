import os
import io
import base64
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
import torch
import soundfile as sf
from .api import TTS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Pydantic models for request/response
class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Text to convert to speech")
    language: str = Field(default="EN", description="Language code (EN, ES, FR, ZH, JP, KR)")
    speaker: str = Field(default="EN-US", description="Speaker ID")
    speed: float = Field(default=1.0, ge=0.1, le=10.0, description="Speech speed multiplier")
    sdp_ratio: float = Field(default=0.2, ge=0.0, le=1.0, description="SDP ratio for speech synthesis")
    noise_scale: float = Field(default=0.6, ge=0.0, le=1.0, description="Noise scale for speech synthesis")
    noise_scale_w: float = Field(default=0.8, ge=0.0, le=1.0, description="Noise scale W for speech synthesis")

class TTSResponse(BaseModel):
    audio_base64: str = Field(..., description="Base64 encoded MP3 audio data")
    sample_rate: int = Field(..., description="Audio sample rate")
    duration: float = Field(..., description="Audio duration in seconds")
    text_length: int = Field(..., description="Length of input text")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status")
    models_loaded: Dict[str, bool] = Field(..., description="Status of loaded models")
    device: str = Field(..., description="Current device being used")

class MeloTTSService:
    def __init__(self, device: str = 'auto', use_hf: bool = True):
        self.device = device
        self.use_hf = use_hf
        self.models = {}
        self.supported_languages = ['EN', 'ES', 'FR', 'ZH', 'JP', 'KR']
        self.model_loading_locks = {}  # Thread-safe loading
        self._initialize_locks()
    
    def _initialize_locks(self):
        """Initialize locks for thread-safe model loading"""
        import threading
        for language in self.supported_languages:
            self.model_loading_locks[language] = threading.Lock()
    
    def _load_model(self, language: str) -> TTS:
        """Load a specific language model"""
        try:
            logger.info(f"Loading {language} model...")
            model = TTS(
                language=language, 
                device=self.device,
                use_hf=self.use_hf
            )
            logger.info(f"Successfully loaded {language} model")
            return model
        except Exception as e:
            logger.error(f"Failed to load {language} model: {e}")
            return None
    
    def get_model(self, language: str) -> TTS:
        """Get a specific language model with lazy loading"""
        if language not in self.supported_languages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Language {language} is not supported"
            )
        
        # Check if model is already loaded
        if language in self.models and self.models[language] is not None:
            return self.models[language]
        
        # Load model with thread safety
        with self.model_loading_locks[language]:
            # Double-check after acquiring lock (in case another thread loaded it)
            if language in self.models and self.models[language] is not None:
                return self.models[language]
            
            # Load the model
            model = self._load_model(language)
            if model is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to load {language} model"
                )
            
            self.models[language] = model
            return model
    
    def synthesize(self, request: TTSRequest) -> TTSResponse:
        """Synthesize text to speech"""
        try:
            model = self.get_model(request.language)
            
            # Validate speaker
            available_speakers = list(model.hps.data.spk2id.keys())
            if request.speaker not in available_speakers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Speaker '{request.speaker}' not available. Available speakers: {available_speakers}"
                )
            
            # Get speaker ID
            speaker_id = model.hps.data.spk2id[request.speaker]
            
            # Create temporary buffer for audio
            audio_buffer = io.BytesIO()
            
            # Synthesize speech
            audio = model.tts_to_file(
                text=request.text,
                speaker_id=speaker_id,
                output_path=audio_buffer,
                sdp_ratio=request.sdp_ratio,
                noise_scale=request.noise_scale,
                noise_scale_w=request.noise_scale_w,
                speed=request.speed,
                format='mp3',
                quiet=True
            )
            
            # Get audio data
            audio_buffer.seek(0)
            audio_data = audio_buffer.read()
            
            # Calculate duration (approximate)
            duration = len(audio_data) / (model.hps.data.sampling_rate * 2)  # Rough estimate
            
            # Encode to base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            return TTSResponse(
                audio_base64=audio_base64,
                sample_rate=model.hps.data.sampling_rate,
                duration=duration,
                text_length=len(request.text)
            )
            
        except Exception as e:
            logger.error(f"Error during synthesis: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Speech synthesis failed: {str(e)}"
            )
    
    def get_health_status(self) -> HealthResponse:
        """Get service health status"""
        models_loaded = {
            lang: model is not None 
            for lang, model in self.models.items()
        }
        
        # Add supported but not yet loaded languages
        for lang in self.supported_languages:
            if lang not in models_loaded:
                models_loaded[lang] = False
        
        return HealthResponse(
            status="healthy",  # Service is healthy even if no models are loaded yet
            models_loaded=models_loaded,
            device=self.device
        )

# Initialize the service
tts_service = MeloTTSService()

# FastAPI app
app = FastAPI(
    title="MeloTTS API",
    description="Secure Text-to-Speech API using MeloTTS",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENABLE_DOCS", "true").lower() == "true" else None,
    redoc_url="/redoc" if os.getenv("ENABLE_DOCS", "true").lower() == "true" else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication function
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API token"""
    token = credentials.credentials
    expected_token = os.getenv("API_TOKEN")
    
    if not expected_token:
        logger.warning("No API_TOKEN set, allowing all requests")
        return True
    
    if token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return tts_service.get_health_status()

@app.post("/synthesize", response_model=TTSResponse)
async def synthesize_speech(
    request: TTSRequest,
    authenticated: bool = Depends(verify_token)
):
    """Convert text to speech"""
    return tts_service.synthesize(request)

@app.post("/synthesize/audio")
async def synthesize_speech_audio(
    request: TTSRequest,
    authenticated: bool = Depends(verify_token)
):
    """Convert text to speech and return raw audio file"""
    try:
        response = tts_service.synthesize(request)
        audio_data = base64.b64decode(response.audio_base64)
        
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=speech.mp3",
                "X-Sample-Rate": str(response.sample_rate),
                "X-Duration": str(response.duration),
                "X-Text-Length": str(response.text_length)
            }
        )
    except Exception as e:
        logger.error(f"Error in audio endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio generation failed: {str(e)}"
        )

@app.get("/speakers/{language}")
async def get_speakers(
    language: str,
    authenticated: bool = Depends(verify_token)
):
    """Get available speakers for a language"""
    try:
        model = tts_service.get_model(language)
        speakers = list(model.hps.data.spk2id.keys())
        return {"language": language, "speakers": speakers}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.get("/languages")
async def get_languages():
    """Get supported languages"""
    return {
        "languages": tts_service.supported_languages,
        "models_loaded": tts_service.get_health_status().models_loaded
    }

@app.get("/models/status")
async def get_models_status():
    """Get detailed status of all models"""
    status = tts_service.get_health_status()
    loaded_models = [lang for lang, loaded in status.models_loaded.items() if loaded]
    unloaded_models = [lang for lang, loaded in status.models_loaded.items() if not loaded]
    
    return {
        "total_supported": len(tts_service.supported_languages),
        "currently_loaded": len(loaded_models),
        "loaded_models": loaded_models,
        "unloaded_models": unloaded_models,
        "models_loaded": status.models_loaded,
        "device": status.device
    }

if __name__ == "__main__":
    import uvicorn
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="MeloTTS Service")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"), 
                       help="Host to bind to (default: 0.0.0.0 for all interfaces, 127.0.0.1 for localhost only)")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8000)), 
                       help="Port to bind to (default: 8000)")
    parser.add_argument("--reload", action="store_true", 
                       help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
    uvicorn.run(
        "melo.service:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    ) 