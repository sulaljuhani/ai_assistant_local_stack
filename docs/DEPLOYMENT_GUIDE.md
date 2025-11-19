# Deployment Guide

Complete guide for deploying the AI Assistant Local Stack from scratch.

## Prerequisites

### System Requirements

- **OS**: Linux (Ubuntu 22.04+ recommended), macOS, or Windows with WSL2
- **RAM**: Minimum 8GB, recommended 16GB+
- **Storage**: 20GB+ free space
- **CPU**: 4+ cores recommended

### Required Software

1. **Docker** (v20.10+)
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

2. **Docker Compose** (v2.0+)
```bash
# Verify installation
docker --version
docker-compose --version
```

3. **Git**
```bash
sudo apt-get install git  # Ubuntu/Debian
# or
brew install git          # macOS
```

---

## Quick Start (5 minutes)

For those who want to get running immediately:

```bash
# 1. Clone repository
git clone https://github.com/yourusername/ai_assistant_local_stack.git
cd ai_assistant_local_stack

# 2. Configure environment
cp .env.example .env.local-stack
# Edit .env.local-stack with your settings (use defaults for quick start)

# 3. Start all services
docker-compose up -d

# 4. Wait for services to initialize (60-90 seconds)
sleep 90

# 5. Run migrations
cd migrations && ./run-migrations.sh && cd ..

# 6. Verify services
docker-compose ps

# 7. Open n8n UI
open http://localhost:5678
```

---

## Detailed Installation Steps

See full documentation at: [https://github.com/yourusername/ai_assistant_local_stack](https://github.com/yourusername/ai_assistant_local_stack)

For troubleshooting, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

