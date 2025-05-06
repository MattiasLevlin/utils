#!/bin/bash

# This script runs cleanup and formatting commands sequentially.
# Run it from the root directory of your project.

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Starting Cleanup & Formatting ---"

# 1. Run cleanup
echo "[1/4] Cleaning up..."
python3 cleanup.py
echo "      Done."

# 2. Run Prettier to format code
echo "[2/4] Formatting with Prettier..."
# Note: Running on '.' can be slow in large projects.
npx prettier --write .
echo "      Done."

# 3. Run StandardJS to lint and fix code
echo "[3/4] Linting and fixing with StandardJS..."
# Note: Running on '.' can be slow.
# This might exit with an error if it finds issues it cannot fix.
# The 'set -e' above will stop the script here if standard fails.
npx standard --fix
echo "      Done."

# 4. Run the tree script
echo "[4/4] Running tree script..."
print-tree.sh
echo "      Done."

echo "--- Cleanup & Formatting Finished Successfully ---"

# Exit with success code
exit 0
