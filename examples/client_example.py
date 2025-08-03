#!/usr/bin/env python3
"""
MeloTTS API Client Example

This example demonstrates how to use the secure MeloTTS API service.
"""

import requests
import base64
import json
import os
from typing import Optional

class MeloTTSClient:
    def __init__(self, base_url: str, api_token: str, verify_ssl: bool = True):
        """
        Initialize the MeloTTS client.
        
        Args:
            base_url: Base URL of the TTS service (e.g., 'https://api.example.com')
            api_token: API token for authentication
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.verify_ssl = verify_ssl
        self.headers = {
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        }
    
    def health_check(self) -> dict:
        """Check the health status of the service."""
        response = requests.get(
            f'{self.base_url}/health',
            headers=self.headers,
            verify=self.verify_ssl
        )
        response.raise_for_status()
        return response.json()
    
    def get_languages(self) -> dict:
        """Get supported languages and their status."""
        response = requests.get(
            f'{self.base_url}/languages',
            headers=self.headers,
            verify=self.verify_ssl
        )
        response.raise_for_status()
        return response.json()
    
    def get_models_status(self) -> dict:
        """Get detailed status of all models."""
        response = requests.get(
            f'{self.base_url}/models/status',
            headers=self.headers,
            verify=self.verify_ssl
        )
        response.raise_for_status()
        return response.json()
    
    def get_speakers(self, language: str) -> dict:
        """Get available speakers for a specific language."""
        response = requests.get(
            f'{self.base_url}/speakers/{language}',
            headers=self.headers,
            verify=self.verify_ssl
        )
        response.raise_for_status()
        return response.json()
    
    def synthesize_text(self, 
                       text: str, 
                       language: str = "EN", 
                       speaker: str = "EN-US",
                       speed: float = 1.0,
                       output_file: Optional[str] = None) -> dict:
        """
        Synthesize text to speech.
        
        Args:
            text: Text to convert to speech
            language: Language code (EN, ES, FR, ZH, JP, KR)
            speaker: Speaker ID
            speed: Speech speed multiplier
            output_file: Optional file path to save the audio
        
        Returns:
            Dictionary containing audio data and metadata
        """
        payload = {
            "text": text,
            "language": language,
            "speaker": speaker,
            "speed": speed
        }
        
        response = requests.post(
            f'{self.base_url}/synthesize',
            headers=self.headers,
            json=payload,
            verify=self.verify_ssl
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Save audio file if requested
        if output_file:
            audio_data = base64.b64decode(result['audio_base64'])
            with open(output_file, 'wb') as f:
                f.write(audio_data)
            print(f"Audio saved to: {output_file}")
        
        return result
    
    def synthesize_text_audio_file(self,
                                  text: str,
                                  language: str = "EN",
                                  speaker: str = "EN-US",
                                  speed: float = 1.0,
                                  output_file: str = "speech.mp3") -> bool:
        """
        Synthesize text to speech and save as audio file directly.
        
        Args:
            text: Text to convert to speech
            language: Language code
            speaker: Speaker ID
            speed: Speech speed multiplier
            output_file: File path to save the audio
        
        Returns:
            True if successful, False otherwise
        """
        payload = {
            "text": text,
            "language": language,
            "speaker": speaker,
            "speed": speed
        }
        
        response = requests.post(
            f'{self.base_url}/synthesize/audio',
            headers=self.headers,
            json=payload,
            verify=self.verify_ssl
        )
        response.raise_for_status()
        
        with open(output_file, 'wb') as f:
            f.write(response.content)
        
        print(f"Audio saved to: {output_file}")
        print(f"Sample rate: {response.headers.get('X-Sample-Rate')}")
        print(f"Duration: {response.headers.get('X-Duration')} seconds")
        return True

def main():
    """Example usage of the MeloTTS client."""
    
    # Configuration
    API_URL = os.getenv('MELOTTS_API_URL', 'https://localhost:8000')
    API_TOKEN = os.getenv('MELOTTS_API_TOKEN', 'your-secure-api-token-here')
    
    # Initialize client
    client = MeloTTSClient(API_URL, API_TOKEN, verify_ssl=False)  # Set verify_ssl=True in production
    
    try:
        # Check service health
        print("=== Health Check ===")
        health = client.health_check()
        print(f"Status: {health['status']}")
        print(f"Device: {health['device']}")
        print("Models loaded:")
        for lang, loaded in health['models_loaded'].items():
            print(f"  {lang}: {'✓' if loaded else '✗'}")
        
        # Get supported languages
        print("\n=== Supported Languages ===")
        languages = client.get_languages()
        print(f"Languages: {languages['languages']}")
        
        # Check model status before any requests
        print("\n=== Model Status (Before Requests) ===")
        try:
            models_status = client.get_models_status()
            print(f"Total supported: {models_status['total_supported']}")
            print(f"Currently loaded: {models_status['currently_loaded']}")
            print(f"Loaded models: {models_status['loaded_models']}")
            print(f"Unloaded models: {models_status['unloaded_models']}")
        except Exception as e:
            print(f"Could not get model status: {e}")
        
        # Get speakers for English
        print("\n=== English Speakers ===")
        speakers = client.get_speakers('EN')
        print(f"Available speakers: {speakers['speakers']}")
        
        # Synthesize text
        print("\n=== Text Synthesis ===")
        test_text = "Hello! This is a test of the MeloTTS API service. The text-to-speech conversion is working perfectly."
        
        # Method 1: Get base64 encoded audio
        result = client.synthesize_text(
            text=test_text,
            language="EN",
            speaker="EN-US",
            speed=1.0,
            output_file="output_base64.mp3"
        )
        print(f"Text length: {result['text_length']}")
        print(f"Duration: {result['duration']:.2f} seconds")
        print(f"Sample rate: {result['sample_rate']}")
        
        # Method 2: Get audio file directly
        client.synthesize_text_audio_file(
            text=test_text,
            language="EN",
            speaker="EN-US",
            speed=1.0,
            output_file="output_direct.mp3"
        )
        
        # Test different languages (demonstrates lazy loading)
        print("\n=== Multi-language Test (Lazy Loading Demo) ===")
        test_cases = [
            ("EN", "EN-US", "Hello, this is English text."),
            ("ES", "ES-ES", "Hola, este es texto en español."),
            ("FR", "FR-FR", "Bonjour, ceci est du texte en français."),
        ]
        
        for i, (lang, speaker, text) in enumerate(test_cases):
            try:
                print(f"\n--- Testing {lang} (Request {i+1}) ---")
                
                # Check model status before this language request
                models_status = client.get_models_status()
                print(f"Models loaded before {lang}: {models_status['loaded_models']}")
                
                speakers = client.get_speakers(lang)
                if speakers['speakers']:
                    available_speaker = speakers['speakers'][0]
                    output_file = f"test_{lang.lower()}.mp3"
                    client.synthesize_text_audio_file(
                        text=text,
                        language=lang,
                        speaker=available_speaker,
                        output_file=output_file
                    )
                    
                    # Check model status after this language request
                    models_status = client.get_models_status()
                    print(f"Models loaded after {lang}: {models_status['loaded_models']}")
                    
            except Exception as e:
                print(f"Error with {lang}: {e}")
        
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 