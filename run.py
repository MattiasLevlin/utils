#!/usr/bin/env python3

import os
import re
import argparse
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Dict

# --- Configuration ---

# Regex patterns for comment removal
COMMENT_REGEX: Dict[str, List[re.Pattern]] = {
    ".html": [re.compile(r'<!--.*?-->', re.DOTALL)],
    ".css": [re.compile(r'/\*.*?\*/', re.DOTALL)],
    ".js": [
        re.compile(r'/\*.*?\*/', re.DOTALL),  # Multi-line /* ... */
        re.compile(r'(?<!:)//.*?$', re.MULTILINE)  # Single-line // ... (avoiding URLs)
    ],
}

# Comment format for adding the header
HEADER_COMMENT_FORMAT: Dict[str, str] = {
    ".html": "<!-- {} -->",
    ".css": "/* {} */",
    ".js": "/* {} */",
}

# Target file extensions
TARGET_EXTENSIONS: Tuple[str, ...] = tuple(COMMENT_REGEX.keys())

# Directories to skip during traversal
SKIP_DIRS: set[str] = {
    '.git', '.vscode', 'node_modules', '__pycache__',
    'venv', '.venv', 'dist', 'build', 'assets' # Added assets as likely we don't want to modify these
}

# --- Utility Functions ---

def colorize(text: str, color: str = "default") -> str:
    """Adds ANSI color codes to text for terminal output."""
    colors: Dict[str, str] = {
        "red": "\033[91m", "yellow": "\033[93m", "green": "\033[92m",
        "blue": "\033[94m", "default": "\033[0m", "end": "\033[0m"
    }
    start_code = colors.get(color.lower(), colors["default"])
    end_code = colors["end"]
    # Disable color if stdout is not a TTY or on basic Windows terminals
    if not sys.stdout.isatty() or (os.name == 'nt' and 'TERM' not in os.environ):
         return text
    return f"{start_code}{text}{end_code}"

def read_file_content(file_path: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Reads file content, trying UTF-8 then latin-1 encoding.
    Returns (content, encoding) or (None, None) on error.
    """
    encodings_to_try = ['utf-8', 'latin-1']
    for encoding in encodings_to_try:
        try:
            content = file_path.read_text(encoding=encoding)
            return content, encoding
        except UnicodeDecodeError:
            continue # Try the next encoding
        except Exception as e:
            print(colorize(f"Error reading {file_path}: {e}", "red"), file=sys.stderr)
            return None, None # General read error

    print(colorize(f"Error: Could not decode {file_path} with {', '.join(encodings_to_try)}.", "red"), file=sys.stderr)
    return None, None

def clean_content(content: str, file_extension: str) -> str:
    """Removes comments based on file extension."""
    cleaned = content
    regex_list = COMMENT_REGEX.get(file_extension)
    if regex_list:
        for regex in regex_list:
            cleaned = regex.sub('', cleaned)
    return cleaned

def create_header(file_path: Path, root_dir: Path, file_extension: str) -> Optional[str]:
    """Creates the header comment with the relative path."""
    try:
        # Calculate relative path reliably
        relative_path = file_path.relative_to(root_dir).as_posix() # Use forward slashes
        formatter = HEADER_COMMENT_FORMAT.get(file_extension)
        if formatter:
            return formatter.format(relative_path)
        else:
             print(colorize(f"Warning: No header format defined for {file_extension} files.", "yellow"), file=sys.stderr)
             return None # Should not happen if TARGET_EXTENSIONS is based on the dict keys
    except ValueError as e:
        # This might happen if file_path is not under root_dir (shouldn't with os.walk)
        print(colorize(f"Error calculating relative path for {file_path} relative to {root_dir}: {e}", "red"), file=sys.stderr)
        # Fallback to filename only
        formatter = HEADER_COMMENT_FORMAT.get(file_extension)
        if formatter:
             return formatter.format(f"{file_path.name} (relative path error)")
        return None
    except Exception as e:
        print(colorize(f"Unexpected error creating header for {file_path}: {e}", "red"), file=sys.stderr)
        return None


def write_file_content(file_path: Path, content: str, encoding: str) -> bool:
    """Writes content back to the file using the original encoding."""
    try:
        file_path.write_text(content, encoding=encoding)
        return True
    except Exception as e:
        print(colorize(f"Error writing back to {file_path}: {e}", "red"), file=sys.stderr)
        return False

# --- Core Logic ---

def process_file(file_path: Path, root_dir: Path) -> bool:
    """
    Processes a single file: reads, cleans comments, adds header, writes back if changed.
    Returns True if the file was modified, False otherwise or on error.
    """
    file_extension = file_path.suffix.lower()
    if file_extension not in TARGET_EXTENSIONS:
        return False # Should not happen if called correctly, but safe check

    # 1. Read Content
    original_content, encoding = read_file_content(file_path)
    if original_content is None or encoding is None:
        return False # Error already printed by read_file_content

    # 2. Clean Content (Remove Comments)
    cleaned_content_no_header = clean_content(original_content, file_extension)

    # 3. Create Header
    header_comment = create_header(file_path, root_dir, file_extension)
    if header_comment is None:
         # Consider if processing should stop or just skip header addition
         print(colorize(f"Skipping header addition for {file_path.relative_to(root_dir).as_posix()}", "yellow"), file=sys.stderr)
         # If we decide to still write the cleaned content without header:
         # final_content = cleaned_content_no_header
         # Otherwise, if header is essential, return False or handle differently
         # For now, let's assume we proceed without header if creation fails
         final_content = cleaned_content_no_header # Or decide to return False here
    else:
        # 4. Construct Final Content (Header + Cleaned Content)
        # Ensure header is on its own line, followed by the content.
        # Handle cases where cleaned content might be empty or just whitespace.
        final_content = f"{header_comment}\n{cleaned_content_no_header.lstrip()}"


    # 5. Write Back if Changed
    modified = False
    if final_content != original_content:
        if write_file_content(file_path, final_content, encoding):
            relative_path_str = file_path.relative_to(root_dir).as_posix()
            # Refine message: distinguish comment removal vs just header change
            if cleaned_content_no_header.strip() != original_content.strip():
                print(f"Removed comments and updated header: {relative_path_str}")
            else:
                print(f"Updated header: {relative_path_str}")
            modified = True
        # else: Error already printed by write_file_content
    # else:
    #    relative_path_str = file_path.relative_to(root_dir).as_posix()
    #    print(f"No changes needed: {relative_path_str}") # Optional: Log unchanged files

    return modified


def process_directory(root_dir: Path) -> Tuple[int, int, int]:
    """
    Recursively finds and processes files with target extensions in the directory.
    Returns (processed_count, changed_count, error_count).
    """
    processed_count = 0
    changed_count = 0
    error_count = 0

    print(f"Starting processing in directory: {root_dir.resolve()}")
    print(f"Targeting extensions: {', '.join(TARGET_EXTENSIONS)}")
    print(f"Skipping directories: {', '.join(SKIP_DIRS)}")
    print(colorize("--- NOTE ---", "blue"))
    print(colorize("Existing comments matching patterns will be removed.", "blue"))
    print(colorize("A header comment with the relative file path will be added/updated.", "blue"))
    print(colorize("JS comment removal uses regex; review changes carefully.", "yellow"))
    print("---")

    for item in root_dir.rglob('*'): # rglob handles recursion
        if item.is_dir():
            # Check if the current directory is in the skip list
            if item.name in SKIP_DIRS or item.name.startswith('.'):
                 # Need to prevent rglob from descending further; Pathlib doesn't have direct prune.
                 # This check is mainly informative; filtering happens below.
                 # A more complex approach would involve manually walking.
                 # print(f"Skipping directory: {item}") # Potentially verbose
                 pass
            continue # Move to the next item

        # Check if the parent directory should be skipped
        # Create a set of absolute paths for skipped dirs for efficient checking
        # This is complex with rglob; simpler to filter files based on path parts.
        part_of_skipped_dir = any(part in SKIP_DIRS or part.startswith('.') for part in item.relative_to(root_dir).parts[:-1]) # Check intermediate parts
        if part_of_skipped_dir:
            continue


        if item.is_file() and item.suffix.lower() in TARGET_EXTENSIONS:
            processed_count += 1
            try:
                was_modified = process_file(item, root_dir)
                if was_modified:
                    changed_count += 1
            except Exception as e:
                # Catch unexpected errors during processing of a single file
                relative_path_str = item.relative_to(root_dir).as_posix()
                print(colorize(f"Critical error processing {relative_path_str}: {e}", "red"), file=sys.stderr)
                error_count += 1

    print("---")
    print(f"Processing finished.")
    print(f"Total files scanned matching extensions: {processed_count}")
    print(f"Files modified: {changed_count}")
    if error_count > 0:
        print(colorize(f"Errors occurred during processing: {error_count}", "red"))

    return processed_count, changed_count, error_count

# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(
        description="Recursively remove comments and add a file path header to HTML, CSS, and JS files.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            f"{colorize('WARNING: Modifies files IN-PLACE.', 'red')}\n"
            f"- Removes existing comments matching predefined patterns.\n"
            f"- Adds/Updates a header comment (e.g., /* path/file.js */) on line 1.\n"
            f"- {colorize('JS comment removal uses regex; review changes carefully!', 'yellow')}\n"
            f"- {colorize('It is HIGHLY recommended to use this on a Git repository or have backups.', 'yellow')}"
        )
    )
    parser.add_argument(
        '-d', '--directory',
        default='.',
        help='The root directory to start searching (default: current directory)'
    )
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Skip the confirmation prompt (use with caution!)'
    )
    args = parser.parse_args()

    target_directory = Path(args.directory)

    if not target_directory.is_dir():
        print(colorize(f"Error: Directory not found: {target_directory}", "red"), file=sys.stderr)
        sys.exit(1)

    abs_target_dir = target_directory.resolve()
    process_directory(abs_target_dir)


if __name__ == "__main__":
    main()
