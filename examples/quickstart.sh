#!/bin/bash
# Quick start guide for Scout v0

echo "Scout v0 - Resume & Job Description Gap Analysis"
echo "=================================================="
echo ""

# Check if GOOGLE_API_KEY is set
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "❌ Error: GOOGLE_API_KEY environment variable is not set"
    echo ""
    echo "Please set your Google API key:"
    echo "  export GOOGLE_API_KEY='your-api-key-here'"
    exit 1
fi

echo "✓ GOOGLE_API_KEY is set"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Run example
echo "Running example extraction..."
python main.py extract \
    --resume examples/example_resume.txt \
    --jd examples/example_jd.txt \
    --out examples/example_output.json

echo ""
echo "✅ Complete! Check examples/example_output.json for results."
