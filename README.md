# 3D Photogrammetry Web Application

A modern full-stack web application for 3D photogrammetry processing using COLMAP for Structure-from-Motion reconstruction, with a Flask backend and Next.js frontend.

## Project Structure

```
3D-photogrammetry/
├── app.py                      # Main Flask backend application
├── colmap_wrapper.py           # COLMAP integration wrapper
├── image_preprocessor.py       # Image preprocessing utilities
├── model_processor.py          # 3D model processing utilities
├── test_colmap_integration.py  # Test script for COLMAP functionality
├── requirements.txt            # Python dependencies
├── README.md                  # Project documentation
├── DEPLOYMENT_GUIDE.md        # Deployment instructions
├── uploads/                   # Directory for uploaded images
├── outputs/                   # Directory for processed results
├── logs/                      # Application log files
├── static/                    # Static backend files
├── templates/                 # Flask HTML templates
└── frontend/                  # Next.js frontend application
    ├── src/
    │   ├── app/               # Next.js app router pages
    │   ├── components/        # React components
    │   ├── hooks/            # Custom React hooks
    │   ├── lib/              # API utilities and helpers
    │   └── types/            # TypeScript type definitions
    ├── package.json          # Frontend dependencies
    ├── tailwind.config.js    # Tailwind CSS configuration
    └── tsconfig.json         # TypeScript configuration
```

## Features

### Backend Features
- **Multiple File Upload**: Secure multi-image upload with session-based organization
- **File Validation**: Comprehensive image validation (JPG, PNG, JPEG) with security checks
- **Session Management**: Unique session IDs for organizing related uploads
- **COLMAP Integration**: Complete Structure-from-Motion pipeline using COLMAP
- **3D Reconstruction**: Sparse and dense 3D reconstruction from images
- **Progress Tracking**: Real-time progress monitoring for long-running processes
- **RESTful API**: JSON-based API endpoints with detailed responses
- **CORS Support**: Cross-Origin Resource Sharing for frontend integration
- **Error Handling**: Robust error handling and detailed logging

### Frontend Features
- **Modern UI**: React-based interface with Tailwind CSS styling
- **3D Model Viewer**: Three.js integration for viewing generated 3D models
- **Drag & Drop Upload**: Intuitive file upload with progress tracking
- **Real-time Status**: Live updates on processing progress
- **Responsive Design**: Works on desktop and mobile devices
- **Error Handling**: User-friendly error messages and notifications

## API Endpoints

### Core Endpoints
- `GET /` - Welcome message and API overview
- `GET /health` - Health check endpoint with system status
- `POST /upload` - Upload multiple images with session management
- `POST /process` - Start COLMAP 3D reconstruction processing
- `GET /status/<session_id>` - Get processing status (uploaded/processing/complete/error)
- `GET /download/<session_id>` - Download processed 3D models

### Upload Endpoint Details

**POST /upload**
- **Content-Type**: `multipart/form-data`
- **Field Name**: `files` (supports multiple files)
- **Supported Formats**: JPG, JPEG, PNG
- **Max Request Size**: 200MB total (sufficient for multiple high-resolution images)
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
  "uploaded_files": [
    {
      "filename": "20250529_120000_image1.jpg",
      "original_name": "image1.jpg",
      "size": 1024000
    }
  ]
}
```

### Process Endpoint Details

**POST /process**
- **Content-Type**: `application/json`
- **Required**: `session_id`
- **Optional Parameters**:
  - `enable_dense_reconstruction` (boolean, default: false) - Dense reconstruction requires CUDA
  - `enable_meshing` (boolean, default: false)  
  - `max_image_size` (integer, default: 1920)
  - `matcher_type` (string, default: "exhaustive", options: "exhaustive", "sequential")

**Request Example**:
```bash
curl -X POST http://localhost:5000/process \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "enable_dense_reconstruction": false,
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
    "enable_dense_reconstruction": false,
    "enable_meshing": false,
    "max_image_size": 1920,
    "matcher_type": "exhaustive"
  },
  "status_endpoint": "/status/550e8400-e29b-41d4-a716-446655440000"
}
```

### Status Endpoint Details

**GET /status/<session_id>**
- **Purpose**: Get processing status with simple status values
- **Status Values**: `"uploaded"`, `"processing"`, `"complete"`, `"error"`
- **Returns**: Current status, messages, error details, and output files when complete

**Response Example (Processing)**:
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

**Response Example (Complete)**:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "complete",
  "message": "Processing completed successfully with downloadable models",
  "start_time": "2025-05-28T12:00:00",
  "end_time": "2025-05-28T12:04:15",
  "error": null,
  "output_files": [
    {
      "type": "sparse_model",
      "path": "outputs/colmap_session_.../sparse_model.ply",
      "size": 1024000
    }
  ],
  "model_processing_results": {
    "compressed_archive": "outputs/colmap_session_.../model_.zip",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Download Endpoint Details

**GET /download/<session_id>**
- **Purpose**: Download processed 3D models as compressed archive
- **Returns**: ZIP file containing all generated 3D models and metadata
- **Supported Formats**: PLY (point cloud), OBJ (mesh if generated)

**Response Example**:
```bash
# Downloads a ZIP file containing all processed models
curl -O -J http://localhost:5000/download/SESSION_ID
# Results in: 3d_model_SESSION_ID.zip
```

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
   - Progress: 45-100% (when dense reconstruction is disabled)

4. **Dense Reconstruction** (Optional, requires CUDA):
   - Creates dense point cloud using multi-view stereo
   - Significantly improves detail but requires GPU hardware
   - Progress: 70-90%

5. **Mesh Generation** (Optional):
   - Generates mesh from dense point cloud using Poisson reconstruction
   - Creates textured 3D model
   - Progress: 90-100%

### Output Files

**Sparse Reconstruction** (Always Generated):
- `sparse_model.ply`: 3D point cloud in PLY format
- `cameras.bin`: Camera intrinsic parameters
- `images.bin`: Camera poses and image information  
- `points3D.bin`: 3D point coordinates and visibility

**Dense Reconstruction** (Optional, requires CUDA):
- `fused.ply`: Dense 3D point cloud in PLY format

**Mesh** (Optional, experimental):
- `mesh.ply`: 3D mesh in PLY format

### Processing Parameters

- **Image Size**: Maximum dimension for processing (trade-off between quality and speed)
- **Matcher Type**: 
  - `exhaustive`: Matches all image pairs (best quality, slower)
  - `sequential`: Matches consecutive images (faster, suitable for ordered sequences)
- **Dense Reconstruction**: Enable for detailed point clouds (requires CUDA/GPU)
- **Meshing**: Enable for 3D mesh generation (experimental, requires dense reconstruction)

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
   colmap -h
   ```

### Backend Setup

1. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Backend**:
   ```bash
   python app.py
   ```

3. **Access the Backend API**:
   - Main API: `http://localhost:5000/`
   - Health Check: `http://localhost:5000/health`

4. **Test COLMAP Integration**:
   ```bash
   python test_colmap_integration.py
   ```

### Frontend Setup

1. **Navigate to Frontend Directory**:
   ```bash
   cd frontend
   ```

2. **Install Dependencies**:
   ```bash
   npm install
   ```

3. **Run Development Server**:
   ```bash
   npm run dev
   ```

4. **Access the Frontend**:
   - Frontend Application: `http://localhost:3000`

### Production Build

1. **Build Frontend**:
   ```bash
   cd frontend
   npm run build
   ```

2. **Start Production Servers**:
   ```bash
   # Backend
   python app.py

   # Frontend (in another terminal)
   cd frontend
   npm start
   ```

## Configuration

### Backend Configuration
- **Max Request Size**: 200MB total (supports multiple high-resolution images)
- **Allowed File Types**: JPG, JPEG, PNG (validated by file signature)
- **Upload Directory**: `uploads/` (organized by session ID)
- **Output Directory**: `outputs/`
- **Log Files**: `logs/app.log`
- **CORS**: Enabled for all origins
- **Session Management**: UUID-based unique session directories

### Frontend Configuration
- **API Base URL**: Configurable in `.env.local`
- **Build Tool**: Next.js with TypeScript
- **Styling**: Tailwind CSS
- **3D Rendering**: Three.js with React Three Fiber

## Dependencies

### Backend Dependencies
- **Flask**: Web framework
- **Flask-CORS**: Cross-Origin Resource Sharing support
- **OpenCV**: Computer vision library for image processing
- **NumPy**: Numerical computing
- **Pillow**: Python Imaging Library for image manipulation
- **Werkzeug**: WSGI utilities

### Frontend Dependencies
- **Next.js**: React framework
- **React**: UI library
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **Three.js**: 3D graphics library
- **@react-three/fiber**: React renderer for Three.js
- **@react-three/drei**: Useful helpers for React Three Fiber

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

outputs/
├── colmap_session_550e8400.../
│   ├── sparse_model.ply
│   ├── model_550e8400...zip
│   ├── sparse/0/
│   └── images/
└── colmap_session_another.../
    └── processing results...
```

## Security Features

- **File Type Validation**: Extension and MIME type checking
- **File Signature Verification**: Binary signature validation
- **Size Limits**: Per-request size limits (200MB total)
- **Secure Filenames**: Sanitized and timestamped filenames
- **Session Isolation**: Files organized in unique session directories
- **Input Sanitization**: All user inputs are validated and sanitized

## Logging

The application logs to both console and file (`logs/app.log`) with structured logging including:
- Request processing
- File uploads and processing
- COLMAP pipeline execution
- Error tracking and debugging
- Health check status
- Performance metrics

## Error Handling

### HTTP Status Codes
- **200**: Success
- **202**: Processing started (async operations)
- **400**: Bad request (invalid parameters)
- **404**: Endpoint or session not found
- **413**: Request entity too large
- **500**: Internal server error

### Custom Error Responses
- **File validation errors**: Invalid file type or corrupted files
- **COLMAP processing errors**: Feature extraction or reconstruction failures
- **Session management errors**: Invalid or expired session IDs
- **Resource errors**: Insufficient disk space or memory

## Performance Notes

### CUDA Support
- **Dense reconstruction requires CUDA**: For GPU-accelerated dense reconstruction
- **Sparse reconstruction works without GPU**: Core functionality available on any system
- **Automatic fallback**: Application gracefully handles missing CUDA

### Optimization Tips
- **Image size**: Smaller images process faster but with lower detail
- **Matcher type**: Sequential matching is faster for ordered image sequences
- **Dense reconstruction**: Only enable if you have CUDA and need maximum detail
- **File formats**: JPEG files are smaller and faster to upload than PNG

## Troubleshooting

### Common Issues
1. **COLMAP not found**: Ensure COLMAP is installed and in PATH
2. **CUDA errors**: Disable dense reconstruction if no GPU available
3. **File upload failures**: Check file size limits and formats
4. **Processing failures**: Verify images have sufficient overlap and features

### Debug Mode
Enable debug logging by setting environment variable:
```bash
export FLASK_DEBUG=1
python app.py