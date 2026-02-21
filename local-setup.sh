#!/bin/bash

# Local Storage Setup Script
# Quick setup for development/testing with local directories

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Local Storage Setup Script${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 1. Create directories
echo -e "${YELLOW}Creating directory structure...${NC}"
mkdir -p documents
mkdir -p documents_archive
mkdir -p documents_deep_archive
mkdir -p iceberg_warehouse
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# 2. Set permissions
echo -e "${YELLOW}Setting appropriate permissions...${NC}"
chmod 755 documents documents_archive documents_deep_archive iceberg_warehouse
echo -e "${GREEN}✓ Permissions set${NC}"
echo ""

# 3. Create config.yaml if it doesn't exist
if [ ! -f "config.yaml" ]; then
    echo -e "${YELLOW}Creating config.yaml...${NC}"
    cat > config.yaml << 'EOF'
app:
  name: Cloud Document Archive
  debug: true
  host: 0.0.0.0
  port: 8000

storage:
  provider: local
  
  local:
    storage_path: ./documents
    archive_path: ./documents_archive
    deep_archive_path: ./documents_deep_archive

database:
  url: sqlite:///./document_archive.db

iceberg:
  warehouse_path: ./iceberg_warehouse
  enable_local_mode: true
EOF
    echo -e "${GREEN}✓ config.yaml created${NC}"
else
    echo -e "${YELLOW}config.yaml already exists, skipping${NC}"
fi
echo ""

# 4. Create .gitignore entries
echo -e "${YELLOW}Updating .gitignore...${NC}"
if [ -f ".gitignore" ]; then
    for dir in documents documents_archive documents_deep_archive iceberg_warehouse; do
        if ! grep -q "^$dir/$" .gitignore; then
            echo "$dir/" >> .gitignore
        fi
    done
    echo "*.db" >> .gitignore 2>/dev/null || true
    echo -e "${GREEN}✓ .gitignore updated${NC}"
else
    cat > .gitignore << 'EOF'
# Local storage directories
documents/
documents_archive/
documents_deep_archive/
iceberg_warehouse/

# Database files
*.db

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db
EOF
    echo -e "${GREEN}✓ .gitignore created${NC}"
fi
echo ""

# 5. Setup Python environment
echo -e "${YELLOW}Checking Python environment...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python 3 not found. Please install Python 3.8+${NC}"
else
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
    
    # Check for virtual environment
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv venv
        echo -e "${GREEN}✓ Virtual environment created${NC}"
        
        # Activate and install dependencies
        echo -e "${YELLOW}Activating virtual environment...${NC}"
        source venv/bin/activate
        
        echo -e "${YELLOW}Installing dependencies...${NC}"
        if [ -f "requirements.txt" ]; then
            pip install -q -r requirements.txt
            echo -e "${GREEN}✓ Dependencies installed${NC}"
        fi
    else
        echo -e "${YELLOW}Virtual environment already exists${NC}"
        echo -e "${YELLOW}To activate: source venv/bin/activate${NC}"
    fi
fi
echo ""

# 6. Create sample test document
echo -e "${YELLOW}Creating sample test document...${NC}"
echo "Sample test document created at $(date)" > "_sample_test.txt"
echo -e "${GREEN}✓ Sample document created at _sample_test.txt${NC}"
echo ""

# 7. Display summary
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "📁 Directory Structure:"
echo "   documents/             - Standard tier (active)"
echo "   documents_archive/     - Archive tier (90+ days)"
echo "   documents_deep_archive/ - Deep archive (365+ days)"
echo "   iceberg_warehouse/     - Iceberg metadata"
echo ""
echo "⚙️  Configuration:"
echo "   config.yaml - Local storage configuration"
echo ""
echo "🚀 Next Steps:"
echo "   1. Activate virtual environment: source venv/bin/activate"
echo "   2. Run the application: python -m app.main"
echo "   3. Open http://localhost:8000 in browser"
echo "   4. See LOCAL_STORAGE.md for API examples"
echo ""
echo "📊 Test Upload:"
echo "   curl -X POST http://localhost:8000/archive \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"document_base64\": \"SGVsbG8gV29ybGQh\", \"filename\": \"test.txt\"}'"
echo ""
echo -e "${GREEN}Happy archiving! 📚${NC}"
