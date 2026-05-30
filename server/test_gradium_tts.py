import asyncio
import os
from dotenv import load_dotenv
from pipecat.services.gradium.tts import GradiumTTSService
from pipecat.frames.frames import StartFrame, EndFrame, TextFrame
from pipecat.utils.asyncio.task_manager import TaskManager
from loguru import logger

load_dotenv(override=True)

async def test_tts():
    api_key = os.environ.get("GRADIUM_API_KEY")
    voice_id = os.getenv("GRADIUM_VOICE_ID", "Eu9iL_CYe8N-Gkx_")
    if not voice_id or not voice_id.strip():
        voice_id = "Eu9iL_CYe8N-Gkx_"
        
    print(f"Testing Gradium TTS with key={api_key[:10]}... voice={voice_id}")
    
    tts = GradiumTTSService(
        api_key=api_key,
        settings=GradiumTTSService.Settings(
            voice=voice_id,
        ),
    )
    
    # Initialize task manager
    tm = TaskManager()
    await tts.setup(tm)
    
    # Start the service
    start_frame = StartFrame()
    await tts.start(start_frame)
    
    # Process text
    text = "Hello, you have reached the City 311 Assistant. Let's see if this works!"
    
    # Run synthesis
    async for frame in tts.run_tts(text, context_id="test-ctx"):
        if frame:
            print(f"Received frame: {type(frame)}")
            if hasattr(frame, "audio"):
                print(f"  audio length: {len(frame.audio)}")
                
    # Stop the service
    await tts.stop(EndFrame())
    print("Done!")

if __name__ == "__main__":
    asyncio.run(test_tts())
