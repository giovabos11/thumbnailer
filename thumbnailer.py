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
    autoFrames: bool = True
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
    gifColors: int = 256
    gifFuzz: int = 30

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
    originalFps: float = 0.0
    outputFps: float = 0.0

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
            'audioQuality': options.audioQuality,
        }
        
        video_hash = hashlib.md5(open(video_path, 'rb').read(8192)).hexdigest()
        options_hash = hashlib.md5(json.dumps(options_dict).encode()).hexdigest()
        return f"{video_hash}_{options_hash}"

    def generate(self, video_path: str, options: ThumbnailOptions) -> ThumbnailResult:
        """
        Generate a video thumbnail based on the provided options.
        
        Args:
            video_path (str): Path to the input video file
            options (ThumbnailOptions): Configuration options for thumbnail generation
            
        Returns:
            ThumbnailResult: Object containing information about the generated thumbnail
            
        Raises:
            FileNotFoundError: If input video file doesn't exist
            ValueError: If invalid options are provided
            RuntimeError: If thumbnail generation fails
        """
        clips = []
        final_clip = None
        video = None
        
        try:
            # Validate input file
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Input video file not found: {video_path}")

            # Setup cache
            cache_dir = options.cacheDir or self.default_cache_dir
            os.makedirs(cache_dir, exist_ok=True)
            cache_key = self._get_cache_key(video_path, options)
            cache_path = os.path.join(cache_dir, f"{cache_key}.{options.format}")

            # Check cache
            if os.path.exists(cache_path):
                return self._load_from_cache(cache_path, options)

            # Get original video FPS using FFmpeg
            probe = ffmpeg.probe(video_path)
            video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            
            # Parse frame rate which might be in rational format (e.g., '24000/1001')
            fps_str = video_info.get('r_frame_rate', video_info.get('avg_frame_rate', '24/1'))
            if '/' in fps_str:
                num, den = map(float, fps_str.split('/'))
                original_fps = num / den
            else:
                original_fps = float(fps_str)

            # Load video
            video = VideoFileClip(video_path)
            
            # Calculate frames per section if autoFrames is True
            if options.autoFrames:
                # Calculate how many frames are in each section at original FPS
                frames_in_section = int(original_fps * options.sectionDuration)
                
                # Define target number of frames based on section duration
                if options.sectionDuration <= 3:
                    target_frames = max(5, min(frames_in_section, 30))
                else:
                    target_frames = max(10, min(frames_in_section, 45))
                
                # Override framesPerSection
                options.framesPerSection = target_frames

            # Calculate sections
            sections = self._calculate_sections(video, options)
            
            if not sections:
                raise ValueError("No valid sections to process")

            # Extract clips
            original_audio = None
            if options.format == 'mp4' and options.includeAudio and video.audio is not None:
                original_audio = video.audio

            for section in sections:
                if section.startTime + section.duration > video.duration:
                    section.duration = video.duration - section.startTime
                
                if section.duration <= 0:
                    continue
                    
                clip = video.subclip(section.startTime, section.startTime + section.duration)
                
                # Handle audio for each clip
                if original_audio is not None:
                    clip.audio = original_audio.subclip(section.startTime, section.startTime + section.duration)
                
                clips.append(clip)

            if not clips:
                raise ValueError("No valid clips could be extracted")

            # Concatenate clips
            final_clip = concatenate_videoclips(clips, method="compose")

            # Handle resizing
            if options.width or options.height:
                width = options.width or -1
                height = options.height or -1
                
                if options.maintainAspectRatio:
                    if width == -1:
                        width = int(final_clip.size[0] * (height / final_clip.size[1]))
                    elif height == -1:
                        height = int(final_clip.size[1] * (width / final_clip.size[0]))
                    final_clip = final_clip.resize(width=width, height=height)
                else:
                    final_clip = final_clip.resize((width, height) if width != -1 and height != -1 
                                                else (width, width * final_clip.size[1] // final_clip.size[0]))

            # Generate output
            output_path = options.outputPath or cache_path
            
            if options.format == 'gif':
                # Calculate target FPS for GIF
                target_fps = options.framesPerSection / options.sectionDuration
                target_fps = max(1, min(30, target_fps))  # Ensure reasonable FPS
                
                # Quality-based settings
                quality_factor = options.quality / 100.0
                colors = int(128 + (128 * quality_factor))  # 128-256 colors
                fuzz = int(50 - (40 * quality_factor))      # 10-50 fuzz factor
                
                final_clip.write_gif(
                    output_path,
                    fps=target_fps,
                    program='ffmpeg',
                    opt='optimizeplus',
                    fuzz=fuzz,
                    colors=colors
                )
            else:  # mp4
                # Calculate target FPS for MP4
                target_fps = options.framesPerSection / options.sectionDuration
                target_fps = min(original_fps, min(30, target_fps))
                
                # Video quality settings
                video_bitrate = int(500 + (4500 * (options.quality / 100.0)))
                
                # Create temporary audio path in cache directory
                temp_audio_path = os.path.join(
                    options.cacheDir or self.default_cache_dir,
                    f"temp_audio_{cache_key}.m4a"
                )
                
                write_videofile_kwargs = {
                    'fps': target_fps,
                    'codec': 'libx264',
                    'bitrate': f"{video_bitrate}k",
                    'preset': 'medium',
                    'threads': 2,
                    'ffmpeg_params': ['-crf', str(int(31 - (options.quality / 100.0 * 30)))],
                    'temp_audiofile': temp_audio_path
                }

                # Add audio settings if needed
                if options.includeAudio and final_clip.audio is not None:
                    write_videofile_kwargs.update({
                        'audio': True,
                        'audio_codec': 'aac',
                        'audio_bitrate': f"{options.audioQuality}k"
                    })
                else:
                    write_videofile_kwargs['audio'] = False

                final_clip.write_videofile(output_path, **write_videofile_kwargs)

            # Prepare result
            result = ThumbnailResult(
                path=output_path,
                width=int(final_clip.size[0]),
                height=int(final_clip.size[1]),
                format=options.format,
                sections=[
                    SectionInfo(
                        startTime=s.startTime,
                        duration=s.duration,
                        frames=int(s.duration * options.framesPerSection/options.sectionDuration)
                    )
                    for s in sections
                ],
                totalFrames=int(final_clip.duration * options.framesPerSection/options.sectionDuration),
                totalDuration=final_clip.duration,
                hasAudio=options.includeAudio and final_clip.audio is not None if options.format == 'mp4' else None,
                audioQuality=options.audioQuality if options.format == 'mp4' and options.includeAudio else None,
                originalFps=original_fps,
                outputFps=target_fps
            )

            return result

        except Exception as e:
            # Clean up any partially created output file
            if 'output_path' in locals() and os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            raise RuntimeError(f"Failed to generate thumbnail: {str(e)}") from e

        finally:
            # Cleanup
            if video is not None:
                try:
                    video.close()
                except:
                    pass
            for clip in clips:
                try:
                    clip.close()
                except:
                    pass
            if final_clip is not None:
                try:
                    final_clip.close()
                except:
                    pass

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

import argparse
import json

def main():
    parser = argparse.ArgumentParser(description='Video Thumbnail Generator')
    parser.add_argument('input', help='Input video path')
    parser.add_argument('--options', help='JSON string of options')
    args = parser.parse_args()

    options_dict = json.loads(args.options) if args.options else {}
    options = ThumbnailOptions(**options_dict)
    
    generator = VideoThumbnailGenerator()
    result = generator.generate(args.input, options)
    
    print(json.dumps(result.__dict__))

if __name__ == '__main__':
    main()