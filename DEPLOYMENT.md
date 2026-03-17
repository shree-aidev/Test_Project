# RAG Healthcare Chat Application - Deployment Guide

## Overview

This guide covers deployment strategies for the RAG-powered healthcare chat application in various environments.

## Local Development

### Quick Setup (Windows)
```bash
setup.bat
python quickstart.py
python main.py
```

### Quick Setup (Linux/Mac)
```bash
chmod +x setup.sh
./setup.sh
source venv/bin/activate
python quickstart.py
python main.py
```

### Manual Setup
```bash
# Create virtual environment
python -m venv venv

# Activate
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

## Docker Deployment

### Single Container

Build image:
```bash
docker build -t rag-healthcare-chat:latest .
```

Run container:
```bash
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/chroma_store:/app/chroma_store \
  --name rag-app \
  rag-healthcare-chat:latest
```

### Docker Compose

Start application:
```bash
docker-compose up -d
```

Stop application:
```bash
docker-compose down
```

View logs:
```bash
docker-compose logs -f
```

## Production Deployment

### Using Gunicorn

```bash
# Install gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn -w 4 \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  main:app
```

### Using Nginx Reverse Proxy

```nginx
upstream rag_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name rag-api.example.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://rag_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running requests
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # CORS handling for preflight requests
    if ($request_method = 'OPTIONS') {
        return 204;
    }
}
```

### Using Systemd (Linux)

Create `/etc/systemd/system/rag-app.service`:

```ini
[Unit]
Description=RAG Healthcare Chat Application
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/rag-app
ExecStart=/opt/rag-app/venv/bin/python main.py
Restart=on-failure
RestartSec=10

# Environment variables
Environment="API_HOST=0.0.0.0"
Environment="API_PORT=8000"
Environment="API_DEBUG=False"

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable rag-app
sudo systemctl start rag-app
```

## Kubernetes Deployment

### Deployment YAML

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-healthcare-chat
  labels:
    app: rag-chat

spec:
  replicas: 3
  
  selector:
    matchLabels:
      app: rag-chat
  
  template:
    metadata:
      labels:
        app: rag-chat
    
    spec:
      containers:
      - name: rag-app
        image: rag-healthcare-chat:latest
        imagePullPolicy: IfNotPresent
        
        ports:
        - containerPort: 8000
          name: http
        
        env:
        - name: API_HOST
          value: "0.0.0.0"
        - name: API_PORT
          value: "8000"
        - name: API_DEBUG
          value: "false"
        - name: TEMPERATURE
          value: "0.7"
        
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        
        volumeMounts:
        - name: data
          mountPath: /app/data
        - name: chroma-store
          mountPath: /app/chroma_store
      
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: rag-data-pvc
      - name: chroma-store
        persistentVolumeClaim:
          claimName: rag-chroma-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: rag-healthcare-chat

spec:
  type: LoadBalancer
  selector:
    app: rag-chat
  
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
```

Deploy to Kubernetes:
```bash
kubectl apply -f deployment.yaml
```

## Environment Configuration for Production

Create production `.env`:

```env
# Security
API_DEBUG=False

# API
API_HOST=0.0.0.0
API_PORT=8000

# LLM
LLAMA_MODEL_PATH=/opt/models/llama-model
TEMPERATURE=0.5
MAX_TOKENS=500

# Embeddings
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Vector DB
CHROMA_DB_PATH=/data/chroma_store
COLLECTION_NAME=Humana_chat_docs

# PDF
PDF_DATA_FOLDER=/data/pdfs
MAX_PDF_SIZE_MB=100

# Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

## Monitoring and Logging

### Health Endpoint
```bash
curl http://localhost:8000/health
```

### Application Logs (Docker)
```bash
docker-compose logs -f rag-app
```

### Application Logs (Systemd)
```bash
journalctl -u rag-app -f
```

## Performance Optimization

### Database Optimization
- Index frequently queried fields
- Use appropriate chunk sizes (1000-2000 characters)
- Batch process documents

### API Optimization
- Enable gzip compression
- Use CDN for static files
- Implement request cashing
- Rate limiting for production

### Model Optimization
- Use quantized model versions
- GPU acceleration if available
- Model caching
- Batch processing

## Backup and Recovery

### Backup ChromaDB
```bash
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz chroma_store/
```

### Backup PDF Data
```bash
tar -czf pdfs_backup_$(date +%Y%m%d).tar.gz data/
```

### Automated Backup (Cron)
```bash
0 2 * * * tar -czf /backups/rag_backup_$(date +\%Y\%m\%d).tar.gz /app/data /app/chroma_store
```

## Security Considerations

### HTTPS Setup
```nginx
listen 443 ssl http2;
ssl_certificate /etc/ssl/certs/certificate.crt;
ssl_certificate_key /etc/ssl/private/private.key;
```

### API Key Authentication (Optional)
Add to `main.py`:
```python
from fastapi.security import HTTPBearer, HTTPAuthCredentials

security = HTTPBearer()

@app.post("/chat")
async def chat(request: ChatRequest, credentials: HTTPAuthCredentials = Depends(security)):
    # Validate API key
    if credentials.credentials != os.getenv("API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Process request
```

### CORS Configuration
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

## Troubleshooting

### Out of Memory
- Reduce CHUNK_SIZE
- Use quantized models
- Reduce concurrent workers

### Slow Responses
- Check embeddings model performance
- Verify ChromaDB indices
- Monitor CPU/GPU usage

### Connection Issues
- Check network connectivity
- Verify firewall rules
- Check DNS resolution

## Scaling

### Horizontal Scaling
- Load balance across multiple instances
- Shared ChromaDB (with persistence)
- Shared PDF storage

### Vertical Scaling
- Increase CPU/GPU resources
- Increase memory allocation
- Use faster storage (SSD)

## Maintenance

### Regular Tasks
- Monitor disk space
- Review and archive old documents
- Update dependencies
- Check application health
- Review error logs

### Update Process
```bash
# Pull latest code
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart application
docker-compose restart
# or
systemctl restart rag-app
```

## Support

For deployment issues:
1. Check logs for error messages
2. Verify environment configuration
3. Review README.md documentation
4. Check API health endpoint

---

Version: 1.0.0
Last Updated: 2026-03-17
