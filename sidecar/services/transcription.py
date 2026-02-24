"""
Transcription Service - Local Whisper (Base Model) for Edge AI Dictation
"""
import logging
from typing import Optional
import tempfile
import os
import whisper

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        logger.info("Initializing LOCAL Whisper model (base)...")
        
        # Windows Path Hack: If ffmpeg is not in PATH, look for winget installation
        import shutil
        if not shutil.which("ffmpeg"):
            winget_ffmpeg = r"C:\Users\PrashanthKuna\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin"
            if os.path.exists(winget_ffmpeg):
                logger.info(f"Adding local FFmpeg to PATH: {winget_ffmpeg}")
                os.environ["PATH"] += os.pathsep + winget_ffmpeg
            else:
                logger.warning("FFmpeg not found in PATH or standard winget location.")

        # Load a small, fast local model for dictation
        self.model = whisper.load_model("base")
        logger.info("Local Whisper model loaded successfully.")

    async def transcribe(self, audio_data: bytes) -> Optional[str]:
        """
        Transcribe audio bytes using local Whisper
        """
        try:
            # Whisper requires a file path, so we write the bytes to a temp file
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name

            # Run local inference
            result = self.model.transcribe(tmp_path)
            
            # Clean up
            os.remove(tmp_path)
            
            return result.get("text", "").strip()
            
        except FileNotFoundError as e:
            logger.error(f"Local transcription error (Missing Dependency): {e}")
            return "Transcription unavailable: FFmpeg is not installed or not in PATH. Please install FFmpeg to use local Dictation features."
        except Exception as e:
            err_msg = str(e)
            logger.error(f"Local transcription error: {err_msg}")
            if "WinError 2" in err_msg:
                 return "Transcription unavailable: FFmpeg is missing from Windows PATH. Please install FFmpeg (https://ffmpeg.org/download.html) to enable local voice dictation."
            return "Transcription failed (Local Error). Audio note captured."

# Singleton
_transcription_service = None

def get_transcription_service():
    global _transcription_service
    if _transcription_service is None:
        _transcription_service = TranscriptionService()
    return _transcription_service
