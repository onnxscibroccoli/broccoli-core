#!/data/data/com.termux/files/usr/bin/bash

# Configuration
SEARCH_DIR="$HOME"
OUTPUT_FILE="$HOME/broccoli-core/pending_tasks.txt"

# Find .md files anywhere in home, extract [ ], save to local file
find "$SEARCH_DIR" -type f -name "*.md" -exec grep -h "\[ \]" {} + > "$OUTPUT_FILE"

# Copy to clipboard using native Termux API
if [ -s "$OUTPUT_FILE" ]; then
    if termux-clipboard-set < "$OUTPUT_FILE"; then
        echo "SUCCESS: Incomplete tasks found and copied to clipboard."
    else
        echo "WARNING: Tasks found and saved to $OUTPUT_FILE, but copying to clipboard failed."
    fi
else
    echo "No incomplete tasks found in the filesystem."
fi
