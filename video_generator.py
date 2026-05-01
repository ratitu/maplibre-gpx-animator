import asyncio
import json
import os
from pathlib import Path
from typing import List, Dict, Optional
import subprocess
import tempfile

class VideoGenerator:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir = Path(tempfile.mkdtemp())

    async def capture_frames(self, html_path: str, duration: float, fps: int = 30,
                            width: int = 1920, height: int = 1080) -> List[str]:
        from playwright.async_api import async_playwright

        frame_dir = self.temp_dir / "frames"
        frame_dir.mkdir(exist_ok=True)

        frame_paths = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={'width': width, 'height': height})
            await page.goto(f"file://{html_path}", wait_until='networkidle')

            await page.wait_for_timeout(2000)

            total_frames = int(duration * fps)
            for frame in range(total_frames):
                progress = frame / total_frames
                await page.evaluate(f"updatePosition({progress})")
                await page.wait_for_timeout(16)

                frame_path = frame_dir / f"frame_{frame:06d}.png"
                await page.screenshot(path=str(frame_path))
                frame_paths.append(str(frame_path))

            await browser.close()

        return frame_paths

    def frames_to_video(self, frame_paths: List[str], output_path: str,
                        fps: int = 30, width: int = 1920, height: int = 1080) -> str:
        frame_pattern = str(Path(frame_paths[0]).parent / "frame_%06d.png")

        cmd = [
            'ffmpeg', '-y',
            '-framerate', str(fps),
            '-i', frame_pattern,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '18',
            '-pix_fmt', 'yuv420p',
            '-vf', f'scale={width}:{height}',
            output_path
        ]

        subprocess.run(cmd, capture_output=True, check=True)
        return output_path

    async def generate_video(self, html_path: str, duration: float,
                             output_filename: str = "animation.mp4",
                             fps: int = 30, width: int = 1920,
                             height: int = 1080) -> str:
        output_path = str(self.output_dir / output_filename)

        frame_paths = await self.capture_frames(html_path, duration, fps, width, height)
        self.frames_to_video(frame_paths, output_path, fps, width, height)

        return output_path

    def cleanup(self):
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
