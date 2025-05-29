# COLMAP Integration Deployment Guide

## Overview

This guide covers the complete setup and deployment of the 3D Photogrammetry Flask application with COLMAP integration for Structure-from-Motion reconstruction.

## Quick Start

### 1. Install COLMAP

**macOS (Homebrew)**:
```bash
brew install colmap
```

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install colmap
```

**Windows**:
- Download from [https://demuc.de/colmap/](https://demuc.de/colmap/)
- Add to PATH

**Verify Installation**:
```bash
colmap -h
```

### 2. Install Python Dependencies

```bash
# Core dependencies
pip install Flask Flask-CORS exifread requests

# Computer vision (may take time to build)
pip install opencv-python numpy Pillow

# Or install from requirements file
pip install -r requirements.txt
```

### 3. Start the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Testing the Integration

### Health Check
```bash
curl http://localhost:5000/health
```

Should return status with `"colmap": true` if properly configured.

### Complete Workflow Test
```bash
python test_colmap_integration.py
```

## API Usage Examples

### 1. Upload Images
```bash
curl -X POST http://localhost:5000/upload \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg" \
  -F "files=@image3.jpg"
```

### 2. Start COLMAP Processing
```bash
curl -X POST http://localhost:5000/colmap/process \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "YOUR_SESSION_ID",
    "enable_dense_reconstruction": true,
    "max_image_size": 1920,
    "matcher_type": "exhaustive"
  }'
```

### 3. Monitor Progress
```bash
curl http://localhost:5000/colmap/status/YOUR_SESSION_ID
```

### 4. Get Results
```bash
curl http://localhost:5000/colmap/results/YOUR_SESSION_ID
```

## Configuration Options

### COLMAP Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enable_dense_reconstruction` | `true` | Generate dense point cloud |
| `enable_meshing` | `false` | Generate 3D mesh (experimental) |
| `max_image_size` | `1920` | Max image dimension for processing |
| `matcher_type` | `"exhaustive"` | Feature matching strategy |

### Processing Strategies

**Fast Processing** (Development/Testing):
```json
{
  "enable_dense_reconstruction": false,
  "max_image_size": 1024,
  "matcher_type": "sequential"
}
```

**High Quality** (Production):
```json
{
  "enable_dense_reconstruction": true,
  "max_image_size": 1920,
  "matcher_type": "exhaustive"
}
```

## File Structure

```
outputs/
├── colmap_session_SESSION_ID/
│   ├── images/              # Prepared input images
│   ├── sparse/             # Sparse reconstruction
│   │   └── 0/
│   │       ├── cameras.txt  # Camera parameters
│   │       ├── images.txt   # Image poses
│   │       └── points3D.txt # 3D points
│   ├── dense/              # Dense reconstruction
│   │   └── fused.ply       # Dense point cloud
│   └── mesh/               # Mesh generation
│       └── mesh.ply        # 3D mesh
```

## Troubleshooting

### Common Issues

**1. COLMAP Not Found**
```
Error: COLMAP executable not found
```
- Verify COLMAP installation: `colmap -h`
- Check PATH environment variable
- On Windows, ensure COLMAP is in system PATH

**2. Processing Fails with "No 3D models were reconstructed"**
- Ensure images have sufficient overlap (50-80%)
- Check image quality (not blurry, good lighting)
- Try different matcher type
- Verify minimum 3 images provided

**3. Out of Memory Errors**
- Reduce `max_image_size`
- Disable dense reconstruction for large image sets
- Process fewer images at once

**4. Slow Processing**
- Use `"matcher_type": "sequential"` for ordered image sequences
- Reduce `max_image_size`
- Disable dense reconstruction for faster sparse-only results

### Performance Optimization

**For Large Image Sets (>50 images)**:
- Use sequential matching
- Process in batches
- Consider hierarchical reconstruction

**For High-Resolution Images**:
- Set appropriate `max_image_size`
- Enable dense reconstruction only when needed
- Monitor system resources

### Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| 503 | COLMAP not available | Install/configure COLMAP |
| 400 | Invalid image set | Check image requirements |
| 404 | Session not found | Upload images first |
| 202 | Processing in progress | Wait for completion |

## Production Deployment

### Docker Deployment

1. **Create Dockerfile**:
```dockerfile
FROM ubuntu:22.04

# Install COLMAP
RUN apt-get update && \
    apt-get install -y colmap python3 python3-pip

# Copy application
COPY . /app
WORKDIR /app

# Install dependencies
RUN pip3 install -r requirements.txt

# Expose port
EXPOSE 5000

# Run application
CMD ["python3", "app.py"]
```

2. **Build and Run**:
```bash
docker build -t photogrammetry-app .
docker run -p 5000:5000 -v ./outputs:/app/outputs photogrammetry-app
```

### Environment Variables

```bash
export COLMAP_EXECUTABLE=/usr/local/bin/colmap
export MAX_UPLOAD_SIZE=52428800  # 50MB
export FLASK_ENV=production
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Security Considerations

1. **File Validation**: All uploaded files are validated
2. **Session Isolation**: Each session has isolated workspace
3. **Size Limits**: Configurable upload limits
4. **Path Sanitization**: Secure filename handling

## Monitoring and Logging

- Application logs: `logs/app.log`
- Progress tracking: Real-time via `/colmap/status` endpoint
- Health monitoring: `/health` endpoint

## Support and Resources

- COLMAP Documentation: [https://colmap.github.io/](https://colmap.github.io/)
- Sample Datasets: [https://colmap.github.io/datasets.html](https://colmap.github.io/datasets.html)
- Computer Vision Datasets: [https://cvg.ethz.ch/research/local-features/](https://cvg.ethz.ch/research/local-features/)