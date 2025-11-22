# 🚀 Frontend Deployment Guide

## ✅ Pre-Deployment Validation

All critical files and configurations have been validated:

### Build Verification
- ✅ Production build succeeds: `npm run build`
- ✅ Bundle size: 255.62 KB (82.88 KB gzipped)
- ✅ TypeScript compilation passes
- ✅ All dependencies installed correctly

### Configuration Files
- ✅ **Dockerfile** - Multi-stage build with correct dependency installation
- ✅ **nginx.conf** - SPA routing, security headers, asset caching
- ✅ **.dockerignore** - Excludes unnecessary files
- ✅ **docker-compose.yml** - Frontend service configured
- ✅ **unRAID template** - Ready for installation

### Critical Fixes Applied
1. ✅ Fixed Dockerfile dependency installation (changed `npm ci --only=production` to `npm ci`)
2. ✅ Updated all port references from 8080 to 8000
3. ✅ Fixed TypeScript verbatimModuleSyntax errors
4. ✅ Fixed Tailwind PostCSS plugin configuration

---

## 🐳 Docker Deployment

### Option 1: Docker Compose (Recommended)

```bash
# Navigate to project root
cd /path/to/ai_stack

# Build and start frontend
docker-compose build frontend
docker-compose up -d frontend

# Check logs
docker logs ai-stack-frontend -f

# Verify health
docker ps | grep frontend
curl http://localhost:3001
```

### Option 2: Standalone Docker

```bash
# Build image
cd frontend
docker build -t ai-stack-frontend .

# Run container
docker run -d \
  --name ai-stack-frontend \
  --network ai-stack-network \
  -p 3001:3001 \
  -e VITE_BACKEND_URL=http://langgraph-agents:8000 \
  ai-stack-frontend

# Check logs
docker logs ai-stack-frontend -f
```

### Option 3: unRAID Template

1. Open unRAID web interface
2. Go to Docker tab
3. Click "Add Container"
4. Select "my-frontend" template
5. Adjust paths if needed (default: `/mnt/user/appdata/ai_stack/frontend`)
6. Click "Apply"

---

## ⚙️ Environment Configuration

### Docker Network (IMPORTANT)

The frontend container **must** be on the same Docker network as the backend:

```bash
# Verify network exists
docker network ls | grep ai-stack-network

# Create if missing
docker network create ai-stack-network

# Verify containers are connected
docker network inspect ai-stack-network
```

### Environment Variables

The build-time variable `VITE_BACKEND_URL` determines the API endpoint:

| Scenario | VITE_BACKEND_URL | When to Use |
|----------|------------------|-------------|
| **Local Development** | `http://localhost:8000` | Running `npm run dev` |
| **Docker Internal** | `http://langgraph-agents:8000` | Containers on same network |
| **External Access** | `http://your-server-ip:8000` | Accessing from different machine |
| **Production Domain** | `https://your-domain.com/api` | With reverse proxy |

**IMPORTANT:** This is a **build-time** variable. To change it after build, you must rebuild the Docker image.

---

## 🔍 Health Checks

### Container Health

```bash
# Check container status
docker ps | grep frontend

# Check health status
docker inspect ai-stack-frontend | grep -A 10 Health

# Manual health check
docker exec ai-stack-frontend wget --spider http://localhost:3001
```

### Backend Connection

```bash
# Test backend from host
curl http://localhost:8000/health

# Test backend from frontend container
docker exec ai-stack-frontend wget -qO- http://langgraph-agents:8000/health
```

### Frontend Accessibility

```bash
# Test from host
curl -I http://localhost:3001

# Test from browser
open http://localhost:3001
# Or visit: http://your-server-ip:3001
```

---

## 🐛 Troubleshooting

### Issue 1: Frontend Container Won't Start

**Symptoms:**
- Container exits immediately
- `docker ps` doesn't show frontend

**Solutions:**
```bash
# Check logs for errors
docker logs ai-stack-frontend

# Verify port 3001 is available
netstat -tulpn | grep 3001

# Check if image built correctly
docker images | grep frontend
```

### Issue 2: "Network error: No response from server"

**Symptoms:**
- Frontend loads but can't connect to backend
- Settings modal shows "Offline"

**Solutions:**

1. **Verify backend is running:**
   ```bash
   docker ps | grep langgraph
   curl http://localhost:8000/health
   ```

2. **Check Docker network:**
   ```bash
   docker network inspect ai-stack-network
   # Both frontend and langgraph-agents should be listed
   ```

3. **Test connectivity from frontend container:**
   ```bash
   docker exec ai-stack-frontend ping langgraph-agents
   docker exec ai-stack-frontend wget -qO- http://langgraph-agents:8000/health
   ```

4. **Check CORS configuration in backend:**
   Backend must allow requests from `http://localhost:3001` (or your domain)
   ```bash
   # In backend .env
   CORS_ALLOWED_ORIGINS=http://localhost:3001,http://your-server-ip:3001
   ```

### Issue 3: 404 on Refresh

**Symptoms:**
- Direct URLs (e.g., `/conversation/123`) return 404
- Works only on home page

**Solution:**
This shouldn't happen as nginx.conf has `try_files` configured for SPA routing. If it does:

```bash
# Verify nginx config is loaded
docker exec ai-stack-frontend cat /etc/nginx/nginx.conf | grep try_files

# Restart container
docker restart ai-stack-frontend
```

### Issue 4: Assets Not Loading

**Symptoms:**
- Blank white screen
- Console shows 404 for JS/CSS files

**Solutions:**

1. **Check build artifacts exist:**
   ```bash
   docker exec ai-stack-frontend ls -la /usr/share/nginx/html
   docker exec ai-stack-frontend ls -la /usr/share/nginx/html/assets
   ```

2. **Verify nginx is serving files:**
   ```bash
   curl http://localhost:3001/assets/index-*.js
   ```

3. **Rebuild if needed:**
   ```bash
   docker-compose build --no-cache frontend
   docker-compose up -d frontend
   ```

### Issue 5: Slow Build Times

**Solution:**
Use Docker layer caching by ensuring package.json changes trigger only dependency reinstall:

```bash
# Clear build cache if needed
docker builder prune

# Rebuild with progress
docker-compose build --progress=plain frontend
```

---

## 🔧 Backend CORS Configuration

The backend needs to allow requests from the frontend domain. Add to backend `.env`:

```bash
# For local Docker deployment
CORS_ALLOWED_ORIGINS=http://localhost:3001

# For unRAID server
CORS_ALLOWED_ORIGINS=http://192.168.1.100:3001

# Multiple origins (comma-separated)
CORS_ALLOWED_ORIGINS=http://localhost:3001,http://192.168.1.100:3001,http://tower:3001
```

Restart backend after changing CORS:
```bash
docker restart langgraph-agents
```

---

## 📊 Monitoring

### Real-time Logs

```bash
# Frontend logs
docker logs -f ai-stack-frontend

# Backend logs (related to API calls)
docker logs -f langgraph-agents | grep "/chat"

# Combined logs
docker-compose logs -f frontend langgraph-agents
```

### Resource Usage

```bash
# Check container stats
docker stats ai-stack-frontend

# Expected usage:
# - CPU: < 1% (idle), 5-10% (active)
# - Memory: ~20-50 MB
# - Network: Variable based on usage
```

### Performance

```bash
# Test response time
time curl http://localhost:3001

# Check bundle load time (in browser)
# Open DevTools > Network > Disable cache > Refresh
# JS bundle should load in < 500ms on local network
```

---

## 🔄 Updates and Rebuilds

### When to Rebuild

Rebuild the Docker image when:
- Updating React components
- Changing Tailwind styles
- Modifying TypeScript code
- Updating dependencies
- Changing environment variables

### Rebuild Process

```bash
# 1. Stop container
docker-compose down frontend

# 2. Rebuild image
docker-compose build --no-cache frontend

# 3. Start container
docker-compose up -d frontend

# 4. Verify
docker logs ai-stack-frontend
curl http://localhost:3001
```

### Zero-Downtime Updates

For production, use rolling updates:

```bash
# Build new image with version tag
docker build -t ai-stack-frontend:v2 ./frontend

# Run new container on different port temporarily
docker run -d --name frontend-v2 -p 3002:3001 ai-stack-frontend:v2

# Test new version
curl http://localhost:3002

# Switch traffic (update docker-compose.yml or reverse proxy)
# Stop old container
docker stop ai-stack-frontend
```

---

## 📝 Deployment Checklist

Before deploying to production:

- [ ] Backend is running and accessible (`curl http://localhost:8000/health`)
- [ ] Docker network `ai-stack-network` exists
- [ ] CORS configured in backend `.env`
- [ ] Frontend `.env` has correct `VITE_BACKEND_URL` for deployment
- [ ] Port 3001 is available and not firewalled
- [ ] Build succeeds locally (`npm run build`)
- [ ] Dockerfile has been tested (even if just locally)
- [ ] nginx.conf is valid
- [ ] Health check endpoints work
- [ ] Browser localStorage is enabled (for conversation persistence)
- [ ] Mobile responsiveness tested (optional but recommended)

---

## 🚀 Post-Deployment Verification

After deployment, verify:

1. **Frontend loads:**
   ```bash
   curl -I http://your-server:3001
   # Should return: 200 OK
   ```

2. **Backend connectivity:**
   - Open Settings modal in UI
   - Should show "Online" status

3. **Chat functionality:**
   - Send a test message
   - Should receive response from agent
   - Check browser console for errors

4. **Persistence:**
   - Create a conversation
   - Refresh page
   - Conversation should still be visible

5. **Mobile responsive:**
   - Open on mobile device
   - Sidebar should slide in as drawer
   - Touch targets should be 44px minimum

---

## 🔐 Security Considerations

### Nginx Security Headers

The following headers are configured in nginx.conf:
- `X-Frame-Options: SAMEORIGIN` - Prevents clickjacking
- `X-Content-Type-Options: nosniff` - Prevents MIME sniffing
- `X-XSS-Protection: 1; mode=block` - XSS protection
- `Referrer-Policy: strict-origin-when-cross-origin` - Privacy
- `server_tokens off` - Hides nginx version

### Network Security

For production:
- Use HTTPS (add reverse proxy like Nginx/Traefik)
- Restrict backend API to internal network only
- Use firewall rules to limit port 3001 access
- Consider VPN for remote access

### Data Security

- All data stored in browser localStorage (client-side)
- No sensitive data in frontend code
- API calls use standard HTTP (add HTTPS in production)
- No authentication in MVP (add in Phase 4)

---

## 📚 Additional Resources

- **Frontend README:** `/frontend/README.md`
- **Implementation Plan:** `/docs/CUSTOM_WEBUI_PLAN.md`
- **Backend Documentation:** `/containers/langgraph-agents/README.md`
- **Main README:** `/README.md`

---

## 🆘 Getting Help

If you encounter issues:

1. Check logs: `docker logs ai-stack-frontend -f`
2. Verify backend health: `curl http://localhost:8000/health`
3. Check Docker network: `docker network inspect ai-stack-network`
4. Review troubleshooting section above
5. Check browser console for frontend errors
6. Test API endpoints directly with curl

---

**Built for AI Stack - 100% local, privacy-first AI assistant** 🔒✨
