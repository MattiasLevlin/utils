#!/bin/bash

# --- Configuration ---
OUTPUT_FILE="tree.txt"
TARGET_DIR="${1:-.}"
SIZE_FIELD_WIDTH=9    # e.g., accommodates " 999.9 MiB"
LINES_FIELD_WIDTH=7   # e.g., accommodates " 1234567"
METADATA_WIDTH=28

# --- OS Detection for stat command ---
STAT_FORMAT=""
OS_TYPE=$(uname -s)
if [[ "$OS_TYPE" == "Linux" ]]; then
    STAT_FORMAT="-c %s"
elif [[ "$OS_TYPE" == "Darwin" ]]; then
    STAT_FORMAT="-f %z"
else
    echo "Warning: Unknown OS type '$OS_TYPE'. Attempting GNU stat format." >&2
    STAT_FORMAT="-c %s"
fi

# --- Redirect stdout ---
exec > "$OUTPUT_FILE"

# --- Global counters ---
total_files=0
total_dirs=0

# --- Function Definitions ---
format_bytes_awk() {
    local bytes=$1
    local decimals=1
    local units_str="B KiB MiB GiB TiB PiB EiB"

    if [[ "$bytes" -eq 0 ]]; then echo "0 B"; return; fi

    echo "$bytes" | awk -v d="$decimals" -v units_str="$units_str" '
    BEGIN { split(units_str, units, " "); divisor = 1024 }
    {
        b = $1; scale = 0
        while (b >= divisor && scale < length(units) - 1 && scale < 10) {
            b /= divisor; scale++
        }
        if (scale == 0) { printf "%d %s", $1, units[scale+1] }
        else { printf "%." d "f %s", b, units[scale+1] }
    }'
}


print_tree_with_info() {
    local dir="$1"
    local prefix="$2"
    local items=()
    local full_path item
    local i count
    local connector indent_chars
    local is_last
    local lines lines_err size_bytes size_err size_human
    local metadata_display

    while IFS= read -r entry; do
        items+=("$entry")
    done < <(find "$dir" -maxdepth 1 -mindepth 1 \( -name venv -prune \) -o \( -name .git -prune \) -o -print | sort)

    count="${#items[@]}"

    for i in "${!items[@]}"; do
        full_path="${items[$i]}"
        item=$(basename "$full_path")
        is_last=$(( i == count - 1 ))

        if [[ $is_last -eq 1 ]]; then
            connector="└── "
            indent_chars="    "
        else
            connector="├── "
            indent_chars="│   "
        fi

        local metadata_placeholder=""

        if [[ -d "$full_path" && ! -L "$full_path" ]]; then
            if [[ "$item" != "venv" && "$item" != ".git" ]]; then
                printf "%-*s %s%s%s\n" "$METADATA_WIDTH" "$metadata_placeholder" "$prefix" "$connector" "$item"
                ((total_dirs++))
                print_tree_with_info "$full_path" "$prefix$indent_chars"
            fi
        elif [[ -f "$full_path" && -r "$full_path" ]]; then
            size_bytes=$(stat "$STAT_FORMAT" "$full_path" 2>/dev/null)
            size_err=$?

            lines=$(wc -l < "$full_path" 2>/dev/null)
            lines_err=$?
            lines=$(echo "$lines" | tr -d '[:space:]')

            metadata_display=""
            if [[ $size_err -eq 0 && $lines_err -eq 0 ]]; then
                size_human=$(format_bytes_awk "$size_bytes")
                local size_fmt=$(printf "%*s" "$SIZE_FIELD_WIDTH" "$size_human")
                local lines_fmt=$(printf "%*s" "$LINES_FIELD_WIDTH" "$lines")
                metadata_display="${size_fmt}, ${lines_fmt} lines"
            else
                local err_str=""
                [[ $size_err -ne 0 ]] && err_str="Size err"
                [[ $lines_err -ne 0 ]] && { [[ -n "$err_str" ]] && err_str+=", "; err_str+="Lines err"; }
                metadata_display="$err_str"
            fi

            printf "%-*s %s%s%s\n" "$METADATA_WIDTH" "$metadata_display" "$prefix" "$connector" "$item"
            ((total_files++))

        elif [[ -e "$full_path" ]]; then
             if [[ "$item" != "venv" && "$item" != ".git" ]]; then
                 printf "%-*s %s%s%s\n" "$METADATA_WIDTH" "$metadata_placeholder" "$prefix" "$connector" "$item"
             fi
        fi
    done
}

# --- Main Script Execution ---
if [[ ! -d "$TARGET_DIR" ]]; then
    echo "Error: Directory '$TARGET_DIR' not found." >&2
    exit 1
fi

if [[ -z "$STAT_FORMAT" ]]; then
    echo "Error: Could not determine appropriate 'stat' command format for this OS ($OS_TYPE)." >&2
    exit 1
fi

# --- Output Generation ---
printf "%-*s %s\n" "$METADATA_WIDTH" "" "$TARGET_DIR"
print_tree_with_info "$TARGET_DIR" ""
echo ""
echo "${total_dirs} directories, ${total_files} files"
echo "Output written to $OUTPUT_FILE" >&2

exit 0