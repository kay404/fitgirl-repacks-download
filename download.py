#!/usr/bin/env python3
"""
FitGirl Repacks - FuckingFast Batch Downloader

Usage:
    python3 download.py <fitgirl_url> [options]

Examples:
    python3 download.py https://fitgirl-repacks.site/black-myth-wukong/
    python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ --filter "part0[0-1]"
    python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ --skip-optional
    python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ --list-only
    python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ --parallel 3
"""

import argparse
import os
import random
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def _fetch_via_curl(url: str) -> str | None:
    """Fallback HTTP GET via system curl (different TLS stack than Python).
    Useful when Python's SSL fails repeatedly against Cloudflare-fronted hosts."""
    curl = shutil.which("curl")
    if not curl:
        return None
    try:
        result = subprocess.run(
            [curl, "-sSL", "--fail", "--max-time", "30",
             "-A", UA, url],
            capture_output=True, timeout=45,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        print(f"  curl fallback failed (exit {result.returncode}): {stderr}", file=sys.stderr)
    except Exception as e:
        print(f"  curl fallback exception: {e}", file=sys.stderr)
    return None


def fetch(url: str, retries: int = 5) -> str:
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            last_err = e
            if attempt < retries:
                # 5xx / 429 are usually rate limits — back off much harder with jitter
                # so we drop out of the host's sliding window.
                if e.code >= 500 or e.code == 429:
                    wait = min(15 * (2 ** (attempt - 1)), 120) + random.uniform(0, 10)
                else:
                    wait = min(2 ** attempt, 30)
                print(f"  fetch failed (HTTP {e.code}); retry {attempt}/{retries - 1} in {wait:.0f}s", file=sys.stderr)
                time.sleep(wait)
        except Exception as e:
            last_err = e
            if attempt < retries:
                wait = min(2 ** attempt, 30) + random.uniform(0, 2)
                print(f"  fetch failed ({type(e).__name__}: {e}); retry {attempt}/{retries - 1} in {wait:.0f}s", file=sys.stderr)
                time.sleep(wait)

    # Python's urllib exhausted retries — try system curl, which uses a
    # different TLS stack and often gets past Cloudflare TLS-fingerprint blocks.
    print(f"  urllib failed after {retries} attempts; falling back to curl", file=sys.stderr)
    body = _fetch_via_curl(url)
    if body is not None:
        return body

    raise last_err  # type: ignore[misc]


def get_fuckingfast_links(fitgirl_url: str) -> list[dict]:
    """Extract all FuckingFast links from a FitGirl Repacks page."""
    html = fetch(fitgirl_url)

    # Find the FuckingFast section and extract links
    links = []
    for m in re.finditer(
        r'<a\s+href="(https://fuckingfast\.co/[^"]+)"[^>]*>([^<]+)</a>',
        html,
    ):
        url = m.group(1)
        name = m.group(2).replace("&#8211;", "--").replace("&#8217;", "'")
        # Also get filename from URL fragment
        fragment = url.split("#", 1)[1] if "#" in url else name
        filename = urllib.request.url2pathname(fragment).replace("--", "--")
        links.append({"url": url, "filename": filename, "name": name})

    return links


def extract_download_url(page_url: str) -> str | None:
    """Fetch a FuckingFast page and extract the direct download URL from JS."""
    html = fetch(page_url)

    # Look for the window.open URL in the download() function
    m = re.search(r'window\.open\("(https://(?:dl\.)?fuckingfast\.co/dl/[^"]+)"', html)
    if m:
        return m.group(1)

    return None


def _size_marker_path(filepath: str) -> str:
    return filepath + ".size"


def _record_complete(filepath: str, total: int) -> None:
    """Write a sidecar file recording the final byte count of a finished download.
    Used to fast-skip already-completed files on re-runs without re-resolving."""
    try:
        with open(_size_marker_path(filepath), "w", encoding="utf-8") as f:
            f.write(str(total))
    except Exception:
        pass


def _is_already_complete(filepath: str) -> int | None:
    """If the file is fully downloaded according to a previous run's sidecar,
    return its size; otherwise None. Allows skipping the FuckingFast resolve."""
    marker = _size_marker_path(filepath)
    if not (os.path.exists(filepath) and os.path.exists(marker)):
        return None
    try:
        with open(marker, "r", encoding="utf-8") as f:
            expected = int(f.read().strip())
        if expected > 0 and os.path.getsize(filepath) == expected:
            return expected
    except Exception:
        pass
    return None


def download_file(dl_url: str, filename: str, output_dir: str) -> tuple[str, bool, str]:
    """Download a file with resume support. Returns (filename, success, message)."""
    filepath = os.path.join(output_dir, filename)

    # Check existing file for resume
    resume_offset = 0
    if os.path.exists(filepath):
        resume_offset = os.path.getsize(filepath)

    # HEAD request to get total size, skip if already complete
    if resume_offset > 0:
        head_req = urllib.request.Request(dl_url, method="HEAD", headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(head_req, timeout=15) as head_resp:
                remote_size = int(head_resp.headers.get("Content-Length", 0))
                if remote_size > 0 and resume_offset >= remote_size:
                    _record_complete(filepath, remote_size)
                    return (filename, True, f"Already complete ({resume_offset / 1024 / 1024:.1f} MB)")
        except Exception:
            pass  # HEAD failed, fall through to normal download

    req = urllib.request.Request(dl_url, headers={"User-Agent": UA})
    if resume_offset > 0:
        req.add_header("Range", f"bytes={resume_offset}-")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            # Check if server supports range requests
            status = resp.status
            content_range = resp.headers.get("Content-Range")

            if resume_offset > 0 and status == 206 and content_range:
                # Partial content - resume supported
                # Content-Range: bytes 12345-67890/67891
                total = int(content_range.split("/")[-1])
                remaining = int(resp.headers.get("Content-Length", 0))
                if resume_offset >= total:
                    return (filename, True, f"Already complete ({total / 1024 / 1024:.1f} MB)")
                print(f"  Resuming from {resume_offset / 1024 / 1024:.1f} MB")
                mode = "ab"  # append
            elif resume_offset > 0 and status == 200:
                # Server doesn't support Range, re-download from scratch
                total = int(resp.headers.get("Content-Length", 0))
                resume_offset = 0
                mode = "wb"
            else:
                total = int(resp.headers.get("Content-Length", 0))
                mode = "wb"

            total_mb = total / 1024 / 1024 if total else 0

            with open(filepath, mode) as f:
                downloaded = resume_offset
                chunk_size = 1024 * 1024  # 1MB chunks
                start_time = time.time()

                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    elapsed = time.time() - start_time
                    new_bytes = downloaded - resume_offset
                    speed = new_bytes / elapsed if elapsed > 0 else 0
                    speed_mb = speed / 1024 / 1024

                    if total:
                        pct = downloaded / total * 100
                        print(
                            f"\r  [{filename}] {downloaded / 1024 / 1024:.1f}/{total_mb:.1f} MB "
                            f"({pct:.1f}%) - {speed_mb:.1f} MB/s",
                            end="",
                            flush=True,
                        )
                    else:
                        print(
                            f"\r  [{filename}] {downloaded / 1024 / 1024:.1f} MB - {speed_mb:.1f} MB/s",
                            end="",
                            flush=True,
                        )

                print()  # newline after progress

            # Verify download completeness
            if total and downloaded < total:
                return (filename, False, f"Incomplete: got {downloaded / 1024 / 1024:.1f}/{total / 1024 / 1024:.1f} MB (connection closed early)")

            elapsed = time.time() - start_time
            new_bytes = downloaded - resume_offset
            if total:
                _record_complete(filepath, total)
            else:
                _record_complete(filepath, downloaded)
            return (filename, True, f"Done ({new_bytes / 1024 / 1024:.1f} MB downloaded in {elapsed:.0f}s, total {downloaded / 1024 / 1024:.1f} MB)")

    except Exception as e:
        return (filename, False, str(e))


def resolve_and_download(link: dict, output_dir: str, retries: int = 3) -> tuple[str, bool, str]:
    """Resolve a FuckingFast link and download the file, with retry on failure."""
    filename = link["filename"]
    filepath = os.path.join(output_dir, filename)

    # Fast path: file was fully downloaded on a previous run — skip resolving the
    # short-lived FuckingFast direct link entirely.
    cached = _is_already_complete(filepath)
    if cached is not None:
        return (filename, True, f"Already complete ({cached / 1024 / 1024:.1f} MB, cached)")

    last_err = ""

    for attempt in range(1, retries + 1):
        if attempt > 1:
            # Longer backoff with jitter: when FuckingFast soft-rate-limits us
            # with 500s, short waits keep us in the same throttling window.
            wait = min(20 * attempt, 90) + random.uniform(0, 10)
            print(f"  Retry {attempt}/{retries} for {filename} (waiting {wait:.0f}s)")
            time.sleep(wait)

        print(f"  Resolving: {filename}")
        try:
            dl_url = extract_download_url(link["url"])
            if not dl_url:
                last_err = "Could not extract download URL"
                continue

            fname, ok, msg = download_file(dl_url, filename, output_dir)
            if ok:
                return (fname, True, msg)
            last_err = msg
        except Exception as e:
            last_err = str(e)

    return (filename, False, f"Failed after {retries} attempts: {last_err}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch download FuckingFast links from FitGirl Repacks"
    )
    parser.add_argument("url", help="FitGirl Repacks game page URL")
    parser.add_argument(
        "-o", "--output", default=".", help="Output directory (default: current dir)"
    )
    parser.add_argument(
        "-p", "--parallel", type=int, default=2,
        help="Number of parallel downloads (default: 2)"
    )
    parser.add_argument(
        "-l", "--list-only", action="store_true",
        help="Only list files, don't download"
    )
    parser.add_argument(
        "-f", "--filter", default=None,
        help="Regex filter for filenames (e.g. 'part0[0-1]' for parts 1-19)"
    )
    parser.add_argument(
        "--skip-optional", action="store_true",
        help="Skip optional components (bonus content, soundtracks, etc.)"
    )
    parser.add_argument(
        "--start", type=int, default=None,
        help="Start from part N (e.g. --start 5 to skip parts 1-4)"
    )
    parser.add_argument(
        "--end", type=int, default=None,
        help="End at part N (e.g. --end 10 to only download up to part 10)"
    )
    parser.add_argument(
        "-r", "--retry", type=int, default=3,
        help="Max retry attempts per file on failure (default: 3)"
    )

    args = parser.parse_args()

    # Fetch links
    print(f"Fetching links from: {args.url}")
    links = get_fuckingfast_links(args.url)

    if not links:
        print("No FuckingFast links found!")
        sys.exit(1)

    print(f"Found {len(links)} files total\n")

    # Apply filters
    filtered = links

    if args.skip_optional:
        filtered = [l for l in filtered if "optional" not in l["filename"].lower()]

    if args.filter:
        pattern = re.compile(args.filter)
        filtered = [l for l in filtered if pattern.search(l["filename"])]

    if args.start is not None or args.end is not None:
        result = []
        for l in filtered:
            m = re.search(r'part(\d+)', l["filename"])
            if not m:
                continue  # skip non-part files when using start/end range
            part_num = int(m.group(1))
            if args.start and part_num < args.start:
                continue
            if args.end and part_num > args.end:
                continue
            result.append(l)
        filtered = result

    if not filtered:
        print("No files match the filter criteria!")
        sys.exit(1)

    # List files
    print(f"Files to download ({len(filtered)}):")
    for i, link in enumerate(filtered, 1):
        print(f"  {i:3d}. {link['filename']}")
    print()

    if args.list_only:
        return

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Download
    print(f"Downloading to: {os.path.abspath(args.output)}")
    print(f"Parallel downloads: {args.parallel}\n")

    success_count = 0
    fail_count = 0
    failed_files = []

    if args.parallel <= 1:
        # Sequential download
        for i, link in enumerate(filtered, 1):
            print(f"[{i}/{len(filtered)}] {link['filename']}")
            filename, ok, msg = resolve_and_download(link, args.output, args.retry)
            if ok:
                success_count += 1
                print(f"  ✓ {msg}")
            else:
                fail_count += 1
                failed_files.append(filename)
                print(f"  ✗ {msg}")
    else:
        # Parallel download
        with ThreadPoolExecutor(max_workers=args.parallel) as executor:
            futures = {}
            for link in filtered:
                future = executor.submit(resolve_and_download, link, args.output, args.retry)
                futures[future] = link

            for future in as_completed(futures):
                link = futures[future]
                filename, ok, msg = future.result()
                if ok:
                    success_count += 1
                    print(f"  ✓ {filename}: {msg}")
                else:
                    fail_count += 1
                    failed_files.append(filename)
                    print(f"  ✗ {filename}: {msg}")

    # Summary
    print(f"\n{'='*50}")
    print(f"Done! Success: {success_count}, Failed: {fail_count}")
    if failed_files:
        print(f"\nFailed files:")
        for f in failed_files:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
