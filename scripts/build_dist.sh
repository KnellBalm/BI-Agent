#!/bin/bash
# BI-Agent Distribution Build Script

echo "📦 Building BI-Agent distribution packages..."

# Ensure build package is installed
python3 -m pip install --upgrade build

# Clean old builds
rm -rf dist/ build/ *.egg-info

# Build with no isolation to avoid pip user-install conflicts
python3 -m build --no-isolation

echo ""
echo "✅ Build complete! Files are in the 'dist/' directory:"
ls -lh dist/
echo ""
echo "🚀 To test locally on another machine/server:"
echo "1. Transfer the .whl file to the server."
echo "2. Run: pip install dist/bi_agent-1.0.0-py3-none-any.whl"
echo ""
echo "🌐 To publish to PyPI (official):"
echo "1. Run: twine upload dist/*"
