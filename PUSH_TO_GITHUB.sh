#!/bin/bash

# Script to push OpenFOAM MCP to GitHub
# Repository: https://github.com/Monishkumarvr/openfoam-mcp.git

echo "🚀 Pushing OpenFOAM MCP to GitHub..."
echo ""

# Check if we're in the right directory
if [ ! -f "openfoam_mcp/server.py" ]; then
    echo "❌ Error: Please run this script from the openfoam-mcp directory"
    exit 1
fi

# Check if remote is set
if ! git remote | grep -q origin; then
    echo "Adding remote origin..."
    git remote add origin https://github.com/Monishkumarvr/openfoam-mcp.git
else
    echo "✓ Remote origin already set"
fi

# Show current status
echo ""
echo "📊 Repository status:"
git log --oneline -1
echo ""

# Push to GitHub
echo "Pushing to GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Successfully pushed to GitHub!"
    echo "🌐 Repository: https://github.com/Monishkumarvr/openfoam-mcp"
    echo ""
    echo "Next steps:"
    echo "1. Visit your repository on GitHub"
    echo "2. Add repository description and topics"
    echo "3. Share with the community!"
else
    echo ""
    echo "❌ Push failed. You may need to:"
    echo "1. Configure git credentials: git config --global credential.helper store"
    echo "2. Or use SSH instead: git remote set-url origin git@github.com:Monishkumarvr/openfoam-mcp.git"
    echo "3. Or create a personal access token: https://github.com/settings/tokens"
fi
