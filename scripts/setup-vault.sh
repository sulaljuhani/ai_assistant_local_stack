#!/bin/bash
# AI Stack - Obsidian Vault Setup
# Creates Obsidian-compatible vault structure for AI Stack

set -e

# Configuration
VAULT_DIR="${VAULT_DIR:-/mnt/user/appdata/ai_stack/vault}"

echo "════════════════════════════════════════════════════════════"
echo "  AI Stack - Obsidian Vault Setup"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Target directory: $VAULT_DIR"
echo ""

# Create vault directory
mkdir -p "$VAULT_DIR"

# Create folder structure
echo "📁 Creating folder structure..."

mkdir -p "$VAULT_DIR/daily"
mkdir -p "$VAULT_DIR/projects"
mkdir -p "$VAULT_DIR/references"
mkdir -p "$VAULT_DIR/templates"
mkdir -p "$VAULT_DIR/attachments"
mkdir -p "$VAULT_DIR/.obsidian"

echo "  ✓ Created folders"

# Create .obsidian configuration
echo "⚙️  Creating Obsidian configuration..."

# app.json
cat > "$VAULT_DIR/.obsidian/app.json" <<'EOF'
{
  "livePreview": true,
  "readableLineLength": true,
  "strictLineBreaks": false,
  "showFrontmatter": true,
  "defaultViewMode": "preview",
  "attachmentFolderPath": "attachments",
  "newLinkFormat": "relative",
  "useMarkdownLinks": true
}
EOF

# workspace.json (minimal)
cat > "$VAULT_DIR/.obsidian/workspace.json" <<'EOF'
{
  "main": {
    "id": "ai-stack-main",
    "type": "split",
    "children": [
      {
        "id": "ai-stack-leaf",
        "type": "leaf",
        "state": {
          "type": "markdown",
          "state": {
            "file": "README.md",
            "mode": "source"
          }
        }
      }
    ]
  },
  "left": {
    "id": "ai-stack-left",
    "type": "split",
    "children": [
      {
        "id": "ai-stack-file-explorer",
        "type": "leaf",
        "state": {
          "type": "file-explorer",
          "state": {}
        }
      }
    ]
  },
  "active": "ai-stack-leaf"
}
EOF

echo "  ✓ Created Obsidian config"

# Create template files
echo "📝 Creating templates..."

# Daily note template
cat > "$VAULT_DIR/templates/daily-note.md" <<'EOF'
---
date: {{date}}
tags: [daily]
---

# {{date:YYYY-MM-DD}}

## 📅 Schedule
-

## ✅ Tasks
- [ ]

## 📝 Notes


## 💭 Reflections


---
Created: {{date}} {{time}}
EOF

# Project template
cat > "$VAULT_DIR/templates/project.md" <<'EOF'
---
title:
status: planning
tags: [project]
created: {{date}}
---

# {{title}}

## 🎯 Goal


## 📋 Tasks
- [ ]

## 📝 Notes


## 🔗 Related
-

---
Created: {{date}} {{time}}
EOF

# Reference template
cat > "$VAULT_DIR/templates/reference.md" <<'EOF'
---
title:
tags: [reference]
source:
created: {{date}}
---

# {{title}}

## Summary


## Details


## Examples


## References
-

---
Created: {{date}} {{time}}
EOF

echo "  ✓ Created templates"

# Create README
echo "📖 Creating README..."

cat > "$VAULT_DIR/README.md" <<'EOF'
# AI Stack Vault

Welcome to your AI Stack knowledge vault! This vault is integrated with:

- **AnythingLLM** - Chat with RAG over your notes
- **OpenMemory** - Long-term memory across all your AI conversations
- **File Watcher** - Auto-embedding when you edit files

## 📁 Folder Structure

- `daily/` - Daily notes and journaling
- `projects/` - Project documentation and planning
- `references/` - Reference materials, guides, how-tos
- `templates/` - Note templates
- `attachments/` - Images, PDFs, and other files

## 🚀 Getting Started

1. **Create a daily note**: Use the daily-note template
2. **Start a project**: Use the project template
3. **Add references**: Document what you learn

## ⚡ Features

### Automatic Embedding
When you save a markdown file, it's automatically:
1. Detected by the file watcher
2. Embedded using nomic-embed-text (768 dims)
3. Stored in Qdrant vector database
4. Made searchable in AnythingLLM

### Integration with AI Stack
Your notes are accessible via:
- **AnythingLLM chat**: "What did I write about Docker?"
- **MCP tools**: `search_notes("docker")`
- **Vector search**: Semantic similarity matching

### Best Practices
- Use descriptive filenames
- Add tags in frontmatter for organization
- Link related notes with `[[note name]]`
- Keep attachments in `attachments/` folder

## 📝 Templates

Access templates from the ribbon:
- **Daily Note** - Daily journal entry
- **Project** - Project documentation
- **Reference** - Knowledge reference

## 🔍 Search

### In Obsidian
- Quick switcher: `Ctrl/Cmd + O`
- Search: `Ctrl/Cmd + Shift + F`
- Graph view: `Ctrl/Cmd + G`

### In AnythingLLM
Ask questions like:
- "Summarize my notes about Python"
- "What projects am I working on?"
- "Show me my notes from last week"

## 💡 Tips

1. **Use frontmatter** for metadata (tags, dates, status)
2. **Link liberally** to create knowledge graph
3. **Review regularly** to reinforce learning
4. **Tag consistently** for better organization

## 🛠️ Technical Details

- **Format**: Markdown (`.md`)
- **Encoding**: UTF-8
- **Line endings**: LF (Unix style)
- **Embedding model**: nomic-embed-text (768 dims)
- **Vector DB**: Qdrant (cosine similarity)

---

Happy note-taking! 📚✨
EOF

echo "  ✓ Created README"

# Create initial daily note
CURRENT_DATE=$(date +%Y-%m-%d)
cat > "$VAULT_DIR/daily/$CURRENT_DATE.md" <<EOF
---
date: $CURRENT_DATE
tags: [daily]
---

# $CURRENT_DATE

## 📅 Schedule
-

## ✅ Tasks
- [ ] Set up AI Stack
- [ ] Explore Obsidian vault

## 📝 Notes

Started using AI Stack today! This vault is integrated with:
- AnythingLLM for chat with RAG
- OpenMemory for long-term AI memory
- Automatic embedding of all notes

## 💭 Reflections

Looking forward to building a personal knowledge base that I can actually search and use effectively.

---
Created: $(date '+%Y-%m-%d %H:%M:%S')
EOF

echo "  ✓ Created first daily note"

# Set permissions
chmod -R 755 "$VAULT_DIR"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Vault Setup Complete!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📂 Vault location: $VAULT_DIR"
echo ""
echo "Next steps:"
echo "  1. Open Obsidian"
echo "  2. Click 'Open folder as vault'"
echo "  3. Select: $VAULT_DIR"
echo "  4. Start taking notes!"
echo ""
echo "Your notes will be automatically:"
echo "  • Embedded using nomic-embed-text"
echo "  • Stored in Qdrant vector database"
echo "  • Searchable in AnythingLLM"
echo ""
