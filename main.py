from thumbnailer import VideoThumbnailGenerator, ThumbnailOptions

# Initialize the generator
generator = VideoThumbnailGenerator()

options = ThumbnailOptions(
    format='mp4',
    includeAudio=True,
    audioQuality=192,
    quality=90,
    cacheDir='cache',
    autoSections=8,
    framesPerSection=100,
)

result = generator.generate("input.mp4", options)

# Access the result
print(f"Thumbnail created at: {result.path}")
print(f"Dimensions: {result.width}x{result.height}")