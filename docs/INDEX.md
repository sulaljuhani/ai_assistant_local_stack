# Documentation Index

Complete documentation for the AI Assistant Local Stack. This index covers all active documentation - historical documents have been moved to `archive/`.

## 📋 Quick Navigation

### 🚀 Getting Started
- [Main README](../README.md) - Project overview and quick start
- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Step-by-step deployment instructions
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- [Production Readiness Report](reports/PRODUCTION_READINESS_REPORT.md) - Security audit and deployment checklist

### 🤖 AI Agents
- [LangGraph Flow Diagram](LANGGRAPH_FLOW_DIAGRAM.md) - ⭐ Visual architecture and routing strategies
- [LangGraph Multi-Agent Plan](LANGGRAPH_MULTI_AGENT_PLAN.md) - Multi-agent architecture overview
- [LangGraph Architecture](../containers/langgraph-agents/ARCHITECTURE.md) - Technical implementation details
- [Prompt Guide](../containers/langgraph-agents/PROMPT_GUIDE.md) - How to modify agent prompts
- [N8N to Python Migration](N8N_TO_PYTHON_MIGRATION_PLAN.md) - Complete migration documentation

### 🔌 API & Integration
- [API Documentation](API_DOCUMENTATION.md) - REST API reference
- [Integration FAQ](INTEGRATION_FAQ.md) - Common integration questions
- [OpenWebUI Integration](../openwebui/README.md) - OpenWebUI setup guide
- [OpenWebUI Quick Start](../openwebui/QUICK_START.md) - Fast setup instructions
- [OpenWebUI Adapter](../openwebui/adapter/README.md) - Adapter service details

### 🗄️ Data & Storage
- [Database Migrations](../migrations/README.md) - PostgreSQL schema and migrations
- [MCP Server](../containers/mcp-server/README.md) - Database tools via Model Context Protocol
- [Qdrant Setup](../scripts/qdrant/README.md) - Vector database initialization
- [Vault Watcher](../scripts/vault-watcher/README.md) - Obsidian file monitoring

### 🏗️ System Architecture
- [Container Architecture](../unraid-templates/CONTAINER_ARCHITECTURE.md) - System architecture overview
- [unRAID Templates](../unraid-templates/README.md) - Container deployment templates
- [Complete Structure](review/COMPLETE_STRUCTURE.md) - Full system architecture

### 📊 Reports & Analysis
- [Production Readiness Report](reports/PRODUCTION_READINESS_REPORT.md) - Security audit and deployment status
- [Security Audit Findings](review/SECURITY_AUDIT_FINDINGS.md) - Detailed security findings
- [Code Review Report](reports/CODE_REVIEW_REPORT.md) - Comprehensive codebase analysis
- [Code Review Summary](review/CODE_REVIEW_SUMMARY.md) - Review findings summary
- [Duplication Analysis](reports/DUPLICATION_ANALYSIS.md) - Code quality assessment

### 🔧 Development & Testing
- [OpenMemory Comparison](OPENMEMORY_COMPARISON.md) - Memory system analysis
- [Testing Guide](../tests/README.md) - Test scripts and usage
- [Technical Q&A](review/ANSWERS_TO_YOUR_QUESTIONS.md) - Technical questions answered

### 📂 Archived Documentation
Historical and completed implementation documentation in `archive/`:
- **Phase Implementation Plans**: PHASE_1-4_IMPLEMENTATION.md
- **Gap Analysis**: GAPS_QUICK_REFERENCE.md, ARCHITECTURE_GAPS_ANALYSIS.md
- **Feature Docs**: FOOD_LOG_FEATURE.md, FOOD_TRACKER_UPDATES.md
- **Legacy Implementations**: PYDANTIC_AI_AGENT_GUIDE.md, PYDANTIC_AI_IMPLEMENTATION.md
- **n8n Migration**: N8N_WORKFLOW_SECURITY_FIX_GUIDE.md
- **WebUI Planning**: CUSTOM_WEBUI_PLAN.md
- **Deployment**: PRE_DEPLOYMENT_CHECKLIST.md

LangGraph implementation summaries in `../containers/langgraph-agents/archive/`:
- Tool integration and event tools documentation
- Refactoring summaries
- Implementation plans

## 📊 Statistics

- **Total Documentation**: 25+ files, 18,773 lines
- **Code Coverage**: 94 files total
  - Python: 25 files (7,207 lines)
  - Bash: 10 files (1,969 lines)
  - SQL: 10 files (1,232 lines)
  - n8n: 21 workflows (6,292 lines)

## 🔍 Find What You Need

### I want to...
- **Deploy the system** → [Deployment Guide](DEPLOYMENT_GUIDE.md) or [Main README](../README.md)
- **Understand security** → [Production Readiness Report](reports/PRODUCTION_READINESS_REPORT.md)
- **Understand agent flow** → [LangGraph Flow Diagram](LANGGRAPH_FLOW_DIAGRAM.md) ⭐
- **Modify agent prompts** → [Prompt Guide](../containers/langgraph-agents/PROMPT_GUIDE.md)
- **Fix issues** → [Troubleshooting Guide](TROUBLESHOOTING.md)
- **Understand architecture** → [Complete Structure](review/COMPLETE_STRUCTURE.md)
- **Review code quality** → [Code Review Report](reports/CODE_REVIEW_REPORT.md)
- **Learn about containers** → [Container Architecture](../unraid-templates/CONTAINER_ARCHITECTURE.md)
- **Integrate with OpenWebUI** → [OpenWebUI Quick Start](../openwebui/QUICK_START.md)

## 📝 Documentation Standards

All documentation in this project follows these standards:
- **Complete**: Every component has its own README
- **Accurate**: Kept in sync with code changes
- **Practical**: Includes examples and use cases
- **Organized**: Grouped by topic and purpose

## 🆘 Getting Help

1. Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review the relevant component README
3. Check the [Code Review Report](reports/CODE_REVIEW_REPORT.md) for known limitations
4. Review recent commits for changes

## 🔄 Recent Updates

- **Documentation Reorganized**: Historical docs moved to `archive/` folders
- **Database Schema Added**: Complete schema documented in main README
- **Agent Flow Diagram**: New comprehensive visual documentation
- **Security Audit Complete**: All 7 critical issues resolved
- **Production Ready**: System validated and tested
