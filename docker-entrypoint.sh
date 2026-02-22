#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Document Archive API Container Starting ===${NC}"

# Check if GitHub repo URL is provided
if [ -n "$GITHUB_REPO_URL" ]; then
    BRANCH="${GITHUB_BRANCH:-main}"
    echo -e "${YELLOW}Pulling latest code from GitHub...${NC}"
    echo "Repository: $GITHUB_REPO_URL"
    echo "Branch: $BRANCH"
    
    cd /app
    
    # Check if it's a fresh clone or existing repo
    if [ -d ".git" ]; then
        echo -e "${YELLOW}Existing repository found, fetching and pulling...${NC}"
        git fetch origin "$BRANCH" 2>&1 || {
            echo -e "${RED}Failed to fetch from GitHub. Continuing with existing code...${NC}"
        }
        
        git reset --hard "origin/$BRANCH" 2>&1 || {
            echo -e "${RED}Failed to reset to remote branch. Continuing with existing code...${NC}"
        }
    else
        echo -e "${YELLOW}No git repository found, cloning...${NC}"
        # Create temp directory for clone
        TEMP_DIR=$(mktemp -d)
        trap "rm -rf $TEMP_DIR" EXIT
        
        git clone --branch "$BRANCH" --depth 1 "$GITHUB_REPO_URL" "$TEMP_DIR" 2>&1 || {
            echo -e "${RED}Failed to clone repository. Continuing without GitHub sync...${NC}"
            cd /app
            exec "$@"
        }
        
        # Copy contents from cloned repo, preserving /app/data
        cp -r "$TEMP_DIR"/* /app/ 2>/dev/null || true
        cp -r "$TEMP_DIR"/.[^.]* /app/ 2>/dev/null || true
    fi
    
    echo -e "${GREEN}GitHub sync complete!${NC}"
    
    # Reinstall dependencies if requirements.txt changed
    if [ -f "requirements.txt" ]; then
        echo -e "${YELLOW}Checking for dependency updates...${NC}"
        pip install --user --no-cache-dir -q -r requirements.txt 2>&1 || {
            echo -e "${RED}Failed to install dependencies, proceeding anyway...${NC}"
        }
    fi
else
    echo -e "${YELLOW}GITHUB_REPO_URL not set. Skipping GitHub sync.${NC}"
fi

echo -e "${GREEN}Starting application...${NC}"

# Run the application
if [ "$RELOAD_ON_CHANGE" = "true" ]; then
    echo "Starting with hot-reload enabled"
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app/app
else
    echo "Starting production mode"
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
