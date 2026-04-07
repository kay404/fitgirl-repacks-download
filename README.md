<h1 align="center">FitGirl Repacks - FuckingFast Batch Downloader</h1>
<p align="center">
  <b>Batch download all FuckingFast-hosted .rar parts from FitGirl Repacks pages</b><br>
  <a href="#usage">Usage</a> •
  <a href="#features">Features</a> •
  <a href="#options">Options</a> •
  <a href="#how-it-works">How It Works</a><br>
  English | <a href="README.zh-CN.md">简体中文</a>
</p>

---

Large games on FitGirl Repacks are split into hundreds of `.rar` parts. Clicking each one manually is painfully slow. This tool batch-downloads all FuckingFast-hosted parts automatically.

## Features

- **Batch download** - Auto-parse page and extract all FuckingFast download links
- **Resume support** - Interrupted? Just re-run. Downloads resume from where they left off
- **Auto retry** - Failed files are retried automatically (default 3 attempts, with backoff)
- **Integrity check** - Verifies file size after download to catch silent truncation
- **Parallel downloads** - Multi-threaded downloads to maximize bandwidth
- **Flexible filtering** - Filter by part range, regex, or skip optional components
- **Zero dependencies** - Pure Python stdlib, no `pip install` needed

## Requirements

- Python 3.12+

## Usage

```bash
# List all files (no download)
python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ --list-only

# Download all files to a directory
python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ -o ~/Downloads/bmw

# Skip optional content (soundtracks, etc.)
python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ -o ~/Downloads/bmw --skip-optional

# Download only part 5 through 10
python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ --start 5 --end 10

# 3 parallel downloads
python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ -p 3

# Regex filter on filenames
python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ --filter "part00[1-5]"

# More retries for unstable networks
python3 download.py https://fitgirl-repacks.site/black-myth-wukong/ -r 5
```

## Options

| Option | Description |
|---|---|
| `-o, --output DIR` | Output directory (default: current dir) |
| `-p, --parallel N` | Parallel download count (default: 2) |
| `-l, --list-only` | List files only, don't download |
| `-f, --filter REGEX` | Regex filter on filenames |
| `--skip-optional` | Skip optional components (soundtracks, etc.) |
| `--start N` | Start from part N |
| `--end N` | End at part N |
| `-r, --retry N` | Max retry attempts per file (default: 3) |

## How It Works

1. Fetch the FitGirl Repacks game page HTML
2. Extract all `fuckingfast.co` file links
3. Visit each FuckingFast page and extract the real download URL from embedded JavaScript (`/dl/` URL)
4. Download files via direct links, with resume and auto-retry

## Notes

- FuckingFast `/dl/` tokens are time-limited; retries automatically re-fetch a fresh token
- Keep parallel count low (2-3) to avoid server throttling
- Re-run the same command after interruption — completed files are skipped automatically

## Disclaimer

This tool is provided for educational and technical learning purposes only. It does not host, distribute, or provide any copyrighted content. Users are solely responsible for ensuring their use of this tool complies with applicable laws and regulations.

**We strongly encourage purchasing genuine copies of games to support the developers.** Game developers invest years of effort into creating these experiences — buying the official version is the best way to ensure they can keep making great games.

- [Steam](https://store.steampowered.com/)
- [Epic Games Store](https://store.epicgames.com/)
- [GOG](https://www.gog.com/)
