# minimot

A passion project for analyzing YouTube transcripts.

## Getting Started

Navigate to the minimot directory and run:

## Features

### Analyzer (`ana`)
Counts how many times a word or phrase appears across a YouTuber's or playlist's transcripts. Supports exact matches, partial matches, regex, and wildcards, with filtering by title, channel, date, and duration.

### Position Analyzer (`first_ana`)
Finds the most common word at any position across transcripts, like first word, last word, nth word, etc. Results can be visualized as bar charts, pie charts, treemaps, or word clouds.

### Downloader (`dloader`)
Downloads subtitles and metadata (title, duration, view count, etc.) from a YouTube channel or playlist using `yt-dlp`. Progress is saved to disk, so interrupted downloads resume without re-fetching existing data.

> **Important Note:** The downloader is the least stable component and may freeze during use. If this happens, close the program and rerun it, already-downloaded data will not be lost.

## Roadmap

- Improve downloader stability
- Add batch cleaning and batch metadata update support
- Making the application more stable and able to work on multiple systems

## Notes on Development

AI pair programming was used during development, primarily for debugging the analyzer modules (`ana`). Project structure was designed independently. 
