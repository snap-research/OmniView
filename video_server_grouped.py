#!/usr/bin/env python3
"""
Video Groups Viewer Server

This server provides a web interface to browse videos in grouped sets.
Each group contains: original.video.mp4, generated.video.mp4, and cond_*.video.mp4
"""

import argparse
import json
import logging
import mimetypes
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("/tmp/video_server.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Global cache for video groups - scan only once at startup
_global_video_groups_cache = None
_global_scan_completed = False


class VideoGroupsHandler(BaseHTTPRequestHandler):

    def __init__(self, *args, video_root=None, **kwargs):
        self.video_root = (
            Path(video_root)
            if video_root
            else Path(
                "/nfs/xfan/object_permanence_data/demo_query_diffusion_model-exp0923-4-1-step030000-test_vids-v3/wods2"
            )
        )
        logger.info(f"Initializing handler with video_root: {self.video_root}")
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests for web pages and video files"""
        path = self.path.split("?")[0]  # Remove query parameters
        path = unquote(path)  # Decode URL encoding

        logger.info(f"GET {path} from {self.client_address[0]}")

        if path == "/" or path == "/index.html":
            self.serve_index()
        elif path == "/api/groups":
            self.serve_video_groups()
        elif path.startswith("/video/"):
            self.serve_video_file(path[7:])  # Remove '/video/' prefix
        else:
            logger.warning(f"404 Not Found: {path}")
            self.send_error(404, "File not found")

    def serve_index(self):
        """Serve the main HTML page"""
        html_content = self._get_html_content()

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(len(html_content)))
        self.end_headers()
        self.wfile.write(html_content.encode("utf-8"))

    def _get_html_content(self):
        """Get the complete HTML content as a string"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Groups Viewer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .controls {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
            display: flex;
            gap: 1rem;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .search-input {
            flex: 1;
            min-width: 200px;
            padding: 0.75rem;
            border: 2px solid #e1e5e9;
            border-radius: 4px;
            font-size: 1rem;
        }
        
        .search-input:focus { outline: none; border-color: #667eea; }
        
        .per-page-select {
            padding: 0.75rem;
            border: 2px solid #e1e5e9;
            border-radius: 4px;
            font-size: 1rem;
        }
        
        .status {
            color: #666;
            font-size: 0.9rem;
        }
        
        .video-groups {
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }
        
        .video-group {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .group-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 0.5rem;
            word-break: break-all;
        }
        
        .group-videos {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 1rem;
        }
        
        @media (max-width: 1200px) {
            .group-videos {
                grid-template-columns: 1fr;
            }
        }
        
        .video-item {
            display: flex;
            flex-direction: column;
        }
        
        .video-label {
            font-weight: 500;
            margin-bottom: 0.5rem;
            color: #555;
            text-align: center;
            padding: 0.25rem;
            background: #f8f9fa;
            border-radius: 4px;
        }
        
        .video-container {
            position: relative;
            width: 100%;
            height: 200px;
            background: #000;
            border-radius: 4px;
            overflow: hidden;
        }
        
        video {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .video-placeholder {
            width: 100%;
            height: 100%;
            background: #f0f0f0;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #999;
            font-style: italic;
        }
        
        .loading {
            text-align: center;
            padding: 2rem;
            color: #666;
        }

        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 1rem;
            margin: 2rem 0;
            padding: 1rem;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .pagination button {
            background: #667eea;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 1rem;
            transition: background 0.2s;
        }

        .pagination button:hover:not(:disabled) {
            background: #5a6fd8;
        }

        .pagination button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }

        #page-info {
            font-weight: 500;
            color: #333;
            margin: 0 1rem;
        }

        .page-jump {
            display: flex;
            align-items: center;
            margin-left: 1rem;
            padding-left: 1rem;
            border-left: 1px solid #ddd;
        }

        .page-jump span {
            color: #666;
            font-size: 0.9rem;
        }

        .page-jump button {
            background: #28a745;
            color: white;
            border: none;
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: background 0.2s;
        }

        .page-jump button:hover {
            background: #218838;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎬 Video Groups Viewer</h1>
        <p>Grouped video comparison: Original, Generated, and Conditioned</p>
    </div>

    <div class="container">
        <div class="controls">
            <input type="text" id="search-input" class="search-input" placeholder="Search groups...">
            <select id="per-page-select" class="per-page-select">
                <option value="5">5 groups per page</option>
                <option value="10" selected>10 groups per page</option>
                <option value="20">20 groups per page</option>
                <option value="50">50 groups per page</option>
            </select>
            <div class="status" id="status">Loading...</div>
        </div>

        <div id="video-groups" class="video-groups">
            <div class="loading">Loading video groups...</div>
        </div>

        <div class="pagination" id="pagination" style="display: none;">
            <button id="prev-btn" onclick="changePage(-1)" disabled>← Previous</button>
            <span id="page-info">Page 1 of 1</span>
            <button id="next-btn" onclick="changePage(1)" disabled>Next →</button>
            <div class="page-jump">
                <span>Go to page:</span>
                <input type="number" id="page-jump-input" min="1" max="1" value="1" style="width: 60px; margin: 0 0.5rem; padding: 0.25rem; border: 1px solid #ccc; border-radius: 4px; text-align: center;">
                <button id="page-jump-btn" onclick="jumpToPage()">Go</button>
            </div>
        </div>
    </div>

    <script>
        let allGroups = [];
        let filteredGroups = [];
        let currentPage = 1;
        let groupsPerPage = 10;
        
        async function loadGroups() {
            try {
                document.getElementById('status').textContent = 'Loading groups...';
                
                const response = await fetch('/api/groups');
                const data = await response.json();
                
                allGroups = data.groups;
                filteredGroups = [...allGroups];
                
                document.getElementById('status').textContent = `${allGroups.length} groups found`;
                
                filterAndRender();
            } catch (error) {
                console.error('Error loading groups:', error);
                document.getElementById('video-groups').innerHTML = 
                    '<div class="loading">Error loading groups: ' + error.message + '</div>';
                document.getElementById('status').textContent = 'Error loading groups';
            }
        }
        
        function filterGroups() {
            const searchTerm = document.getElementById('search-input').value.toLowerCase();
            
            if (!searchTerm) {
                filteredGroups = [...allGroups];
            } else {
                filteredGroups = allGroups.filter(group => 
                    group.name.toLowerCase().includes(searchTerm)
                );
            }
            
            document.getElementById('status').textContent = `${filteredGroups.length} groups found`;
            currentPage = 1;
        }
        
        function renderGroups() {
            const container = document.getElementById('video-groups');
            
            if (filteredGroups.length === 0) {
                container.innerHTML = '<div class="loading">No groups found.</div>';
                updatePagination(0, 0);
                return;
            }
            
            const totalPages = Math.ceil(filteredGroups.length / groupsPerPage);
            const startIdx = (currentPage - 1) * groupsPerPage;
            const endIdx = Math.min(startIdx + groupsPerPage, filteredGroups.length);
            const pageGroups = filteredGroups.slice(startIdx, endIdx);
            
            container.innerHTML = pageGroups.map(group => createGroupHTML(group)).join('');
            
            updatePagination(currentPage, totalPages);
        }
        
        function createGroupHTML(group) {
            return `
                <div class="video-group">
                    <div class="group-title">${group.name}</div>
                    <div class="group-videos">
                        <div class="video-item">
                            <div class="video-label">Original</div>
                            <div class="video-container">
                                ${group.original ? 
                                    `<video controls preload="metadata" autoplay muted loop>
                                        <source src="/video/${encodeURIComponent(group.original)}" type="video/mp4">
                                    </video>` :
                                    '<div class="video-placeholder">No original video</div>'
                                }
                            </div>
                        </div>
                        <div class="video-item">
                            <div class="video-label">Generated</div>
                            <div class="video-container">
                                ${group.generated ? 
                                    `<video controls preload="metadata" autoplay muted loop>
                                        <source src="/video/${encodeURIComponent(group.generated)}" type="video/mp4">
                                    </video>` :
                                    '<div class="video-placeholder">No generated video</div>'
                                }
                            </div>
                        </div>
                        <div class="video-item">
                            <div class="video-label">Conditioned</div>
                            <div class="video-container">
                                ${group.conditioned ? 
                                    `<video controls preload="metadata" autoplay muted loop>
                                        <source src="/video/${encodeURIComponent(group.conditioned)}" type="video/mp4">
                                    </video>` :
                                    '<div class="video-placeholder">No conditioned video</div>'
                                }
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        function updatePagination(page, totalPages) {
            const pagination = document.getElementById('pagination');
            const pageInfo = document.getElementById('page-info');
            const prevBtn = document.getElementById('prev-btn');
            const nextBtn = document.getElementById('next-btn');
            const pageJumpInput = document.getElementById('page-jump-input');
            
            if (totalPages > 1) {
                pagination.style.display = 'flex';
                pageInfo.textContent = `Page ${page} of ${totalPages}`;
                prevBtn.disabled = page <= 1;
                nextBtn.disabled = page >= totalPages;
                
                // Update page jump input
                if (pageJumpInput) {
                    pageJumpInput.max = totalPages;
                    pageJumpInput.value = page;
                }
            } else {
                pagination.style.display = 'none';
            }
        }
        
        function changePage(direction) {
            const totalPages = Math.ceil(filteredGroups.length / groupsPerPage);
            const newPage = currentPage + direction;
            
            if (newPage >= 1 && newPage <= totalPages) {
                currentPage = newPage;
                renderGroups();
            }
        }
        
        function changePageSize() {
            groupsPerPage = parseInt(document.getElementById('per-page-select').value);
            currentPage = 1;
            renderGroups();
        }
        
        function filterAndRender() {
            filterGroups();
            renderGroups();
        }
        
        // Event listeners
        document.getElementById('search-input').addEventListener('input', filterAndRender);
        document.getElementById('per-page-select').addEventListener('change', changePageSize);
        
        function jumpToPage() {
            const pageJumpInput = document.getElementById('page-jump-input');
            const targetPage = parseInt(pageJumpInput.value);
            const totalPages = Math.ceil(filteredGroups.length / groupsPerPage);
            
            if (targetPage >= 1 && targetPage <= totalPages && targetPage !== currentPage) {
                currentPage = targetPage;
                renderGroups();
            }
        }
        
        // Keyboard navigation
        document.addEventListener('keydown', function(e) {
            // Allow Enter key in page jump input to trigger jump
            if (e.target.id === 'page-jump-input' && e.key === 'Enter') {
                jumpToPage();
                return;
            }
            
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') {
                return;
            }
            
            const totalPages = Math.ceil(filteredGroups.length / groupsPerPage);
            if (e.key === 'ArrowLeft' && currentPage > 1) {
                changePage(-1);
            } else if (e.key === 'ArrowRight' && currentPage < totalPages) {
                changePage(1);
            }
        });
        
        // Initialize
        loadGroups();
    </script>
</body>
</html>"""

    def serve_video_groups(self):
        """Serve video groups data from one-time scan"""
        global _global_video_groups_cache, _global_scan_completed

        try:
            logger.info(f"API request for video groups from {self.client_address[0]}")

            # Check if we have scanned already
            if not _global_scan_completed or _global_video_groups_cache is None:
                logger.info("Performing initial video groups scan...")
                start_time = time.time()
                groups = self.find_video_groups()
                scan_time = time.time() - start_time
                logger.info(f"Video scan completed in {scan_time:.2f} seconds, found {len(groups)} groups")

                _global_video_groups_cache = {"groups": groups, "total": len(groups)}
                _global_scan_completed = True
                logger.info("Video groups cache populated, no future scans will be performed")
            else:
                logger.info(f"Serving cached groups data ({len(_global_video_groups_cache['groups'])} groups)")

            response = json.dumps(_global_video_groups_cache, indent=2)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response.encode("utf-8"))
            logger.info(f"Sent {len(response)} bytes to client")
        except Exception as e:
            logger.error(f"Error getting video groups: {str(e)}", exc_info=True)
            self.send_error(500, f"Error getting video groups: {str(e)}")

    def find_video_groups(self):
        """Find all video groups in the dataset using optimized scanning"""
        logger.info(f"Starting optimized video group scan in: {self.video_root}")
        groups = []
        total_dirs_scanned = 0
        total_files_checked = 0
        dataset_count = 0

        if not self.video_root.exists():
            logger.error(f"Video root directory does not exist: {self.video_root}")
            return groups

        for dataset_dir in self.video_root.iterdir():
            if not dataset_dir.is_dir():
                continue

            dataset_count += 1
            dataset_start_time = time.time()
            logger.info(f"Scanning dataset {dataset_count}: {dataset_dir.name}")

            dirs_in_dataset = 0
            groups_in_dataset = 0

            # Optimized approach: use glob to find directories that contain the target video files directly
            try:
                # Find directories containing original.video.mp4
                original_dirs = set()
                for original_file in dataset_dir.rglob("original.video.mp4"):
                    original_dirs.add(original_file.parent)

                # Find directories containing generated.video.mp4
                generated_dirs = set()
                for generated_file in dataset_dir.rglob("generated.video.mp4"):
                    generated_dirs.add(generated_file.parent)

                # Find directories containing cond_*.video.mp4
                conditioned_dirs = set()
                for cond_file in dataset_dir.rglob("cond_*.video.mp4"):
                    conditioned_dirs.add(cond_file.parent)

                # Get all unique directories that contain at least one target video
                all_target_dirs = original_dirs | generated_dirs | conditioned_dirs

                logger.info(
                    f"  Found {len(original_dirs)} dirs with original, {len(generated_dirs)} with generated, {len(conditioned_dirs)} with conditioned"
                )
                logger.info(f"  Total unique directories with target videos: {len(all_target_dirs)}")

                # Process each directory that contains target videos
                for target_dir in all_target_dirs:
                    dirs_in_dataset += 1
                    total_dirs_scanned += 1

                    if dirs_in_dataset % 50 == 0:
                        logger.info(
                            f"  Processed {dirs_in_dataset}/{len(all_target_dirs)} target directories in {dataset_dir.name}"
                        )

                    # Check what videos exist in this directory
                    original_video = None
                    generated_video = None
                    conditioned_video = None

                    try:
                        # Check for original video
                        original_path = target_dir / "original.video.mp4"
                        if original_path.exists():
                            original_video = str(original_path.relative_to(self.video_root))
                            total_files_checked += 1

                        # Check for generated video
                        generated_path = target_dir / "generated.video.mp4"
                        if generated_path.exists():
                            generated_video = str(generated_path.relative_to(self.video_root))
                            total_files_checked += 1

                        # Check for conditioned videos (there might be multiple)
                        for cond_file in target_dir.glob("cond_*.video.mp4"):
                            if conditioned_video is None:  # Take the first one we find
                                conditioned_video = str(cond_file.relative_to(self.video_root))
                                total_files_checked += 1
                                break

                    except (PermissionError, OSError) as e:
                        logger.warning(f"Cannot access files in {target_dir}: {e}")
                        continue

                    # Create a group if we found at least one video
                    if original_video or generated_video or conditioned_video:
                        group_name = str(target_dir.relative_to(self.video_root))
                        groups.append(
                            {
                                "name": group_name,
                                "original": original_video,
                                "generated": generated_video,
                                "conditioned": conditioned_video,
                            }
                        )
                        groups_in_dataset += 1
                        logger.debug(f"Created group: {group_name}")

            except (PermissionError, OSError) as e:
                logger.error(f"Cannot scan dataset directory {dataset_dir}: {e}")
                continue

            dataset_time = time.time() - dataset_start_time
            logger.info(
                f"  Dataset {dataset_dir.name} scan complete: {groups_in_dataset} groups found in {dirs_in_dataset} target dirs ({dataset_time:.2f}s)"
            )

        logger.info(
            f"Total scan summary: {len(groups)} groups, {total_dirs_scanned} target dirs, {total_files_checked} files checked"
        )

        # Sort groups by name
        logger.info("Sorting groups by name...")
        groups.sort(key=lambda x: x["name"])
        logger.info("Video group scan complete")
        return groups

    def serve_video_file(self, video_path):
        """Serve actual video files with range support"""
        try:
            full_path = self.video_root / video_path

            if not full_path.exists():
                self.send_error(404, "Video file not found")
                return

            if not full_path.is_file():
                self.send_error(400, "Path is not a file")
                return

            # Determine content type
            content_type, _ = mimetypes.guess_type(str(full_path))
            if content_type is None:
                content_type = "application/octet-stream"

            # Get file size
            file_size = full_path.stat().st_size

            # Handle range requests for video streaming
            range_header = self.headers.get("Range")

            if range_header:
                # Parse range header (e.g., "bytes=0-1023")
                range_match = range_header.replace("bytes=", "").split("-")
                start = int(range_match[0]) if range_match[0] else 0
                end = int(range_match[1]) if range_match[1] else file_size - 1

                # Ensure end doesn't exceed file size
                end = min(end, file_size - 1)
                content_length = end - start + 1

                self.send_response(206)  # Partial Content
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(content_length))
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

                # Send partial content
                with open(full_path, "rb") as f:
                    f.seek(start)
                    remaining = content_length
                    while remaining > 0:
                        chunk_size = min(8192, remaining)
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            else:
                # Send entire file
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

                with open(full_path, "rb") as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        self.wfile.write(chunk)

        except Exception as e:
            self.send_error(500, f"Error serving video: {str(e)}")


def create_handler_class(video_root):
    """Create a handler class with the video root path"""

    class Handler(VideoGroupsHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, video_root=video_root, **kwargs)

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Video Groups Viewer Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    parser.add_argument(
        "--video-root",
        default="/nfs/xfan/object_permanence_data/demo_query_diffusion_model-exp0923-4-1-step030000-test_vids-v3/wods2",
        help="Root directory containing videos",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Set debug level if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug logging enabled")

    # Verify video root exists
    video_root = Path(args.video_root)
    if not video_root.exists():
        logger.error(f"Video root directory '{video_root}' does not exist!")
        print(f"Error: Video root directory '{video_root}' does not exist!")
        return

    logger.info(f"Video root: {video_root}")
    logger.info(f"Starting server on http://{args.host}:{args.port}")
    print(f"Video root: {video_root}")
    print(f"Starting server on http://{args.host}:{args.port}")
    print(f"Logs are being written to /tmp/video_server.log")

    handler_class = create_handler_class(args.video_root)
    httpd = HTTPServer((args.host, args.port), handler_class)

    try:
        logger.info("Server started successfully, waiting for requests...")
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
