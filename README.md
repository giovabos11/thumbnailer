# Video Thumbnail Generator Documentation

## Overview

The Video Thumbnail Generator is a powerful and flexible Python library that creates high-quality gif or mp4 thumbnails from video files. It supports various customization options, caching, and can be used both as a Python library or called from other programming languages.

## Installation

### Requirements

- Python 3.7+
- FFmpeg
- MoviePy
- ffmpeg-python

```bash
pip install moviepy ffmpeg-python
```

Make sure FFmpeg is installed on your system:

- For Ubuntu/Debian: `sudo apt-get install ffmpeg`
- For MacOS: `brew install ffmpeg`
- For Windows: Download from [FFmpeg website](https://ffmpeg.org/download.html)

## Basic Usage

### Python

```python
from thumbnail_generator import VideoThumbnailGenerator, ThumbnailOptions

# Initialize the generator
generator = VideoThumbnailGenerator()

# Simple usage with default options
result = generator.generate("input.mp4", ThumbnailOptions())

# Access the result
print(f"Thumbnail created at: {result.path}")
print(f"Dimensions: {result.width}x{result.height}")
```

## Configuration Options

### ThumbnailOptions

| Option              | Type               | Default | Description                                                                                         |
| ------------------- | ------------------ | ------- | --------------------------------------------------------------------------------------------------- |
| quality             | int                | 75      | Output quality (1-100)                                                                              |
| framesPerSection    | int                | 10      | Number of frames to extract per section                                                             |
| sections            | List[VideoSection] | None    | Manual section definitions                                                                          |
| autoSections        | int                | None    | Number of automatically distributed sections                                                        |
| sectionDuration     | float              | 3.0     | Duration of each section in seconds                                                                 |
| width               | int                | None    | Output width (maintains aspect ratio if height not specified)                                       |
| height              | int                | None    | Output height (maintains aspect ratio if width not specified)                                       |
| maintainAspectRatio | bool               | True    | Whether to maintain aspect ratio when resizing                                                      |
| outputPath          | str                | None    | Custom output path (uses cache directory if not specified)                                          |
| cacheDir            | str                | None    | Custom cache directory                                                                              |
| format              | str                | 'gif'   | Output format ('gif' or 'mp4')                                                                      |
| includeAudio        | bool               | False   | Include audio in mp4 output                                                                         |
| audioQuality        | int                | 128     | Audio quality for mp4 (32-256 kbps)                                                                 |
| gifColors           | int                | 256     | Number of colors in the GIF palette (2-256). Higher values give better quality but larger file size |
| gifFuzz             | int                | 30      | Color reduction fuzz factor (1-100). Lower values give better quality but larger file size          |

### VideoSection

| Property  | Type  | Description           |
| --------- | ----- | --------------------- |
| startTime | float | Start time in seconds |
| duration  | float | Duration in seconds   |

## Advanced Usage Examples

### Custom Quality and Dimensions

```python
options = ThumbnailOptions(
    quality=85,
    width=320,
    height=240,
    maintainAspectRatio=True
)
result = generator.generate("input.mp4", options)
```

### Multiple Auto-Distributed Sections

```python
options = ThumbnailOptions(
    autoSections=3,
    sectionDuration=2.0,
    framesPerSection=15
)
result = generator.generate("input.mp4", options)
```

### Manual Section Selection

```python
options = ThumbnailOptions(
    sections=[
        VideoSection(10.5, 2.0),  # 2 seconds starting at 10.5s
        VideoSection(30.0, 3.0),  # 3 seconds starting at 30s
        VideoSection(60.0, 2.5)   # 2.5 seconds starting at 60s
    ]
)
result = generator.generate("input.mp4", options)
```

### MP4 Output with Audio

```python
options = ThumbnailOptions(
    format='mp4',
    includeAudio=True,
    audioQuality=192,
    quality=90
)
result = generator.generate("input.mp4", options)
```

## Result Object (ThumbnailResult)

The generate method returns a ThumbnailResult object with the following properties:

| Property      | Type              | Description                             |
| ------------- | ----------------- | --------------------------------------- |
| path          | str               | Path to the generated thumbnail         |
| width         | int               | Output width                            |
| height        | int               | Output height                           |
| format        | str               | Output format ('gif' or 'mp4')          |
| sections      | List[SectionInfo] | Information about processed sections    |
| totalFrames   | int               | Total number of frames in output        |
| totalDuration | float             | Total duration in seconds               |
| hasAudio      | bool              | Whether the output has audio (mp4 only) |
| audioQuality  | int               | Audio quality used (mp4 only)           |

## Using from Other Languages

### Command Line Interface

```bash
python thumbnail_generator.py input.mp4 --options '{"quality": 85, "autoSections": 3, "format": "gif"}'
```

### JavaScript (Node.js)

```javascript
const result = await generateThumbnail("input.mp4", {
  quality: 85,
  autoSections: 3,
  format: "gif",
});
```

## Caching

The generator automatically caches thumbnails based on:

- Input video content (first 8KB hash)
- Configuration options

Cache location:

- Default: system temporary directory
- Custom: specify through `cacheDir` option

## Error Handling

```python
try:
    result = generator.generate("input.mp4", options)
except Exception as e:
    print(f"Error generating thumbnail: {str(e)}")
```

## Performance Considerations

- Higher quality settings will increase processing time
- More sections or frames will increase processing time
- MP4 output with audio takes longer to process than GIF
- Caching improves subsequent generation speed for identical inputs and options

## Best Practices

1. Use appropriate quality settings for your needs
2. Consider using autoSections for evenly distributed previews
3. Maintain aspect ratio unless specifically needed otherwise
4. Use caching for repeated operations
5. Clean cache periodically if storage is a concern

## Limitations

- Requires FFmpeg installation
- GIF output size can be large for high quality/long duration
- Memory usage increases with video size and number of sections

This documentation should provide a comprehensive overview of the Video Thumbnail Generator's capabilities and usage patterns. Let me know if you need any clarification or additional examples!

## Contributing

Contributions are welcome! Please feel free to submit pull requests and report issues on GitHub.

## License

MIT License - feel free to use this library in your projects.

---

For more information or support, please visit my GitHub repository or raise an issue.
