#!/usr/bin/env python3
"""
Self-contained script to generate complete index.html with all available demo videos.
No dependencies on existing HTML files - generates everything from scratch.
"""

# List of videos to include (edit this list to exclude videos)
# Format: "filename_without_extension" (e.g., "video_nvs_01" will include both video_nvs_01-cond.mp4 and video_nvs_01-gen.mp4)
INCLUDED_VIDEOS = [
    # Video Novel View Synthesis (01-71)
    "video_nvs_43",
    "video_nvs_12",
    "video_nvs_34",
    "video_nvs_26",
    "video_nvs_38",
    "video_nvs_40",
    "video_nvs_66",
    "video_nvs_47",
    "video_nvs_19",
    "video_nvs_23",
    "video_nvs_01",
    "video_nvs_19",
    "video_nvs_36",
    "video_nvs_46",
    "video_nvs_55",
    "video_nvs_56",
    "video_nvs_60",
    "video_nvs_62",
    "video_nvs_67",
    "video_nvs_69",
    "video_nvs_71",
    # Static Novel View Synthesis (01-15, 17 - note: 16 missing)
    "static_nvs_01",
    "static_nvs_03",
    "static_nvs_12",
    "static_nvs_15",
    "static_nvs_17",
    # Image-to-Video Generation (01-26)
    "i2v_22",
    "i2v_01",
    "i2v_03",
    "i2v_09",
    "i2v_15",
    "i2v_18",
    # Video-to-Video (01-06, 15-16)
    "v2v_01",
    "v2v_02",
    # Keyframe Interpolation (01-13, 18, 20 - note: some have cond0/cond1, others only cond)
    "keyframe_interp_05",
    "keyframe_interp_06",
]

import os
import re
from collections import defaultdict
from pathlib import Path


def scan_videos(demos_dir):
    """Scan the demos directory and categorize videos."""
    videos = defaultdict(list)

    for video_file in sorted(Path(demos_dir).glob("*.mp4")):
        filename = video_file.name

        # Extract source prefix for grouping
        source_prefix = None

        # Video Novel View Synthesis
        if match := re.match(r"video_nvs_(\d+)-(cond|gen)\.mp4", filename):
            num, type_ = match.groups()
            source_prefix = f"video_nvs_{num}"
            # Only include if in the INCLUDED_VIDEOS list
            if source_prefix in INCLUDED_VIDEOS:
                videos["video_nvs"].append((int(num), type_, filename, source_prefix))

        # Static Novel View Synthesis
        elif match := re.match(r"static_nvs_(\d+)-(cond|gen)\.mp4", filename):
            num, type_ = match.groups()
            source_prefix = f"static_nvs_{num}"
            # Only include if in the INCLUDED_VIDEOS list
            if source_prefix in INCLUDED_VIDEOS:
                videos["static_nvs"].append((int(num), type_, filename, source_prefix))

        # Image-to-Video Generation
        elif match := re.match(r"i2v_(\d+)-(cond|gen)\.mp4", filename):
            num, type_ = match.groups()
            source_prefix = f"i2v_{num}"
            # Only include if in the INCLUDED_VIDEOS list
            if source_prefix in INCLUDED_VIDEOS:
                videos["i2v"].append((int(num), type_, filename, source_prefix))

        # Video-to-Video
        elif match := re.match(r"v2v_(\d+)-(cond|gen)\.mp4", filename):
            num, type_ = match.groups()
            source_prefix = f"v2v_{num}"
            # Only include if in the INCLUDED_VIDEOS list
            if source_prefix in INCLUDED_VIDEOS:
                videos["v2v"].append((int(num), type_, filename, source_prefix))

        # Keyframe Interpolation (more complex patterns)
        elif match := re.match(r"keyframe_interp_(\d+)-(cond|gen|cond0|cond1)\.mp4", filename):
            num, type_ = match.groups()
            source_prefix = f"keyframe_interp_{num}"
            # Only include if in the INCLUDED_VIDEOS list
            if source_prefix in INCLUDED_VIDEOS:
                videos["keyframe_interp"].append((int(num), type_, filename, source_prefix))

    return videos


def group_video_pairs(video_list):
    """Group videos by source prefix into sets of 2 pairs (4 videos total) for 2x2 display."""
    grouped = defaultdict(dict)

    for num, type_, filename, source_prefix in video_list:
        grouped[source_prefix][type_] = filename

    # Filter to only include complete pairs (both cond and gen) and preserve INCLUDED_VIDEOS order
    complete_pairs = []
    for source_prefix in INCLUDED_VIDEOS:
        if source_prefix in grouped and "cond" in grouped[source_prefix] and "gen" in grouped[source_prefix]:
            complete_pairs.append((source_prefix, grouped[source_prefix]))

    # Group into sets of 2 pairs (showing 4 videos: 2 cond + 2 gen in 2x2 grid)
    grouped_sets = []
    for i in range(0, len(complete_pairs), 2):
        batch = complete_pairs[i : i + 2]
        grouped_sets.append(batch)

    return grouped_sets


def group_keyframe_videos(video_list):
    """Group keyframe videos by source prefix into sets of 2 pairs for 2x2 display."""
    grouped = defaultdict(dict)

    for num, type_, filename, source_prefix in video_list:
        grouped[source_prefix][type_] = filename

    # Filter to include sets with at least cond and gen and preserve INCLUDED_VIDEOS order
    complete_sets = []
    for source_prefix in INCLUDED_VIDEOS:
        if (
            source_prefix in grouped
            and "gen" in grouped[source_prefix]
            and (
                "cond" in grouped[source_prefix]
                or ("cond0" in grouped[source_prefix] and "cond1" in grouped[source_prefix])
            )
        ):
            complete_sets.append((source_prefix, grouped[source_prefix]))

    # Group into sets of 2 pairs (showing keyframe components in 2x2 grid)
    grouped_sets = []
    for i in range(0, len(complete_sets), 2):
        batch = complete_sets[i : i + 2]
        grouped_sets.append(batch)

    return grouped_sets


def generate_carousel_wrapper_start(section_id, grouped_sets):
    """Generate opening carousel container with left arrow."""
    if len(grouped_sets) <= 1:
        return '          <div class="carousel-content">\n'  # No arrows for single slide

    html = f'          <div class="carousel-container">\n'
    html += (
        f'            <button class="carousel-arrow prev-arrow" data-section="{section_id}" data-direction="prev">\n'
    )
    html += f'              <i class="fas fa-chevron-left"></i>\n'
    html += f"            </button>\n"
    html += f'            <div class="carousel-content">\n'

    return html


def generate_carousel_wrapper_end(section_id, grouped_sets):
    """Generate closing carousel container with right arrow."""
    if len(grouped_sets) <= 1:
        return "          </div>\n"  # No arrows for single slide

    html = f"            </div>\n"
    html += (
        f'            <button class="carousel-arrow next-arrow" data-section="{section_id}" data-direction="next">\n'
    )
    html += f'              <i class="fas fa-chevron-right"></i>\n'
    html += f"            </button>\n"
    html += f"          </div>\n"

    return html


def generate_slide_contents(grouped_sets, is_keyframe=False):
    """Generate slide content for batches of videos."""
    html = ""

    for i, batch in enumerate(grouped_sets):
        display_style = "block" if i == 0 else "none"

        html += f"          <!-- Slide {i} -->\n"
        html += f'          <div class="slide-content" data-slide="{i}" style="display: {display_style};" role="tabpanel">\n'

        if len(batch) >= 2:
            # Show 2 complete pairs in 2x2 grid (or fewer if less available)
            pairs_to_show = min(2, len(batch))
            grid_class = "keyframe-demo-grid" if is_keyframe else "demo-video-grid"
            html += f'            <div class="{grid_class}">\n'

            # Add titles only once for the entire grid
            if is_keyframe and len(batch) > 0 and "cond0" in batch[0][1] and "cond1" in batch[0][1]:
                # Keyframe case: show titles for keyframe layout with first keyframe, generated, and last keyframe
                html += '              <div class="demo-video-pair">\n'
                html += '                <div class="video-label">First Keyframe</div>\n'
                html += f'                <video class="demo-video" src="static/videos/demos/{batch[0][1]["cond0"]}" autoplay loop muted></video>\n'
                html += "              </div>\n"
                html += '              <div class="demo-video-pair">\n'
                html += '                <div class="video-label">Generated</div>\n'
                html += f'                <video class="demo-video" src="static/videos/demos/{batch[0][1]["gen"]}" autoplay loop muted></video>\n'
                html += "              </div>\n"
                html += '              <div class="demo-video-pair">\n'
                html += '                <div class="video-label">Last Keyframe</div>\n'
                html += f'                <video class="demo-video" src="static/videos/demos/{batch[0][1]["cond1"]}" autoplay loop muted></video>\n'
                html += "              </div>\n"
                if len(batch) > 1:
                    html += '              <div class="demo-video-pair">\n'
                    html += f'                <video class="demo-video" src="static/videos/demos/{batch[1][1]["cond0"]}" autoplay loop muted></video>\n'
                    html += "              </div>\n"
                    html += '              <div class="demo-video-pair">\n'
                    html += f'                <video class="demo-video" src="static/videos/demos/{batch[1][1]["gen"]}" autoplay loop muted></video>\n'
                    html += "              </div>\n"
                    html += '              <div class="demo-video-pair">\n'
                    html += f'                <video class="demo-video" src="static/videos/demos/{batch[1][1]["cond1"]}" autoplay loop muted></video>\n'
                    html += "              </div>\n"
            else:
                # Regular case: show conditioning and generated titles only once
                html += '              <div class="demo-video-pair">\n'
                html += '                <div class="video-label">Conditioning</div>\n'
                html += f'                <video class="demo-video" src="static/videos/demos/{batch[0][1]["cond"]}" autoplay loop muted></video>\n'
                html += "              </div>\n"
                html += '              <div class="demo-video-pair">\n'
                html += '                <div class="video-label">Generated</div>\n'
                html += f'                <video class="demo-video" src="static/videos/demos/{batch[0][1]["gen"]}" autoplay loop muted></video>\n'
                html += "              </div>\n"
                if len(batch) > 1:
                    # Second pair without titles
                    html += '              <div class="demo-video-pair">\n'
                    html += f'                <video class="demo-video" src="static/videos/demos/{batch[1][1]["cond"]}" autoplay loop muted></video>\n'
                    html += "              </div>\n"
                    html += '              <div class="demo-video-pair">\n'
                    html += f'                <video class="demo-video" src="static/videos/demos/{batch[1][1]["gen"]}" autoplay loop muted></video>\n'
                    html += "              </div>\n"

            html += "            </div>\n"
        else:
            # Single row layout for fewer than 2 pairs
            html += '            <div class="demo-video-row">\n'

            # Add titles only for the first pair
            for idx, (source_prefix, files) in enumerate(batch):
                if is_keyframe and "cond0" in files and "cond1" in files:
                    if idx == 0:
                        # Show all keyframe components with titles for first pair
                        html += '              <div class="demo-video-pair">\n'
                        html += '                <div class="video-label">First Keyframe</div>\n'
                        html += f'                <video class="demo-video" src="static/videos/demos/{files["cond0"]}" autoplay loop muted></video>\n'
                        html += "              </div>\n"
                        html += '              <div class="demo-video-pair">\n'
                        html += '                <div class="video-label">Generated</div>\n'
                        html += f'                <video class="demo-video" src="static/videos/demos/{files["gen"]}" autoplay loop muted></video>\n'
                        html += "              </div>\n"
                        html += '              <div class="demo-video-pair">\n'
                        html += '                <div class="video-label">Last Keyframe</div>\n'
                        html += f'                <video class="demo-video" src="static/videos/demos/{files["cond1"]}" autoplay loop muted></video>\n'
                        html += "              </div>\n"
                elif "cond" in files:
                    if idx == 0:
                        # Show conditioning and generated with titles for first pair
                        html += '              <div class="demo-video-pair">\n'
                        html += '                <div class="video-label">Conditioning</div>\n'
                        html += f'                <video class="demo-video" src="static/videos/demos/{files["cond"]}" autoplay loop muted></video>\n'
                        html += "              </div>\n"
                        html += '              <div class="demo-video-pair">\n'
                        html += '                <div class="video-label">Generated</div>\n'
                        html += f'                <video class="demo-video" src="static/videos/demos/{files["gen"]}" autoplay loop muted></video>\n'
                        html += "              </div>\n"
                    else:
                        # Show without titles for additional pairs
                        html += '              <div class="demo-video-pair">\n'
                        html += f'                <video class="demo-video" src="static/videos/demos/{files["cond"]}" autoplay loop muted></video>\n'
                        html += "              </div>\n"
                        html += '              <div class="demo-video-pair">\n'
                        html += f'                <video class="demo-video" src="static/videos/demos/{files["gen"]}" autoplay loop muted></video>\n'
                        html += "              </div>\n"

            html += "            </div>\n"

        html += "          </div>\n\n"

    return html


def generate_section(title, description, section_id, grouped_sets, is_keyframe=False):
    """Generate a complete section with slides."""
    if not grouped_sets:
        return ""

    html = f"""  <section class="section demo-section">
    <div class="container is-max-desktop">
      <div class="columns is-centered has-text-centered">
        <div class="column is-full-width">
          <h2 class="title is-3">{title}</h2>
          <div class="content has-text-justified">
            <p>{description}</p>
          </div>
          
{generate_carousel_wrapper_start(section_id, grouped_sets)}{generate_slide_contents(grouped_sets, is_keyframe)}{generate_carousel_wrapper_end(section_id, grouped_sets)}        </div>
      </div>
    </div>
  </section>
"""
    return html


def generate_html_head():
    """Generate the complete HTML head section."""
    return """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="description" content="OmniView: An All-Seeing Diffusion Model for 3D and 4D View Synthesis">
  <meta property="og:title" content="OmniView: An All-Seeing Diffusion Model for 3D and 4D View Synthesis" />
  <meta property="og:description" content="We introduce OmniView, a unified framework that generalizes across a wide range of 4D consistency tasks." />
  <meta property="og:url" content="https://omniview-video.github.io/" />
  <meta name="viewport" content="width=device-width, initial-scale=1">
  
  <title>OmniView: An All-Seeing Diffusion Model for 3D and 4D View Synthesis</title>
  <link href="https://fonts.googleapis.com/css?family=Google+Sans|Noto+Sans|Castoro" rel="stylesheet">
  <link rel="stylesheet" href="static/css/bulma.min.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/jpswalsh/academicons@1/css/academicons.min.css">
  <link rel="stylesheet" href="static/css/index.css">
  
  <style>
    .carousel-container {
      position: relative;
      width: 100%;
      max-width: 900px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      gap: 20px;
    }
    
    .carousel-content {
      flex: 1;
      display: flex;
      justify-content: center;
    }
    
    .carousel-arrow {
      background: #1772d0;
      color: white;
      border: none;
      border-radius: 50%;
      width: 50px;
      height: 50px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 18px;
      transition: all 0.3s ease;
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
      flex-shrink: 0;
    }
    
    .carousel-arrow:hover {
      background: #0d5aa7;
      box-shadow: 0 4px 12px rgba(0,0,0,0.25);
      transform: scale(1.05);
    }
    
    .carousel-arrow:disabled {
      background: #e0e0e0;
      color: #999;
      cursor: not-allowed;
      box-shadow: none;
      transform: none;
    }
    
    .demo-video-row {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 20px;
      flex-wrap: wrap;
    }
    
    .slide-content {
      margin: 20px 0 40px 0;
      width: 100%;
    }
    
    .demo-video-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr 1fr;
      gap: 20px;
      justify-items: center;
      align-items: center;
      max-width: 640px;
      margin: 0 auto;
    }
    
    .keyframe-demo-grid {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      grid-template-rows: 1fr 1fr;
      gap: 20px;
      justify-items: center;
      align-items: center;
      max-width: 900px;
      margin: 0 auto;
    }
    
    .demo-video-pair, .demo-video-triple {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
      width: 100%;
    }
    
    .keyframe-grid {
      display: grid;
      grid-template-columns: 1fr 2fr 1fr;
      gap: 15px;
      justify-items: center;
      align-items: center;
      max-width: 800px;
      margin: 0 auto;
    }
    
    .demo-video {
      width: 280px;
      height: 158px;
      border: 1px solid #ddd;
      border-radius: 8px;
    }
    
    .keyframe-video {
      width: 200px;
      height: 112px;
      border: 1px solid #ddd;
      border-radius: 8px;
    }
    
    .video-label {
      text-align: center;
      font-size: 14px;
      font-weight: bold;
      margin-bottom: 5px;
    }
    
    /* Responsive design for smaller screens */
    @media (max-width: 768px) {
      .carousel-container {
        flex-direction: column;
        gap: 15px;
      }
      
      .carousel-content {
        order: 1;
      }
      
      .prev-arrow {
        order: 0;
      }
      
      .next-arrow {
        order: 2;
      }
      
      .carousel-arrow {
        width: 40px;
        height: 40px;
        font-size: 16px;
      }
    }
  </style>
</head>"""


def generate_html_header():
    """Generate the page header and navigation."""
    return """<body>
  <section class="hero">
    <div class="hero-body">
      <div class="container is-max-desktop">
        <div class="columns is-centered">
          <div class="column has-text-centered">
            <h1 class="title is-1 publication-title">
              <img width="36" height="36" src="static/images/logo.png" />
              OmniView: An All-Seeing Diffusion Model for 3D and 4D View Synthesis
            </h1>
            <div class="is-size-5 publication-authors">
              <span class="author-block"><a href="https://xiangfan.io/" target="_blank">Xiang Fan</a><sup>1 2</sup>,</span>
              <span class="author-block"><a href="" target="_blank">Sharath Girish</a><sup>2</sup>,</span>
              <span class="author-block"><a href="" target="_blank">Vivek Ramanujan</a><sup>1</sup>,</span>
              <span class="author-block"><a href="" target="_blank">Chaoyang Wang</a><sup>2</sup>,</span>
              <span class="author-block"><a href="" target="_blank">Ashkan Mirzaei</a><sup>2</sup>,</span>
              <span class="author-block"><a href="" target="_blank">Petr Sushko</a><sup>1</sup>,</span>
              <span class="author-block"><a href="" target="_blank">Aliaksandr Siarohin</a><sup>2</sup>,</span>
              <span class="author-block"><a href="" target="_blank">Sergey Tulyakov</a><sup>2</sup>,</span>
              <span class="author-block"><a href="https://www.ranjaykrishna.com/" target="_blank">Ranjay Krishna</a><sup>1</sup></span>
            </div>
            <div class="is-size-5 publication-authors">
              <span class="author-block"><sup>1</sup>University of Washington, <sup>2</sup>Snap Inc.</span>
            </div>
            <div class="column has-text-centered">
              <div class="publication-links">
                <span class="link-block">
                  <a href="#" target="_blank" class="external-link button is-normal is-rounded is-dark">
                    <span class="icon"><i class="fas fa-file-pdf"></i></span>
                    <span>Paper (Coming Soon)</span>
                  </a>
                </span>
                <span class="link-block">
                  <a href="https://github.com/omniview-video/omniview" target="_blank" class="external-link button is-normal is-rounded is-dark">
                    <span class="icon"><i class="fab fa-github"></i></span>
                    <span>Code (Coming Soon)</span>
                  </a>
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="section hero is-light">
    <div class="container is-max-desktop">
      <div class="columns is-centered has-text-centered">
        <div class="column is-four-fifths">
          <h2 class="title is-3">Abstract</h2>
          <div class="content has-text-justified">
            <p>
              Prior approaches injecting camera control into diffusion models have focused on specific subsets of 4D
              consistency tasks: novel view synthesis, text-to-video with camera control, image-to-video, amongst
              others. Therefore, these fragmented approaches are trained on disjoint slices of available 3D/4D data. We
              introduce OmniView, a unified framework that generalizes across a wide range of 4D consistency tasks. Our
              method separately represents space, time, and view conditions, enabling flexible combinations of these
              inputs. For example, OmniView can synthesize novel views from static, dynamic, and multiview inputs,
              extrapolate trajectories forward and backward in time, and create videos from text or image prompts with
              full camera control. OmniView is competitive with task-specific models across diverse benchmarks and
              metrics, improving image quality scores among camera-conditioned diffusion models by up to 33% in
              multiview NVS LLFF dataset, 60% in dynamic NVS Neural 3D Video benchmark, 20% in static camera control on
              RE-10K, and reducing camera trajectory errors by 4x in text-conditioned video generation. With strong
              generalizability in one model, OmniView demonstrates the feasibility of a generalist 4D video model.
            </p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="section">
    <div class="container is-max-desktop">
      <div class="columns is-centered has-text-centered">
        <div class="column is-four-fifths">
          <h2 class="title is-3">Teaser</h2>
          <div class="content has-text-justified">
            <p>
              Watch our comprehensive demonstration showcasing OmniView's capabilities across all supported tasks. 
              This video presents conditioning inputs alongside generated results for dynamic novel view synthesis, 
              static novel view synthesis, image-to-video generation, keyframe interpolation, and video-to-video translation.
            </p>
          </div>
          <div class="columns is-centered">
            <div class="column is-full-width">
              <video class="teaser-video" controls style="width: 100%; max-width: 800px; height: auto; border-radius: 8px;">
                <source src="static/videos/teaser.mp4" type="video/mp4">
                Your browser does not support the video tag.
              </video>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>"""


def generate_html_footer():
    """Generate the page footer."""
    return """
  <footer class="footer">
    <div class="container">
      <div class="content has-text-centered">
        <a class="icon-link" href="https://github.com/omniview-video/omniview" target="_blank">
          <i class="fab fa-github"></i>
        </a>
      </div>
      <div class="columns is-centered">
        <div class="column is-8">
          <div class="content">
            <p>
              This website is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.
            </p>
            <p>
              This means you are free to borrow the <a href="https://github.com/nerfies/nerfies.github.io">source code</a> of this website,
              we just ask that you link back to this page in the footer.
              Please remember to remove the analytics code included in the header of the website which you do not want on your website.
            </p>
          </div>
        </div>
      </div>
    </div>
  </footer>

  <script>
    document.addEventListener('DOMContentLoaded', function() {
      // Arrow-based carousel functionality
      const sections = document.querySelectorAll('.demo-section');
      
      sections.forEach(section => {
        const slides = section.querySelectorAll('.slide-content');
        const prevArrow = section.querySelector('.prev-arrow');
        const nextArrow = section.querySelector('.next-arrow');
        
        if (!slides.length || (!prevArrow && !nextArrow)) {
          return; // Skip sections without slides or arrows
        }
        
        let currentSlide = 0;
        const totalSlides = slides.length;
        
        // Function to show specific slide
        function showSlide(index) {
          // Hide all slides
          slides.forEach((slide, slideIndex) => {
            if (slideIndex === index) {
              slide.style.display = 'block';
              const videos = slide.querySelectorAll('video');
              videos.forEach(v => {
                v.currentTime = 0;
                v.play().catch(() => {});
              });
            } else {
              slide.style.display = 'none';
              const videos = slide.querySelectorAll('video');
              videos.forEach(v => v.pause());
            }
          });
          
          // Update arrow states
          if (prevArrow) {
            prevArrow.disabled = (index === 0);
          }
          if (nextArrow) {
            nextArrow.disabled = (index === totalSlides - 1);
          }
        }
        
        // Arrow click handlers
        if (prevArrow) {
          prevArrow.addEventListener('click', () => {
            if (currentSlide > 0) {
              currentSlide--;
              showSlide(currentSlide);
            }
          });
        }
        
        if (nextArrow) {
          nextArrow.addEventListener('click', () => {
            if (currentSlide < totalSlides - 1) {
              currentSlide++;
              showSlide(currentSlide);
            }
          });
        }
        
        // Keyboard navigation
        section.addEventListener('keydown', (e) => {
          if (e.key === 'ArrowLeft' && currentSlide > 0) {
            currentSlide--;
            showSlide(currentSlide);
            e.preventDefault();
          } else if (e.key === 'ArrowRight' && currentSlide < totalSlides - 1) {
            currentSlide++;
            showSlide(currentSlide);
            e.preventDefault();
          }
        });
        
        // Make section focusable for keyboard navigation
        section.setAttribute('tabindex', '0');
        
        // Initialize first slide
        showSlide(0);
      });
    });
  </script>
</body>
</html>"""


def generate_complete_html(videos):
    """Generate the complete HTML file from scratch."""
    # Process each video category into grouped sets
    video_nvs_sets = group_video_pairs(videos["video_nvs"])
    static_nvs_sets = group_video_pairs(videos["static_nvs"])
    i2v_sets = group_video_pairs(videos["i2v"])
    v2v_sets = group_video_pairs(videos["v2v"])
    keyframe_sets = group_keyframe_videos(videos["keyframe_interp"])

    # Start with HTML head
    html = generate_html_head()

    # Add header
    html += generate_html_header()

    # Generate demo sections
    if video_nvs_sets:
        html += generate_section(
            "Dynamic Novel View Synthesis",
            "Camera-controlled video synthesis from input video. Given a video sequence captured from one viewpoint, our model generates the same scene from novel camera perspectives while preserving temporal dynamics. This task requires maintaining 3D consistency across viewpoints and temporal coherence across frames, ensuring that moving objects and camera motion are properly disentangled and rendered from new angles.",
            "video-nvs",
            video_nvs_sets,
        )

    if static_nvs_sets:
        html += generate_section(
            "Play and Freeze Time",
            "A unique capability where temporal and spatial controls are seamlessly combined. The video initially plays forward in time, then freezes at a specific moment while the camera moves to explore the scene from different viewpoints, and finally resumes temporal progression. This demonstrates our model's ability to decouple time and space, allowing independent control over when and where to observe the scene.",
            "static-nvs",
            static_nvs_sets,
        )

    if i2v_sets:
        html += generate_section(
            "Image-to-Video Generation w/ Camera Control",
            "Transform static images into dynamic videos with full camera control. Starting from a single input image, our model generates temporal dynamics while simultaneously allowing camera movement through the scene. This task requires hallucinating plausible 3D structure from 2D observations and animating the scene with realistic object motion, lighting changes, and camera trajectories.",
            "i2v",
            i2v_sets,
        )

    if v2v_sets:
        html += generate_section(
            "Video-to-Video Generation w/ Camera Control",
            "Extend short video clips into longer sequences with camera control. Given an input video segment, our model predicts future frames while allowing the camera trajectory to be specified independently. This enables creative control over both the temporal evolution of the scene and the viewing perspective, useful for applications like cinematography and content creation where specific camera movements are desired.",
            "v2v",
            v2v_sets,
        )

    if keyframe_sets:
        html += generate_section(
            "Keyframe Interpolation",
            "Generate smooth video sequences between specified keyframe images with camera control. Given two or more keyframe images that define the start and end states, our model creates natural temporal transitions while maintaining 3D consistency. This is particularly useful for animation workflows where artists specify key poses or states, and the model fills in the intermediate frames with realistic motion and camera movement.",
            "keyframe-interp",
            keyframe_sets,
            is_keyframe=True,
        )

    # Add method section
    html += """
  <section class="section hero is-light">
    <div class="container is-max-desktop">
      <div class="columns is-centered has-text-centered">
        <div class="column is-full-width">
          <h2 class="title is-3">Method</h2>
          <div class="content has-text-justified">
            <p>
              Our approach unifies multiple 4D consistency tasks through a shared framework that separately models space, time, and camera viewpoint conditions.
            </p>
          </div>
          <div class="columns is-centered">
            <div class="column is-full-width">
              <img src="static/images/method.png" alt="OmniView method overview" style="max-width: 100%; height: auto;">
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
"""

    # Add citation section
    html += """
  <section class="section">
    <div class="container is-max-desktop">
      <div class="columns is-centered">
        <div class="column is-four-fifths">
          <h2 class="title is-3 has-text-centered">Citation</h2>
          <div class="content">
            <pre style="text-align: left;"><code>@article{fan2025omniview,
  title={OmniView: An All-Seeing Diffusion Model for 3D and 4D View Synthesis},
  author={Fan, Xiang and Girish, Sharath and Ramanujan, Vivek and Wang, Chaoyang and Mirzaei, Ashkan and Sushko, Petr and Siarohin, Aliaksandr and Tulyakov, Sergey and Krishna, Ranjay},
  journal={arXiv preprint},
  year={2025}
}</code></pre>
          </div>
        </div>
      </div>
    </div>
  </section>
"""

    # Add footer
    html += generate_html_footer()

    return html


def main():
    """Main function."""
    demos_dir = "static/videos/demos"

    if not os.path.exists(demos_dir):
        print(f"Error: Directory {demos_dir} not found!")
        return

    print("Scanning video files...")
    videos = scan_videos(demos_dir)

    # Print statistics
    for category, video_list in videos.items():
        if category == "keyframe_interp":
            sets = group_keyframe_videos(video_list)
        else:
            sets = group_video_pairs(video_list)
        total_videos = sum(len(batch) for batch in sets)
        print(f"{category}: {len(sets)} slide groups containing {total_videos} video pairs")

    print("\nGenerating complete HTML from scratch...")
    html_content = generate_complete_html(videos)

    # Backup existing file if it exists
    if os.path.exists("index.html"):
        os.rename("index.html", "index.html.backup")
        print("Backed up existing index.html to index.html.backup")

    # Write new file
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print("Generated complete index.html with clean carousel functionality!")


if __name__ == "__main__":
    main()
