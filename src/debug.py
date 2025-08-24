import os
import json
import argparse
import re
from pathlib import Path

"""

    RUN AFTER ALL FILES WERE DOWNLOADED
    THEN RUN DOWNLOADER AGAIN
    SOME VIDEOS JUST DONT HAVE SUBTITLES

"""

DEFAULT_BASE_DIR = "/Users/c/minimot/data/input"
VTT_SUBDIR = "vtt_files"

def get_vid_id(filename):
    match = re.search(r'\[([a-zA-Z0-9_-]{11})\]\.en\.vtt$', filename)
    return match.group(1) if match else None

def check_and_clean_subtitles(metadata_path, archive_path, vtt_directory):
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    except Exception as e:
        print(f"Error loading metadata file: {e}")
        return [], 0, 0

    metadata_ids = {entry['id']: entry for entry in metadata if 'id' in entry}

    vtt_files = {}
    for filename in os.listdir(vtt_directory):
        if filename.endswith('.en.vtt'):
            video_id = get_vid_id(filename)
            if video_id:
                vtt_files[video_id] = filename

    missing_files = []
    for video_id, entry in metadata_ids.items():
        if video_id not in vtt_files:
            missing_files.append({
                'id': video_id,
                'title': entry.get('title'),
                'expected_filename': f"{entry.get('title')} [{video_id}].en.vtt"
            })

    try:
        with open(archive_path, 'r', encoding='utf-8') as f:
            archive_lines = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error loading archive file: {e}")
        return missing_files, len(metadata), 0

    entries_to_keep = []
    entries_removed = 0
    
    for line in archive_lines:
        parts = line.split()
        if len(parts) >= 2 and parts[0] == 'youtube':
            video_id = parts[1]

            if video_id in vtt_files: # or video_id in metadata_ids:
                entries_to_keep.append(line)
            else:
                entries_removed += 1

    # Comment out if archive.txt needs to be cleaned of videos with no subs
    '''
    if entries_removed > 0:
        try:
            with open(archive_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(entries_to_keep) + "\n")
        except Exception as e:
            print(f"Error updating archive file: {e}")
            return missing_files, len(metadata), 0
            '''
    
    return missing_files, len(metadata), entries_removed

def main():
    parser = argparse.ArgumentParser(
        description="Check VTT files match metadata and clean archive.txt")
    parser.add_argument('directory', help="Name of directory (e.g., 'vsauce') containing the files")
    parser.add_argument('--base-dir', default=DEFAULT_BASE_DIR, 
                       help=f"Base directory (default: {DEFAULT_BASE_DIR})")
    
    args = parser.parse_args()
    
    dir_path = Path(args.base_dir) / args.directory
    metadata_path = dir_path / "metadata.json"
    archive_path = dir_path / "archive.txt"
    vtt_dir = dir_path / VTT_SUBDIR
    
    if not metadata_path.exists():
        print(f"Error: metadata.json not found at {metadata_path}")
        return
    if not archive_path.exists():
        print(f"Error: archive.txt not found at {archive_path}")
        return
    if not vtt_dir.exists():
        print(f"Error: VTT directory not found at {vtt_dir}")
        return
    
    missing, total, removed = check_and_clean_subtitles(
        str(metadata_path), str(archive_path), str(vtt_dir))
    
    print(f"\nChecked {total} entries in metadata.json")
    print(f"Found {len(missing)} missing subtitle files")
    print(f"Removed {removed} entries from archive.txt")
    
    if missing:
        print("\nMissing subtitle files:")
        for i, item in enumerate(missing[:10], 1):
            print(f"{i}. {item['title']} [{item['id']}]")
            print(f"   Expected filename: {item['expected_filename']}")
        
        if len(missing) > 10:
            print(f"\n...and {len(missing) - 10} more missing files")
        
        missing_path = dir_path / "missing_subtitles.json"
        with open(missing_path, 'w', encoding='utf-8') as f:
            json.dump(missing, f, indent=2)
        print(f"\nFull list saved to: {missing_path}")

if __name__ == "__main__":
    main()

# python3 src/debug.py debug