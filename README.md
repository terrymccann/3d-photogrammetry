# 3D Photogrammetry Web Application

A Flask-based web application for 3D photogrammetry processing using OpenCV, NumPy, and COLMAP for Structure-from-Motion reconstruction.

## Project Structure

```
3D-photogrammetry/
├── app.py                      # Main Flask application
├── colmap_wrapper.py           # COLMAP integration wrapper
├── image_preprocessor.py       # Image preprocessing utilities
├── test_colmap_integration.py  # Test script for COLMAP functionality
├── requirements.txt            # Python dependencies
├── README.md                  # Project documentation
├── uploads/                   # Directory for uploaded images
├── outputs/                   # Directory for processed results (including COLMAP)
├── static/                    # Static files (CSS, JS, images)
├── templates/                 # Flask HTML templates
└── logs/                      # Application log files
```

## Features

- **Multiple File Upload**: Secure multi-image upload with session-based organization
- **File Validation**: Comprehensive image validation (JPG, PNG, JPEG) with security checks
- **Session Management**: Unique session IDs for organizing related uploads
- **Health Check**: Comprehensive health monitoring endpoint
- **CORS Support**: Cross-Origin Resource Sharing for frontend integration
- **Error Handling**: Robust error handling and detailed logging
- **Image Preprocessing**: Advanced image preprocessing with quality assessment
- **COLMAP Integration**: Complete Structure-from-Motion pipeline using COLMAP
- **3D Reconstruction**: Sparse and dense 3D reconstruction from images
- **Progress Tracking**: Real-time progress monitoring for long-running processes
- **RESTful API**: JSON-based API endpoints with detailed responses

## API Endpoints

### Core Endpoints
- `GET /` - Welcome message and API overview
- `GET /health` - Health check endpoint with system status
- `POST /upload` - Upload multiple images with session management
- `POST /preprocess` - Preprocess images with validation and optimization
- `GET /preprocess/<session_id>` - Get preprocessing results for a session
- `POST /process` - Start COLMAP 3D reconstruction processing
- `GET /status/<session_id>` - Get processing status (uploaded/processing/complete/error)
- `GET /download/<session_id>` - Download processed 3D models (OBJ, PLY formats)

### Advanced COLMAP Endpoints
- `POST /colmap/process` - Advanced COLMAP processing with detailed configuration
- `GET /colmap/status/<session_id>` - Detailed COLMAP progress with stage information
- `GET /colmap/results/<session_id>` - Get final reconstruction results
- `POST /colmap/cancel/<session_id>` - Cancel ongoing processing
- `POST /colmap/cleanup/<session_id>` - Clean up session data and temporary files

### Upload Endpoint Details

**POST /upload**
- **Content-Type**: `multipart/form-data`
- **Field Name**: `files` (supports multiple files)
- **Supported Formats**: JPG, JPEG, PNG
- **Max File Size**: 16MB per file
- **Security**: File signature validation and size checks

**Request Example**:
```bash
curl -X POST http://localhost:5000/upload \
  -F "files=@image1.jpg" \
  -F "files=@image2.png" \
  -F "files=@image3.jpeg"
```

**Response Example**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "upload_status": "success",
  "files_uploaded": 3,
  "files_failed": 0,
  "total_files": 3,
  "total_size": 2457600,
  "uploaded_files": [...]
}
```

### Process Endpoint Details

**POST /process**
- **Content-Type**: `application/json`
### Main Processing Endpoint Details

**POST /process**
- **Content-Type**: `application/json`
- **Required**: `session_id`
- **Optional Parameters**:
  - `enable_dense_reconstruction` (boolean, default: true)
  - `enable_meshing` (boolean, default: false)  
  - `max_image_size` (integer, default: 1920)
  - `matcher_type` (string, default: "exhaustive", options: "exhaustive", "sequential")

**Request Example**:
```bash
curl -X POST http://localhost:5000/process \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "enable_dense_reconstruction": true,
    "max_image_size": 1920,
    "matcher_type": "exhaustive"
  }'
```

**Response Example**:
```json
{
  "message": "Processing started",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "input_files_count": 5,
  "processing_parameters": {
    "enable_dense_reconstruction": true,
    "enable_meshing": false,
    "max_image_size": 1920,
    "matcher_type": "exhaustive"
  },
  "status_endpoint": "/status/550e8400-e29b-41d4-a716-446655440000"
}
```

**GET /status/<session_id>**
- **Purpose**: Get processing status with simple status values
- **Status Values**: `"uploaded"`, `"processing"`, `"complete"`, `"error"`
- **Returns**: Current status, messages, error details, and output files when complete

**Response Example**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "COLMAP processing started",
  "start_time": "2025-05-28T12:00:00",
  "end_time": null,
  "error": null,
  "output_files": [],
  "detailed_progress": {
    "stage": "sparse_reconstruction",
    "progress_percent": 45.0,
    "stage_message": "Performing sparse 3D reconstruction"
  }
}
```

**Status when Complete**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "complete",
  "message": "COLMAP processing completed successfully",
  "start_time": "2025-05-28T12:00:00",
  "end_time": "2025-05-28T12:04:15",
  "error": null,
  "output_files": [
    {
      "type": "sparse_model_cameras",
      "path": "/path/to/cameras.txt",
      "size": 1024
    },
    {
      "type": "dense_pointcloud",
      "path": "/path/to/fused.ply", 
      "size": 2458624
### Download Endpoint Details

**GET /download/<session_id>**
- **Purpose**: Download processed 3D models in multiple formats
- **Returns**: Compressed archive or individual file information
- **Supported Formats**: OBJ, PLY, MTL (materials)
- **Features**: Mesh cleaning, optimization, format conversion

**Response Example (Compressed Archive)**:
```bash
# Downloads a ZIP file containing all processed models
curl -O -J http://localhost:5000/download/SESSION_ID
# Results in: 3d_model_SESSION_ID.zip
```

**Response Example (Individual Files)**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "complete",
  "available_files": [
    {
      "type": "dense_pointcloud",
      "format": "obj",
      "size": 2458624,
      "download_url": "/download/SESSION_ID/file/fused.obj",
      "metadata": {
        "vertex_count": 125000,
        "face_count": 245000,
        "has_colors": true,
        "bounding_box": {
          "min": [-1.2, -0.8, -0.5],
          "max": [1.1, 0.9, 0.7],
          "center": [0.0, 0.0, 0.1]
        }
      }
    }
  ],
  "model_metadata": {
    "dense_pointcloud": {
      "vertex_count": 125000,
      "face_count": 245000,
      "file_size": 2458624,
      "format": "obj",
      "has_colors": true,
      "has_normals": false,
      "has_textures": true
    }
  }
}
```

**GET /download/<session_id>/file/<filename>**
- **Purpose**: Download individual model files
- **Examples**:
  ```bash
  # Download OBJ file
  curl -O http://localhost:5000/download/SESSION_ID/file/fused.obj
  
  # Download PLY file
  curl -O http://localhost:5000/download/SESSION_ID/file/fused.ply
  
  # Download material file
  curl -O http://localhost:5000/download/SESSION_ID/file/fused.mtl
  ```
    }
  ]
}
```
- **Required**: `session_id`

**Request Example**:
```bash
curl -X POST http://localhost:5000/process \
  -H "Content-Type: application/json" \
  -d '{"session_id": "550e8400-e29b-41d4-a716-446655440000"}'
```

### Preprocessing Endpoint Details

**POST /preprocess**
- **Content-Type**: `application/json`
- **Required**: `session_id`
- **Optional**: `max_dimension` (default: 1920)

**Features**:
- Image validation and quality assessment
- Automatic resizing to optimize processing
- EXIF data extraction (camera info, GPS, settings)
- Quality metrics calculation (brightness, contrast, sharpness)
- Blur detection and scoring
- Common format issue handling

**Request Example**:
```bash
curl -X POST http://localhost:5000/preprocess \
  -H "Content-Type: application/json" \
  -d '{"session_id": "550e8400-e29b-41d4-a716-446655440000", "max_dimension": 1920}'
```

**Response Example**:
```json
{
  "message": "Image preprocessing completed",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "preprocessing_results": {
    "statistics": {
      "total_images": 3,
      "processed_count": 3,
      "failed_count": 0,
      "average_dimensions": {"width": 1920, "height": 1440}
### COLMAP Endpoint Details

**POST /colmap/process**
- **Content-Type**: `application/json`
- **Required**: `session_id`
- **Optional Parameters**:
  - `enable_dense_reconstruction` (boolean, default: true)
  - `enable_meshing` (boolean, default: false)  
  - `max_image_size` (integer, default: 1920)
  - `matcher_type` (string, default: "exhaustive", options: "exhaustive", "sequential")

**Request Example**:
```bash
curl -X POST http://localhost:5000/colmap/process \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "enable_dense_reconstruction": true,
    "enable_meshing": false,
    "max_image_size": 1920,
    "matcher_type": "exhaustive"
  }'
```

**Response Example**:
```json
{
  "message": "COLMAP processing started",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "input_files_count": 5,
  "processing_parameters": {
    "enable_dense_reconstruction": true,
    "enable_meshing": false,
    "max_image_size": 1920,
    "matcher_type": "exhaustive"
  },
  "status_endpoint": "/colmap/status/550e8400-e29b-41d4-a716-446655440000",
  "results_endpoint": "/colmap/results/550e8400-e29b-41d4-a716-446655440000"
}
```

**GET /colmap/status/<session_id>**
- **Purpose**: Get real-time processing status and progress
- **Returns**: Detailed progress information including current stage and completion percentage

**Response Example**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "colmap_progress": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "stage": "sparse_reconstruction",
    "status": "running",
    "progress_percent": 45.0,
    "message": "Performing sparse 3D reconstruction",
    "start_time": "2025-05-28T12:00:00",
    "error_message": null,
    "output_files": []
  }
}
```

**GET /colmap/results/<session_id>**
- **Purpose**: Get final reconstruction results (only when processing is completed)
- **Returns**: Paths to generated 3D models and reconstruction data

**Response Example**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "processing_time": 245.7,
  "workspace_directory": "/path/to/outputs/colmap_session_550e8400...",
  "output_files": {
    "sparse_model": {
      "cameras": "/path/to/sparse/0/cameras.txt",
      "images": "/path/to/sparse/0/images.txt", 
      "points3D": "/path/to/sparse/0/points3D.txt"
    },
    "dense_pointcloud": "/path/to/dense/fused.ply",
    "mesh": null
  }
}
```
    },
    "processed_images": [...]
  }
}
```

**GET /preprocess/<session_id>**
- **Purpose**: Retrieve preprocessing results for a session
- **Returns**: Detailed preprocessing results including quality metrics

## Setup Instructions

### Prerequisites

1. **Install COLMAP**:
   
   **macOS (using Homebrew)**:
   ```bash
   brew install colmap
   ```
   
   **Ubuntu/Debian**:
   ```bash
   sudo apt-get install colmap
   ```
   
   **Windows**:
   - Download pre-built binaries from [https://demuc.de/colmap/](https://demuc.de/colmap/)
   - Or build from source following [COLMAP installation guide](https://colmap.github.io/install.html)

   **Verify Installation**:
   ```bash
## COLMAP 3D Reconstruction Workflow

The application integrates COLMAP to provide a complete Structure-from-Motion (SfM) pipeline:

### Processing Stages

1. **Feature Extraction**: 
   - Detects and describes keypoints in each image using SIFT features
   - Configurable image size and feature parameters
   - Progress: 10-25%

2. **Feature Matching**:
   - Matches features between image pairs
   - Supports exhaustive and sequential matching strategies
   - Progress: 25-45%

3. **Sparse Reconstruction**:
   - Estimates camera poses and creates sparse 3D point cloud
   - Bundle adjustment for optimization
   - Progress: 45-70%

4. **Dense Reconstruction** (Optional):
   - Creates dense point cloud using multi-view stereo
   - Significantly improves detail but requires more processing time
   - Progress: 70-90%

5. **Mesh Generation** (Optional):
   - Generates mesh from dense point cloud using Poisson reconstruction
   - Creates textured 3D model
   - Progress: 90-100%

### Output Files

**Sparse Reconstruction**:
- `cameras.txt`: Camera intrinsic parameters
- `images.txt`: Camera poses and image information  
- `points3D.txt`: 3D point coordinates and visibility

**Dense Reconstruction**:
- `fused.ply`: Dense 3D point cloud in PLY format

**Mesh** (if enabled):
- `mesh.ply`: 3D mesh in PLY format

### Processing Parameters

- **Image Size**: Maximum dimension for processing (trade-off between quality and speed)
- **Matcher Type**: 
  - `exhaustive`: Matches all image pairs (best quality, slower)
  - `sequential`: Matches consecutive images (faster, suitable for ordered sequences)
- **Dense Reconstruction**: Enable for detailed point clouds (slower but higher quality)
- **Meshing**: Enable for 3D mesh generation (experimental, requires dense reconstruction)
   colmap -h
   ```

### Application Setup

1. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python app.py
   ```

3. **Access the Application**:
   - Main API: `http://localhost:5000/`
   - Health Check: `http://localhost:5000/health`

4. **Test COLMAP Integration**:
   ```bash
   python test_colmap_integration.py
   ```

## Configuration

- **Max File Size**: 16MB per file
- **Allowed File Types**: JPG, JPEG, PNG (validated by file signature)
- **Upload Directory**: `uploads/` (organized by session ID)
- **Output Directory**: `outputs/`
- **Log Files**: `logs/app.log`
- **CORS**: Enabled for all origins
- **Session Management**: UUID-based unique session directories

## Dependencies

### Python Dependencies
- **Flask**: Web framework
- **Flask-CORS**: Cross-Origin Resource Sharing support
- **OpenCV**: Computer vision library for image processing
- **NumPy**: Numerical computing
- **Pillow**: Python Imaging Library for image manipulation
- **exifread**: EXIF data extraction from images
- **Werkzeug**: WSGI utilities
- **pathlib**: Path manipulation utilities

### External Dependencies
- **COLMAP**: Structure-from-Motion and Multi-View Stereo pipeline
  - Version: 3.11+ recommended
  - Installation: See [COLMAP installation guide](https://colmap.github.io/install.html)
  - Features: Feature extraction, matching, sparse/dense reconstruction

## File Organization

Uploaded files are organized in session-based directories:
```
uploads/
├── 550e8400-e29b-41d4-a716-446655440000/
│   ├── 20250528_120000_image1.jpg
│   ├── 20250528_120001_image2.png
│   └── 20250528_120002_image3.jpeg
└── another-session-id/
    └── uploaded files...
```

## Preprocessing Features

- **Image Validation**: Comprehensive validation including file integrity and format checking
- **Quality Assessment**: Automatic calculation of brightness, contrast, sharpness, and blur metrics
- **EXIF Data Extraction**: Camera information, GPS coordinates, and technical settings
- **Smart Resizing**: Maintains aspect ratio while optimizing for processing (default max: 1920px)
- **Format Handling**: Supports JPG, JPEG, PNG with automatic format conversion
- **Quality Scoring**: Overall image quality assessment for photogrammetry suitability
- **Blur Detection**: Laplacian variance method for detecting motion blur and focus issues
- **Statistics Generation**: Batch processing statistics and quality reports

## Security Features

- **File Type Validation**: Extension and MIME type checking
- **File Signature Verification**: Binary signature validation
- **Size Limits**: Per-file and total request size limits
- **Secure Filenames**: Sanitized and timestamped filenames
- **Session Isolation**: Files organized in unique session directories

## Logging

The application logs to both console and file (`logs/app.log`) with structured logging including:
- Request processing
- File uploads
- Error tracking
- Health check status

## Error Handling

- **404**: Endpoint not found
- **413**: File too large
- **500**: Internal server error
- **Custom validation**: File type and request validation