from dataclasses import dataclass
from typing import List, Optional, Literal
import os
import hashlib
import json
from pathlib import Path
import tempfile
from moviepy.editor import VideoFileClip, concatenate_videoclips
import ffmpeg

OutputFormat = Literal['gif', 'mp4']

@dataclass
class VideoSection:
    startTime: float
    duration: float

@dataclass
class ThumbnailOptions:
    quality: int = 75
    framesPerSection: int = 10
    sections: Optional[List[VideoSection]] = None
    autoSections: Optional[int] = None
    sectionDuration: float = 3.0
    width: Optional[int] = None
    height: Optional[int] = None
    maintainAspectRatio: bool = True
    outputPath: Optional[str] = None
    cacheDir: Optional[str] = None
    format: OutputFormat = 'gif'
    includeAudio: bool = False
    audioQuality: int = 128

@dataclass
class SectionInfo:
    startTime: float
    duration: float
    frames: int

@dataclass
class ThumbnailResult:
    path: str
    width: int
    height: int
    format: OutputFormat
    sections: List[SectionInfo]
    totalFrames: int
    totalDuration: float
    hasAudio: Optional[bool] = None
    audioQuality: Optional[int] = None

class VideoThumbnailGenerator:
    def __init__(self):
        self.default_cache_dir = os.path.join(tempfile.gettempdir(), 'video_thumbnails')
        os.makedirs(self.default_cache_dir, exist_ok=True)

    def _get_cache_key(self, video_path: str, options: ThumbnailOptions) -> str:
        """Generate a unique cache key based on video path and options"""
        options_dict = {
            'quality': options.quality,
            'framesPerSection': options.framesPerSection,
            'sections': [(s.startTime, s.duration) for s in (options.sections or [])],
            'autoSections': options.autoSections,
            'sectionDuration': options.sectionDuration,
            'width': options.width,
            'height': options.height,
            'maintainAspectRatio': options.maintainAspectRatio,
            'format': options.format,
            'includeAudio': options.includeAudio,
            'audioQuality': options.audioQuality
        }
        
        video_hash = hashlib.md5(open(video_path, 'rb').read(8192)).hexdigest()
        options_hash = hashlib.md5(json.dumps(options_dict).encode()).hexdigest()
        return f"{video_hash}_{options_hash}"

    def generate(self, video_path: str, options: ThumbnailOptions) -> ThumbnailResult:
        cache_dir = options.cacheDir or self.default_cache_dir
        cache_key = self._get_cache_key(video_path, options)
        cache_path = os.path.join(cache_dir, f"{cache_key}.{options.format}")

        # Check cache
        if os.path.exists(cache_path):
            return self._load_from_cache(cache_path, options)

        # Process video
        video = VideoFileClip(video_path)
        
        # Calculate sections
        sections = self._calculate_sections(video, options)
        
        # Extract clips
        clips = []
        for section in sections:
            clip = video.subclip(section.startTime, section.startTime + section.duration)
            clips.append(clip)

        # Concatenate clips
        final_clip = concatenate_videoclips(clips)

        # Resize if needed
        if options.width or options.height:
            width = options.width or -1
            height = options.height or -1
            if options.maintainAspectRatio:
                final_clip = final_clip.resize(width=width, height=height)
            else:
                final_clip = final_clip.resize((width, height))

        # Generate output
        output_path = options.outputPath or cache_path
        if options.format == 'gif':
            final_clip.write_gif(output_path, fps=options.framesPerSection/options.sectionDuration,
                               program='ffmpeg', optimize=True, quality=options.quality)
        else:  # mp4
            audio = None if not options.includeAudio else video.audio
            final_clip.write_videofile(output_path, fps=options.framesPerSection/options.sectionDuration,
                                     audio=audio, audio_bitrate=f"{options.audioQuality}k")

        video.close()

        return ThumbnailResult(
            path=output_path,
            width=int(final_clip.size[0]),
            height=int(final_clip.size[1]),
            format=options.format,
            sections=[SectionInfo(s.startTime, s.duration, 
                                int(s.duration * options.framesPerSection/options.sectionDuration))
                     for s in sections],
            totalFrames=int(final_clip.duration * options.framesPerSection/options.sectionDuration),
            totalDuration=final_clip.duration,
            hasAudio=options.includeAudio if options.format == 'mp4' else None,
            audioQuality=options.audioQuality if options.format == 'mp4' and options.includeAudio else None
        )

    def _calculate_sections(self, video: VideoFileClip, options: ThumbnailOptions) -> List[VideoSection]:
        if options.sections:
            return options.sections
        
        if options.autoSections:
            duration = video.duration
            section_count = options.autoSections
            section_duration = options.sectionDuration
            interval = (duration - section_duration) / (section_count - 1) if section_count > 1 else 0
            
            return [
                VideoSection(i * interval, section_duration)
                for i in range(section_count)
            ]
        
        return [VideoSection(0, options.sectionDuration)]

    def _load_from_cache(self, cache_path: str, options: ThumbnailOptions) -> ThumbnailResult:
        clip = VideoFileClip(cache_path) if options.format == 'mp4' else None
        
        return ThumbnailResult(
            path=cache_path,
            width=int(clip.size[0]) if clip else None,
            height=int(clip.size[1]) if clip else None,
            format=options.format,
            sections=[],  # Would need to store metadata separately to recover this
            totalFrames=int(clip.duration * options.framesPerSection/options.sectionDuration) if clip else None,
            totalDuration=clip.duration if clip else None,
            hasAudio=options.includeAudio if options.format == 'mp4' else None,
            audioQuality=options.audioQuality if options.format == 'mp4' and options.includeAudio else None
        )

# Example usage

if __name__ == '__main__':
    generator = VideoThumbnailGenerator()
    options = ThumbnailOptions(
        quality=85,
        framesPerSection=100,
        autoSections=8,
        sectionDuration=3.0,
        width=320,
        height=240,
        format='mp4',
        includeAudio=True,
        cacheDir='./cache/'
    )
    result = generator.generate("input.mp4", options).path
    print(f"Thumbnail: {result}")