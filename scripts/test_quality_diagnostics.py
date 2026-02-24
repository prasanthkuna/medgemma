import asyncio
import sys
import os
from pathlib import Path

# Add sidecar to path
sys.path.append(os.path.abspath("sidecar"))
from services.quality import check_quality

async def test_image():
    img_path = Path("data/demo/case_002_ortho_blurry/implant_sticker.jpg")
    print(f"Testing quality for: {img_path}")
    
    if not img_path.exists():
        print("Error: File not found")
        return
        
    flags = await check_quality(str(img_path.absolute()), "image/jpeg")
    print(f"Quality Flags: {flags}")

if __name__ == "__main__":
    asyncio.run(test_image())
