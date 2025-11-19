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
