import subprocess
import tempfile
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe, read_frames


DEFAULT_BANNER_X = 0.0
DEFAULT_BANNER_Y = 0.0
DEFAULT_BANNER_WIDTH = 100.0
DEFAULT_BANNER_HEIGHT = 15.0
GREEN_SCREEN_COLOR = "0x00FF00"
GREEN_SCREEN_SIMILARITY = 0.3
GREEN_SCREEN_BLEND = 0.12


def _get_video_size(video_path: str) -> tuple[int, int]:
    reader = read_frames(video_path)
    try:
        meta = next(reader)
    finally:
        reader.close()
    width, height = meta["size"]
    return int(width), int(height)


def _clamp_percent(value: float | None, fallback: float, min_value: float, max_value: float) -> float:
    if value is None:
        return fallback
    return max(min_value, min(float(value), max_value))


def compose_clip_with_banner(
    clip_path: str,
    banner_video_path: str,
    banner_x: float | None = None,
    banner_y: float | None = None,
    banner_width: float | None = None,
    banner_height: float | None = None,
    remove_green_background: bool = True,
) -> str:
    clip_width, clip_height = _get_video_size(clip_path)

    x_percent = _clamp_percent(banner_x, DEFAULT_BANNER_X, 0.0, 100.0)
    y_percent = _clamp_percent(banner_y, DEFAULT_BANNER_Y, 0.0, 100.0)
    width_percent = _clamp_percent(banner_width, DEFAULT_BANNER_WIDTH, 1.0, 100.0)
    height_percent = _clamp_percent(banner_height, DEFAULT_BANNER_HEIGHT, 1.0, 100.0)

    banner_width_px = max(1, int(round(clip_width * width_percent / 100)))
    banner_height_px = max(1, int(round(clip_height * height_percent / 100)))
    banner_x_px = min(max(0, int(round(clip_width * x_percent / 100))), max(0, clip_width - banner_width_px))
    banner_y_px = min(max(0, int(round(clip_height * y_percent / 100))), max(0, clip_height - banner_height_px))

    output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    ffmpeg_exe = get_ffmpeg_exe()

    banner_filters = [
        f"scale={banner_width_px}:{banner_height_px}",
        "setsar=1",
    ]
    if remove_green_background:
        banner_filters.extend(
            [
                "format=rgba",
                f"colorkey={GREEN_SCREEN_COLOR}:{GREEN_SCREEN_SIMILARITY}:{GREEN_SCREEN_BLEND}",
            ]
        )

    filter_complex = (
        f"[1:v]{','.join(banner_filters)}[banner];"
        f"[0:v][banner]overlay={banner_x_px}:{banner_y_px}:shortest=1:format=auto[outv]"
    )

    command = [
        ffmpeg_exe,
        "-y",
        "-i",
        str(Path(clip_path)),
        "-stream_loop",
        "-1",
        "-i",
        str(Path(banner_video_path)),
        "-filter_complex",
        filter_complex,
        "-map",
        "[outv]",
        "-map",
        "0:a?",
        "-c:a",
        "copy",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "28",
        "-threads",
        "2",
        "-pix_fmt",
        "yuv420p",
        "-shortest",
        output_path,
    ]

    subprocess.run(command, check=True, capture_output=True)
    return output_path
