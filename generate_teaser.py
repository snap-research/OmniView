#!/usr/bin/env python3
"""
Script to generate a compilation video showcasing different tasks.
Each task section shows conditioning followed by generated results.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

# =============================================================================
# CONFIGURATION - Customize these lists to select videos for each task
# =============================================================================

# Video selections per task (customize these lists)
TASK_VIDEOS = {
    "video_nvs": [
        "video_nvs_43",
        "video_nvs_12",
        "video_nvs_34",
        "video_nvs_26",
        "video_nvs_38",
        "video_nvs_40",
    ],
    "static_nvs": ["static_nvs_01", "static_nvs_03", "static_nvs_12", "static_nvs_15"],
    "i2v": ["i2v_22", "i2v_01", "i2v_03", "i2v_09"],
    "v2v": ["v2v_01", "v2v_02"],
}

# Task display names and descriptions
TASK_INFO = {
    "video_nvs": {
        "name": "Video Novel View Synthesis",
        "description": "Generating new viewpoints from video sequences",
    },
    "static_nvs": {
        "name": "Static Novel View Synthesis",
        "description": "Generating new viewpoints from static images",
    },
    "i2v": {"name": "Image-to-Video Generation", "description": "Converting static images to dynamic video sequences"},
    "v2v": {"name": "Video-to-Video Translation", "description": "Transforming shorter videos into longer sequences"},
}

# Video settings
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 24
TITLE_DURATION = 3  # seconds for title cards
VIDEO_DURATION = 6  # seconds per conditioning/generated pair
FREEZE_DURATION = 1  # seconds to freeze on final frame
KEYFRAME_DURATION = 8  # longer duration for keyframe interpolation

# Paths
VIDEOS_DIR = Path("static/videos/demos")
OUTPUT_PATH = "static/videos/teaser.mp4"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def check_ffmpeg():
    """Check if ffmpeg is available."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def create_title_card(text: str, subtitle: str, duration: float, output_path: str, logo_path: str = None):
    """Create a title card video with text overlay and optional logo."""
    if logo_path and os.path.exists(logo_path):
        # With logo - invert colors (black to white) and position logo before text
        logo_size = 200  # Logo height
        spacing = 40  # Space between logo and text

        # Calculate approximate positions - center the logo+text combination
        # Assuming "OmniView" text is roughly 800px wide at 144pt font
        text_width_estimate = 800
        total_width = logo_size + spacing + text_width_estimate
        start_x = (VIDEO_WIDTH - total_width) // 2

        logo_x = start_x
        text_x = start_x + logo_size + spacing
        logo_y = (VIDEO_HEIGHT - logo_size) // 2  # Calculate fixed Y position

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:size={VIDEO_WIDTH}x{VIDEO_HEIGHT}:duration={duration}",
            "-i",
            logo_path,
            "-filter_complex",
            f"[1:v]scale=-1:{logo_size},negate[logo];"
            f"[0:v][logo]overlay={logo_x}:{logo_y}[bg_with_logo];"
            f"[bg_with_logo]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{text}':fontcolor=white:fontsize=144:x={text_x}:y=(h-text_h)/2[with_title];"
            f"[with_title]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{subtitle}':fontcolor=gray:fontsize=36:x=(w-text_w)/2:y=(h+text_h)/2[out]",
            "-map",
            "[out]",
            "-r",
            str(FPS),
            "-pix_fmt",
            "yuv420p",
            output_path,
        ]
    else:
        # Without logo - original behavior
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:size={VIDEO_WIDTH}x{VIDEO_HEIGHT}:duration={duration}",
            "-vf",
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{text}':fontcolor=white:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/3,"
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
            f"text='{subtitle}':fontcolor=gray:fontsize=36:x=(w-text_w)/2:y=(h+text_h)/2",
            "-r",
            str(FPS),
            "-pix_fmt",
            "yuv420p",
            output_path,
        ]

    subprocess.run(cmd, check=True)


def get_video_info(video_path: str) -> Tuple[int, int, float]:
    """Get video dimensions and duration."""
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", video_path]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    import json

    data = json.loads(result.stdout)

    # Find video stream
    video_stream = None
    for stream in data["streams"]:
        if stream["codec_type"] == "video":
            video_stream = stream
            break

    if not video_stream:
        raise ValueError(f"No video stream found in {video_path}")

    width = int(video_stream["width"])
    height = int(video_stream["height"])
    duration = float(data["format"]["duration"])

    return width, height, duration


def resize_and_pad_video(input_path: str, output_path: str, target_duration: float, add_freeze: bool = True):
    """Resize video to fit target dimensions with padding and set duration."""
    # First get original video info
    orig_width, orig_height, orig_duration = get_video_info(input_path)

    # Calculate scaling to fit within target dimensions while maintaining aspect ratio
    scale_x = VIDEO_WIDTH / orig_width
    scale_y = VIDEO_HEIGHT / orig_height
    scale = min(scale_x, scale_y)

    new_width = int(orig_width * scale)
    new_height = int(orig_height * scale)

    # Ensure dimensions are even (required for some codecs)
    new_width = new_width - (new_width % 2)
    new_height = new_height - (new_height % 2)

    # Calculate padding
    pad_x = (VIDEO_WIDTH - new_width) // 2
    pad_y = (VIDEO_HEIGHT - new_height) // 2

    # Build ffmpeg command with optional freeze frame
    if add_freeze and orig_duration < target_duration:
        # Play video then freeze on last frame
        play_duration = min(orig_duration, target_duration - FREEZE_DURATION)
        freeze_duration = target_duration - play_duration

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-vf",
            f"scale={new_width}:{new_height}," f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:{pad_x}:{pad_y}:black",
            "-filter_complex",
            f"[0:v]trim=0:{play_duration}[play];[0:v]trim={max(0, orig_duration-0.1)}:{orig_duration},loop=loop=-1:size={int(freeze_duration*FPS)}[freeze];[play][freeze]concat=n=2:v=1:a=0[out]",
            "-map",
            "[out]",
            "-r",
            str(FPS),
            "-pix_fmt",
            "yuv420p",
            output_path,
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-vf",
            f"scale={new_width}:{new_height}," f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:{pad_x}:{pad_y}:black",
            "-t",
            str(target_duration),
            "-r",
            str(FPS),
            "-pix_fmt",
            "yuv420p",
            output_path,
        ]

    subprocess.run(cmd, check=True, capture_output=True)


def create_keyframe_conditioning_video(cond0_path: str, cond1_path: str, output_path: str, duration: float):
    """Create a conditioning video showing both keyframes for keyframe interpolation."""
    target_width = VIDEO_WIDTH // 2
    target_height = VIDEO_HEIGHT

    # Create a video that shows keyframe 0, then keyframe 1, then both together
    keyframe_display_time = duration / 3

    with tempfile.TemporaryDirectory() as temp_dir:
        # Process both keyframe images to videos
        kf0_video = os.path.join(temp_dir, "kf0.mp4")
        kf1_video = os.path.join(temp_dir, "kf1.mp4")
        both_video = os.path.join(temp_dir, "both.mp4")

        # Get dimensions for scaling
        orig_width, orig_height, _ = get_video_info(cond0_path)
        scale_x = target_width / orig_width
        scale_y = target_height / orig_height
        scale = min(scale_x, scale_y)

        new_width = int(orig_width * scale)
        new_height = int(orig_height * scale)
        new_width = new_width - (new_width % 2)
        new_height = new_height - (new_height % 2)

        pad_x = (target_width - new_width) // 2
        pad_y = (target_height - new_height) // 2

        # Create keyframe 0 video with "Keyframe 1" label
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                cond0_path,
                "-vf",
                f"scale={new_width}:{new_height},"
                f"pad={target_width}:{target_height}:{pad_x}:{pad_y}:black,"
                f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"text='Keyframe 1':fontcolor=white:fontsize=28:x=10:y=10:"
                f"box=1:boxcolor=black@0.8:boxborderw=5",
                "-t",
                str(keyframe_display_time),
                "-r",
                str(FPS),
                "-pix_fmt",
                "yuv420p",
                kf0_video,
            ],
            check=True,
            capture_output=True,
        )

        # Create keyframe 1 video with "Keyframe 2" label
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                cond1_path,
                "-vf",
                f"scale={new_width}:{new_height},"
                f"pad={target_width}:{target_height}:{pad_x}:{pad_y}:black,"
                f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"text='Keyframe 2':fontcolor=white:fontsize=28:x=10:y=10:"
                f"box=1:boxcolor=black@0.8:boxborderw=5",
                "-t",
                str(keyframe_display_time),
                "-r",
                str(FPS),
                "-pix_fmt",
                "yuv420p",
                kf1_video,
            ],
            check=True,
            capture_output=True,
        )

        # Create side-by-side keyframes video
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                cond0_path,
                "-i",
                cond1_path,
                "-filter_complex",
                f"[0:v]scale={new_width//2}:{new_height//2}[kf0_small];"
                f"[1:v]scale={new_width//2}:{new_height//2}[kf1_small];"
                f"[kf0_small][kf1_small]hstack=inputs=2[keyframes_side];"
                f"[keyframes_side]pad={target_width}:{target_height}:{pad_x}:{pad_y}:black,"
                f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"text='Both Keyframes':fontcolor=white:fontsize=28:x=10:y=10:"
                f"box=1:boxcolor=black@0.8:boxborderw=5[out]",
                "-map",
                "[out]",
                "-t",
                str(keyframe_display_time),
                "-r",
                str(FPS),
                "-pix_fmt",
                "yuv420p",
                both_video,
            ],
            check=True,
            capture_output=True,
        )

        # Concatenate all three parts
        concat_file = os.path.join(temp_dir, "concat.txt")
        with open(concat_file, "w") as f:
            f.write(f"file '{kf0_video}'\n")
            f.write(f"file '{kf1_video}'\n")
            f.write(f"file '{both_video}'\n")

        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", output_path],
            check=True,
            capture_output=True,
        )


def create_side_by_side_video(
    cond_path: str,
    gen_path: str,
    output_path: str,
    duration: float,
    label_cond: str = "Conditioning",
    label_gen: str = "Generated",
):
    """Create side-by-side video with conditioning on left, generated on right."""

    # Create temporary processed videos
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_cond = os.path.join(temp_dir, "cond_processed.mp4")
        temp_gen = os.path.join(temp_dir, "gen_processed.mp4")

        # Resize both videos to half width
        target_width = VIDEO_WIDTH // 2
        target_height = VIDEO_HEIGHT

        # Process conditioning video
        orig_width, orig_height, orig_duration = get_video_info(cond_path)
        scale_x = target_width / orig_width
        scale_y = target_height / orig_height
        scale = min(scale_x, scale_y)

        new_width = int(orig_width * scale)
        new_height = int(orig_height * scale)
        new_width = new_width - (new_width % 2)
        new_height = new_height - (new_height % 2)

        pad_x = (target_width - new_width) // 2
        pad_y = (target_height - new_height) // 2

        # Process conditioning video - simpler approach
        cmd_cond = [
            "ffmpeg",
            "-y",
            "-i",
            cond_path,
            "-vf",
            f"scale={new_width}:{new_height},"
            f"pad={target_width}:{target_height}:{pad_x}:{pad_y}:black,"
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{label_cond}':fontcolor=white:fontsize=32:x=10:y=10:"
            f"box=1:boxcolor=black@0.8:boxborderw=5",
            "-t",
            str(duration),
            "-r",
            str(FPS),
            "-pix_fmt",
            "yuv420p",
            temp_cond,
        ]

        # Process generated video
        orig_width, orig_height, orig_duration = get_video_info(gen_path)
        scale_x = target_width / orig_width
        scale_y = target_height / orig_height
        scale = min(scale_x, scale_y)

        new_width = int(orig_width * scale)
        new_height = int(orig_height * scale)
        new_width = new_width - (new_width % 2)
        new_height = new_height - (new_height % 2)

        pad_x = (target_width - new_width) // 2
        pad_y = (target_height - new_height) // 2

        # Process generated video - use full original duration, but limit to our target duration
        actual_duration = min(orig_duration, duration)
        cmd_gen = [
            "ffmpeg",
            "-y",
            "-i",
            gen_path,
            "-vf",
            f"scale={new_width}:{new_height},"
            f"pad={target_width}:{target_height}:{pad_x}:{pad_y}:black,"
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"text='{label_gen}':fontcolor=white:fontsize=32:x=10:y=10:"
            f"box=1:boxcolor=black@0.8:boxborderw=5",
            "-t",
            str(actual_duration),
            "-r",
            str(FPS),
            "-pix_fmt",
            "yuv420p",
            temp_gen,
        ]

        subprocess.run(cmd_cond, check=True, capture_output=True)
        subprocess.run(cmd_gen, check=True, capture_output=True)

        # Combine side by side
        cmd_combine = [
            "ffmpeg",
            "-y",
            "-i",
            temp_cond,
            "-i",
            temp_gen,
            "-filter_complex",
            "[0:v][1:v]hstack=inputs=2[v]",
            "-map",
            "[v]",
            "-r",
            str(FPS),
            "-pix_fmt",
            "yuv420p",
            output_path,
        ]

        subprocess.run(cmd_combine, check=True, capture_output=True)


def create_task_section(task_name: str, video_list: List[str], temp_dir: str) -> str:
    """Create a complete section for one task."""
    print(f"Creating section for {TASK_INFO[task_name]['name']}...")

    section_videos = []

    # Create title card
    title_path = os.path.join(temp_dir, f"{task_name}_title.mp4")
    create_title_card(TASK_INFO[task_name]["name"], TASK_INFO[task_name]["description"], TITLE_DURATION, title_path)
    section_videos.append(title_path)

    # Create video pairs
    for i, video_base in enumerate(video_list):
        cond_path = VIDEOS_DIR / f"{video_base}-cond.mp4"
        gen_path = VIDEOS_DIR / f"{video_base}-gen.mp4"

        if not cond_path.exists():
            print(f"Warning: {cond_path} not found, skipping...")
            continue
        if not gen_path.exists():
            print(f"Warning: {gen_path} not found, skipping...")
            continue

        pair_path = os.path.join(temp_dir, f"{task_name}_pair_{i:02d}.mp4")

        # Handle special case for keyframe interpolation
        if task_name == "keyframe_interp":
            # Check if separate keyframe files exist
            cond0_path = VIDEOS_DIR / f"{video_base}-cond0.mp4"
            cond1_path = VIDEOS_DIR / f"{video_base}-cond1.mp4"

            if cond0_path.exists() and cond1_path.exists():
                # Create special keyframe conditioning video
                keyframe_cond_path = os.path.join(temp_dir, f"keyframe_cond_{i}.mp4")
                create_keyframe_conditioning_video(
                    str(cond0_path), str(cond1_path), keyframe_cond_path, KEYFRAME_DURATION
                )
                create_side_by_side_video(
                    keyframe_cond_path, str(gen_path), pair_path, KEYFRAME_DURATION, "Keyframes", "Interpolated"
                )
            else:
                create_side_by_side_video(
                    str(cond_path), str(gen_path), pair_path, KEYFRAME_DURATION, "Conditioning", "Interpolated"
                )
        else:
            create_side_by_side_video(str(cond_path), str(gen_path), pair_path, VIDEO_DURATION)

        section_videos.append(pair_path)
        print(f"  Created pair {i+1}/{len(video_list)}")

    # Concatenate all videos in this section
    section_output = os.path.join(temp_dir, f"{task_name}_complete.mp4")

    if len(section_videos) == 1:
        # Just copy the single video
        subprocess.run(
            ["ffmpeg", "-y", "-i", section_videos[0], "-c", "copy", section_output], check=True, capture_output=True
        )
    else:
        # Create concat file
        concat_file = os.path.join(temp_dir, f"{task_name}_concat.txt")
        with open(concat_file, "w") as f:
            for video in section_videos:
                f.write(f"file '{video}'\n")

        # Concatenate
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", section_output],
            check=True,
            capture_output=True,
        )

    return section_output


def main():
    """Main function to create the compilation video."""

    # Check dependencies
    if not check_ffmpeg():
        print("Error: ffmpeg not found. Please install ffmpeg to use this script.")
        return

    print("Creating task compilation video...")
    print(f"Output will be saved to: {OUTPUT_PATH}")

    with tempfile.TemporaryDirectory() as temp_dir:
        all_sections = []

        # Create main title
        main_title_path = os.path.join(temp_dir, "main_title.mp4")
        logo_path = "static/images/logo.png"
        create_title_card(
            "OmniView",
            "",
            TITLE_DURATION * 1.5,
            main_title_path,
            logo_path,
        )
        all_sections.append(main_title_path)

        # Create each task section
        for task_name, video_list in TASK_VIDEOS.items():
            if not video_list:  # Skip empty task lists
                continue

            section_path = create_task_section(task_name, video_list, temp_dir)
            all_sections.append(section_path)

        # Create final compilation
        print("Creating final compilation...")

        if len(all_sections) == 1:
            subprocess.run(
                ["ffmpeg", "-y", "-i", all_sections[0], "-c", "copy", OUTPUT_PATH], check=True, capture_output=True
            )
        else:
            # Create final concat file
            final_concat = os.path.join(temp_dir, "final_concat.txt")
            with open(final_concat, "w") as f:
                for section in all_sections:
                    f.write(f"file '{section}'\n")

            # Create final video
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", final_concat, "-c", "copy", OUTPUT_PATH],
                check=True,
                capture_output=True,
            )

    print(f"✅ Compilation complete! Saved to: {OUTPUT_PATH}")

    # Print summary
    total_videos = sum(len(videos) for videos in TASK_VIDEOS.values())
    keyframe_videos = len(TASK_VIDEOS.get("keyframe_interp", []))
    regular_videos = total_videos - keyframe_videos
    total_duration = (
        TITLE_DURATION * 1.5  # Main title
        + len(TASK_VIDEOS) * TITLE_DURATION  # Task titles
        + regular_videos * VIDEO_DURATION  # Regular video pairs
        + keyframe_videos * KEYFRAME_DURATION
    )  # Keyframe interpolation pairs

    print(f"\nSummary:")
    print(f"  Tasks: {len(TASK_VIDEOS)}")
    print(f"  Total video pairs: {total_videos}")
    print(f"  Estimated duration: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")


if __name__ == "__main__":
    main()
