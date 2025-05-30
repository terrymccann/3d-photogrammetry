import os
import logging
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import cv2
import numpy as np
import threading
from pathlib import Path
from image_preprocessor import ImagePreprocessor, preprocess_session_images
from model_processor import ModelProcessor, create_model_processor, ModelProcessingError

# Try to import COLMAP wrapper - make it optional
try:
    from colmap_wrapper import ColmapProcessor, create_colmap_processor, validate_image_set
    COLMAP_AVAILABLE = True
except ImportError:
    print("Warning: COLMAP wrapper not available - COLMAP functionality will be disabled")
    ColmapProcessor = None
    create_colmap_processor = None
    validate_image_set = lambda x: (True, "Image validation skipped")
    COLMAP_AVAILABLE = False

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for all routes
CORS(app)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB total request size for multiple high-res images
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}  # Restrict to jpg, png, jpeg only

# Ensure required directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
os.makedirs('logs', exist_ok=True)
os.makedirs('static', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize COLMAP processor
try:
    colmap_processor = create_colmap_processor(
        base_output_dir=app.config['OUTPUT_FOLDER'],
        enable_dense_reconstruction=False,  # Disabled by default (requires CUDA)
        enable_meshing=False,  # Can be enabled for full mesh generation
        cleanup_temp_files=False,  # Keep files for download
        use_gpu=True,  # Enable GPU acceleration if available
        gpu_indices="0",  # Use first GPU by default
        enable_dsp_sift=True,  # Enable DSP-SIFT for better features
        enable_guided_matching=True,  # Enable guided matching for improved results
        enable_geometric_consistency=True  # Enable geometric consistency in dense reconstruction
    )
    logger.info("COLMAP processor initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize COLMAP processor: {str(e)}")
    colmap_processor = None

# Initialize Model processor
try:
    model_processor = create_model_processor(
        temp_dir=os.path.join(app.config['OUTPUT_FOLDER'], 'temp'),
        enable_compression=True
    )
    logger.info("Model processor initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize model processor: {str(e)}")
    model_processor = None


def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def validate_image_file(file):
    """Validate that the uploaded file is a proper image."""
    try:
        # Check file extension
        if not allowed_file(file.filename):
            return False, "Invalid file type. Only JPG, PNG, and JPEG files are allowed."
        
        # Check file size (additional check beyond Flask's MAX_CONTENT_LENGTH)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset file pointer
        
        if file_size > app.config['MAX_CONTENT_LENGTH']:
            return False, "File too large. Maximum size is 16MB."
        
        if file_size == 0:
            return False, "Empty file not allowed."
        
        # Basic security check - verify it's actually an image
        file_header = file.read(10)
        file.seek(0)  # Reset file pointer
        
        # Check for common image file signatures
        image_signatures = [
            b'\xff\xd8\xff',  # JPEG
            b'\x89PNG\r\n\x1a\n',  # PNG
            b'GIF87a',  # GIF87a
            b'GIF89a',  # GIF89a
        ]
        
        is_valid_image = any(file_header.startswith(sig) for sig in image_signatures)
        if not is_valid_image:
            return False, "File does not appear to be a valid image."
        
        return True, "Valid image file."
        
    except Exception as e:
        logger.error(f"File validation error: {str(e)}")
        return False, "Error validating file."


def create_session_directory(session_id):
    """Create a unique session directory for uploads."""
    session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    os.makedirs(session_dir, exist_ok=True)
    return session_dir


@app.route('/')
def index():
    """Main index page."""
    return jsonify({
        'message': 'Welcome to 3D Photogrammetry API',
        'status': 'running',
        'version': '1.0.0',
        'endpoints': {
            'health': '/health - GET - Health check endpoint',
            'upload': '/upload - POST - Upload multiple images (form-data with "files" field)',
            'preprocess': '/preprocess - POST - Preprocess images by session_id',
            'preprocess_results': '/preprocess/<session_id> - GET - Get preprocessing results',
            'process': '/process - POST - Start COLMAP 3D reconstruction processing',
            'status': '/status/<session_id> - GET - Get processing status (uploaded/processing/complete/error)',
            'download': '/download/<session_id> - GET - Download processed 3D models',
            'colmap_process': '/colmap/process - POST - Start COLMAP 3D reconstruction',
            'colmap_status': '/colmap/status/<session_id> - GET - Get COLMAP processing status',
            'colmap_results': '/colmap/results/<session_id> - GET - Get COLMAP processing results',
            'colmap_cancel': '/colmap/cancel/<session_id> - POST - Cancel COLMAP processing'
        },
        'upload_requirements': {
            'field_name': 'files',
            'supported_formats': ['jpg', 'jpeg', 'png'],
            'max_file_size': '16MB',
            'multiple_files': True
        }
    })


@app.route('/health')
def health_check():
    """Health check endpoint."""
    try:
        # Basic health checks
        upload_dir_exists = os.path.exists(app.config['UPLOAD_FOLDER'])
        output_dir_exists = os.path.exists(app.config['OUTPUT_FOLDER'])
        
        # Check OpenCV availability
        opencv_available = True
        try:
            cv2.__version__
        except Exception:
            opencv_available = False
        
        # Check numpy availability
        numpy_available = True
        try:
            np.__version__
        except Exception:
            numpy_available = False
        
        # Check COLMAP availability
        colmap_available = colmap_processor is not None
        
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'services': {
                'upload_directory': upload_dir_exists,
                'output_directory': output_dir_exists,
                'opencv': opencv_available,
                'numpy': numpy_available,
                'colmap': colmap_available
            },
            'versions': {
                'opencv': cv2.__version__ if opencv_available else 'unavailable',
                'numpy': np.__version__ if numpy_available else 'unavailable',
                'colmap': 'available' if colmap_available else 'unavailable'
            }
        }
        
        # Overall health status
        if all(health_status['services'].values()):
            logger.info("Health check passed")
            return jsonify(health_status), 200
        else:
            health_status['status'] = 'degraded'
            logger.warning("Health check shows degraded status")
            return jsonify(health_status), 503
            
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 503


@app.route('/upload', methods=['POST'])
def upload_files():
    """Upload multiple images for photogrammetry processing."""
    try:
        # Check if files are present in the request
        if 'files' not in request.files:
            return jsonify({'error': 'No files part in the request'}), 400
        
        files = request.files.getlist('files')
        
        if not files or all(file.filename == '' for file in files):
            return jsonify({'error': 'No files selected'}), 400
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        session_dir = create_session_directory(session_id)
        
        uploaded_files = []
        failed_files = []
        total_size = 0
        
        # Process each file
        for file in files:
            if file.filename == '':
                continue
                
            # Validate file
            is_valid, validation_message = validate_image_file(file)
            
            if not is_valid:
                failed_files.append({
                    'filename': file.filename,
                    'error': validation_message
                })
                continue
            
            # Generate secure filename
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            unique_filename = f"{timestamp}{filename}"
            
            # Save file to session directory
            filepath = os.path.join(session_dir, unique_filename)
            file.save(filepath)
            
            # Get file size for response
            file_size = os.path.getsize(filepath)
            total_size += file_size
            
            uploaded_files.append({
                'original_filename': file.filename,
                'saved_filename': unique_filename,
                'filepath': filepath,
                'size': file_size
            })
            
            logger.info(f"File uploaded successfully: {unique_filename} in session {session_id}")
        
        # Prepare response
        response_data = {
            'session_id': session_id,
            'upload_status': 'success' if uploaded_files else 'failed',
            'files_uploaded': len(uploaded_files),
            'files_failed': len(failed_files),
            'total_files': len(files),
            'total_size': total_size,
            'uploaded_files': uploaded_files
        }
        
        if failed_files:
            response_data['failed_files'] = failed_files
            response_data['upload_status'] = 'partial' if uploaded_files else 'failed'
        
        # Initialize processing status for successful uploads
        if uploaded_files:
            update_processing_status(session_id, 'uploaded', f'{len(uploaded_files)} files uploaded successfully')
        
        # Determine response status code
        if uploaded_files:
            status_code = 200 if not failed_files else 207  # 207 for partial success
            logger.info(f"Upload session {session_id}: {len(uploaded_files)} files uploaded successfully")
        else:
            status_code = 400
            logger.warning(f"Upload session {session_id}: No files uploaded successfully")
        
        return jsonify(response_data), status_code
        
    except RequestEntityTooLarge:
        logger.warning("File upload rejected: file too large")
        return jsonify({'error': 'One or more files are too large. Maximum size is 16MB per file.'}), 413
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': 'Upload failed due to server error'}), 500

@app.route('/preprocess', methods=['POST'])
def preprocess_images():
    """Preprocess uploaded images in a session."""
    try:
        data = request.get_json()
        
        if not data or 'session_id' not in data:
            return jsonify({'error': 'No session_id provided'}), 400
        
        session_id = data['session_id']
        session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        
        # Verify session directory exists
        if not os.path.exists(session_dir):
            return jsonify({'error': f'Session {session_id} not found'}), 404
        
        # Get preprocessing parameters
        max_dimension = data.get('max_dimension', 1920)
        
        logger.info(f"Starting preprocessing for session {session_id} with max_dimension={max_dimension}")
        
        # Initialize preprocessor and process images
        try:
            preprocessor = ImagePreprocessor(max_dimension=max_dimension)
            results = preprocessor.process_session_images(session_dir)
            
            # Save preprocessing results to session directory
            results_file = os.path.join(session_dir, 'preprocessing_results.json')
            import json
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Preprocessing completed for session {session_id}: "
                       f"{results['statistics']['processed_count']} processed, "
                       f"{results['statistics']['failed_count']} failed")
            
            # Prepare response
            response_data = {
                'message': 'Image preprocessing completed',
                'session_id': session_id,
                'preprocessing_results': results,
                'results_saved_to': results_file
            }
            
            return jsonify(response_data), 200
            
        except Exception as e:
            logger.error(f"Preprocessing failed for session {session_id}: {str(e)}")
            return jsonify({
                'error': 'Preprocessing failed',
                'session_id': session_id,
                'details': str(e)
            }), 500
        
    except Exception as e:
        logger.error(f"Preprocessing endpoint error: {str(e)}")
        return jsonify({'error': 'Preprocessing request failed'}), 500


@app.route('/preprocess/<session_id>', methods=['GET'])
def get_preprocessing_results(session_id):
    """Get preprocessing results for a session."""
    try:
        session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        
        # Verify session directory exists
        if not os.path.exists(session_dir):
            return jsonify({'error': f'Session {session_id} not found'}), 404
        
        # Check if preprocessing results exist
        results_file = os.path.join(session_dir, 'preprocessing_results.json')
        if not os.path.exists(results_file):
            return jsonify({
                'error': 'No preprocessing results found for this session',
                'session_id': session_id,
                'suggestion': 'Run POST /preprocess first'
            }), 404
        
        # Load and return results
        import json
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        logger.info(f"Retrieved preprocessing results for session {session_id}")
        
        return jsonify({
            'session_id': session_id,
            'preprocessing_results': results,
            'results_file': results_file
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving preprocessing results for session {session_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve preprocessing results'}), 500


# Global dictionary to store processing status
processing_status = {}
processing_lock = threading.Lock()

def update_processing_status(session_id, status, message=None, error=None, output_files=None):
    """Update processing status for a session."""
    with processing_lock:
        if session_id not in processing_status:
            processing_status[session_id] = {
                'session_id': session_id,
                'status': 'uploaded',
                'message': 'Session created',
                'start_time': datetime.now().isoformat(),
                'end_time': None,
                'error': None,
                'output_files': []
            }
        
        processing_status[session_id]['status'] = status
        if message:
            processing_status[session_id]['message'] = message
        if error:
            processing_status[session_id]['error'] = error
        if output_files:
            processing_status[session_id]['output_files'] = output_files
        if status in ['complete', 'error']:
            processing_status[session_id]['end_time'] = datetime.now().isoformat()


@app.route('/process', methods=['POST'])
def process_images():
    """Process uploaded images for photogrammetry using COLMAP."""
    try:
        data = request.get_json()
        
        if not data or 'session_id' not in data:
            return jsonify({'error': 'No session_id provided'}), 400
        
        session_id = data['session_id']
        session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        
        # Verify session directory exists
        if not os.path.exists(session_dir):
            return jsonify({'error': f'Session {session_id} not found'}), 404
        
        # Check if COLMAP processor is available
        if not colmap_processor:
            return jsonify({
                'error': 'COLMAP processor not available',
                'details': 'COLMAP may not be installed or configured properly'
            }), 503
        
        # Get all image files from the session directory
        image_files = []
        for filename in os.listdir(session_dir):
            filepath = os.path.join(session_dir, filename)
            if os.path.isfile(filepath) and allowed_file(filename):
                image_files.append(filepath)
        
        if not image_files:
            return jsonify({'error': 'No valid image files found in session'}), 404
        
        # Validate image set for COLMAP processing
        is_valid, validation_message = validate_image_set(image_files)
        if not is_valid:
            update_processing_status(session_id, 'error', error=f'Image validation failed: {validation_message}')
            return jsonify({
                'error': 'Image validation failed',
                'details': validation_message
            }), 400
        
        # Initialize processing status
        update_processing_status(session_id, 'uploaded', 'Images uploaded and validated')
        
        # Get processing parameters
        enable_dense = data.get('enable_dense_reconstruction', False)
        enable_mesh = data.get('enable_meshing', False)
        max_image_size = data.get('max_image_size', 1920)
        matcher_type = data.get('matcher_type', 'exhaustive')
        
        logger.info(f"Starting COLMAP processing for session {session_id} with {len(image_files)} images")
        
        # Start processing in background thread
        def process_in_background():
            try:
                # Update status to processing
                update_processing_status(session_id, 'processing', 'Starting COLMAP 3D reconstruction')
                
                # Configure processor for this session
                colmap_processor.enable_dense_reconstruction = enable_dense
                colmap_processor.enable_meshing = enable_mesh
                colmap_processor.max_image_size = max_image_size
                colmap_processor.matcher_type = matcher_type.lower()
                
                # Run COLMAP processing (synchronous mode)
                results = colmap_processor.process_images(session_id, image_files, async_mode=False)
                
                if results.get('status') == 'completed':
                    # Process 3D models for download
                    output_files = []
                    model_processing_results = None
                    
                    try:
                        if model_processor:
                            update_processing_status(session_id, 'processing', 'Processing 3D models for download')
                            
                            # Get COLMAP workspace directory
                            workspace_dir = Path(app.config['OUTPUT_FOLDER']) / f"colmap_session_{session_id}"
                            
                            # Process COLMAP output into downloadable models
                            model_processing_results = model_processor.process_colmap_output(session_id, workspace_dir)
                            
                            # Add processed model files to output
                            if model_processing_results and model_processing_results.get('processed_files'):
                                for file_info in model_processing_results['processed_files']:
                                    output_files.append({
                                        'type': file_info.get('type', 'unknown'),
                                        'format': file_info.get('format', 'unknown'),
                                        'path': file_info.get('processed_file', ''),
                                        'size': file_info.get('metadata', {}).get('file_size', 0),
                                        'metadata': file_info.get('metadata', {})
                                    })
                            
                            logger.info(f"3D model processing completed for session {session_id}")
                        
                    except ModelProcessingError as e:
                        logger.error(f"Model processing failed for session {session_id}: {str(e)}")
                        # Continue with COLMAP results even if model processing fails
                    except Exception as e:
                        logger.error(f"Unexpected error in model processing for session {session_id}: {str(e)}")
                    
                    # Extract original COLMAP output files if model processing failed
                    if not output_files and results.get('output_files'):
                        colmap_output_files = results['output_files']
                        
                        # Handle both list and dict formats
                        if isinstance(colmap_output_files, list):
                            # COLMAP wrapper returns list of file info dicts
                            output_files.extend(colmap_output_files)
                        elif isinstance(colmap_output_files, dict):
                            # Legacy format: dict with file types as keys
                            for file_type, file_info in colmap_output_files.items():
                                if file_info:
                                    if isinstance(file_info, dict):
                                        for sub_type, sub_path in file_info.items():
                                            if sub_path and os.path.exists(sub_path):
                                                output_files.append({
                                                    'type': f"{file_type}_{sub_type}",
                                                    'path': sub_path,
                                                    'size': os.path.getsize(sub_path)
                                                })
                                    elif isinstance(file_info, str) and os.path.exists(file_info):
                                        output_files.append({
                                            'type': file_type,
                                            'path': file_info,
                                            'size': os.path.getsize(file_info)
                                        })
                    
                    # Store model processing results in status
                    processing_status[session_id]['model_processing_results'] = model_processing_results
                    
                    update_processing_status(
                        session_id,
                        'complete',
                        'Processing completed successfully with downloadable models',
                        output_files=output_files
                    )
                    logger.info(f"Complete processing finished for session {session_id}")
                else:
                    error_msg = results.get('error', 'Unknown error during processing')
                    update_processing_status(session_id, 'error', error=error_msg)
                    logger.error(f"COLMAP processing failed for session {session_id}: {error_msg}")
                    
            except Exception as e:
                error_msg = f"Processing failed: {str(e)}"
                update_processing_status(session_id, 'error', error=error_msg)
                logger.error(f"COLMAP background processing failed for session {session_id}: {str(e)}")
        
        # Start background processing
        import threading
        processing_thread = threading.Thread(target=process_in_background)
        processing_thread.daemon = True
        processing_thread.start()
        
        # Update status to processing
        update_processing_status(session_id, 'processing', 'COLMAP processing started')
        
        return jsonify({
            'message': 'Processing started',
            'session_id': session_id,
            'status': 'processing',
            'input_files_count': len(image_files),
            'processing_parameters': {
                'enable_dense_reconstruction': enable_dense,
                'enable_meshing': enable_mesh,
                'max_image_size': max_image_size,
                'matcher_type': matcher_type
            },
            'status_endpoint': f'/status/{session_id}'
        }), 202  # 202 Accepted for async processing
        
    except Exception as e:
        error_msg = f"Processing request failed: {str(e)}"
        logger.error(f"Processing error for session {session_id if 'session_id' in locals() else 'unknown'}: {error_msg}")
        if 'session_id' in locals():
            update_processing_status(session_id, 'error', error=error_msg)
        return jsonify({'error': error_msg}), 500


@app.route('/status/<session_id>', methods=['GET'])
def get_processing_status(session_id):
    """Get processing status for a session."""
    try:
        with processing_lock:
            if session_id not in processing_status:
                return jsonify({
                    'error': f'No processing status found for session {session_id}',
                    'suggestion': 'Start processing with POST /process'
                }), 404
            
            status_data = processing_status[session_id].copy()
        
        # Add additional details if available from COLMAP processor
        if colmap_processor:
            colmap_progress = colmap_processor.get_progress(session_id)
            if colmap_progress:
                stage = colmap_progress.get('stage', 'unknown')
                # Convert enum to string if it's an enum
                if hasattr(stage, 'value'):
                    stage = stage.value
                status_data['detailed_progress'] = {
                    'stage': stage,
                    'progress_percent': colmap_progress.get('progress_percent', 0),
                    'stage_message': colmap_progress.get('message', '')
                }
        
        logger.info(f"Retrieved status for session {session_id}: {status_data['status']}")
        
        return jsonify(status_data), 200
        
    except Exception as e:
        logger.error(f"Error retrieving status for session {session_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve processing status'}), 500


@app.route('/download/<session_id>', methods=['GET'])
def download_models(session_id):
    """Download processed 3D models for a session."""
    try:
        # Check if session exists in processing status
        with processing_lock:
            if session_id not in processing_status:
                return jsonify({
                    'error': f'No processing found for session {session_id}',
                    'suggestion': 'Start processing with POST /process'
                }), 404
            
            session_status = processing_status[session_id].copy()
        
        # Check if processing is completed
        if session_status['status'] != 'complete':
            return jsonify({
                'error': 'Processing not completed yet',
                'current_status': session_status['status'],
                'message': session_status.get('message', ''),
                'status_endpoint': f'/status/{session_id}'
            }), 400
        
        # Get model processing results
        model_results = session_status.get('model_processing_results')
        if not model_results:
            return jsonify({
                'error': 'No processed models available for download',
                'details': 'Model processing may have failed or not been performed'
            }), 404
        
        # Check for compressed archive first
        compressed_archive = model_results.get('compressed_archive')
        if compressed_archive and os.path.exists(compressed_archive):
            logger.info(f"Serving compressed model archive for session {session_id}")
            
            return send_file(
                compressed_archive,
                as_attachment=True,
                download_name=f"3d_model_{session_id}.zip",
                mimetype='application/zip'
            )
        
        # If no compressed archive, check for individual files
        output_files = session_status.get('output_files', [])
        if not output_files:
            return jsonify({
                'error': 'No output files available for download'
            }), 404
        
        # For individual file download, return information about available files
        # In a more complete implementation, you might want to create a zip on-the-fly
        available_files = []
        for file_info in output_files:
            file_path = file_info.get('path', '')
            if file_path and os.path.exists(file_path):
                available_files.append({
                    'type': file_info.get('type', 'unknown'),
                    'format': file_info.get('format', 'unknown'),
                    'size': file_info.get('size', 0),
                    'download_url': f'/download/{session_id}/file/{os.path.basename(file_path)}',
                    'metadata': file_info.get('metadata', {})
                })
        
        if not available_files:
            return jsonify({
                'error': 'No downloadable files found'
            }), 404
        
        return jsonify({
            'session_id': session_id,
            'status': 'complete',
            'available_files': available_files,
            'total_files': len(available_files),
            'model_metadata': model_results.get('model_metadata', {}),
            'download_info': {
                'individual_files': True,
                'compressed_archive': False,
                'note': 'Use the download_url for each file to download individually'
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error handling download request for session {session_id}: {str(e)}")
        return jsonify({'error': 'Failed to process download request'}), 500


@app.route('/download/<session_id>/file/<filename>', methods=['GET'])
def download_individual_file(session_id, filename):
    """Download an individual file from a processing session."""
    try:
        # Check if session exists and is completed
        with processing_lock:
            if session_id not in processing_status:
                return jsonify({
                    'error': f'No processing found for session {session_id}'
                }), 404
            
            session_status = processing_status[session_id].copy()
        
        if session_status['status'] != 'complete':
            return jsonify({
                'error': 'Processing not completed yet'
            }), 400
        
        # Find the requested file
        output_files = session_status.get('output_files', [])
        target_file = None
        
        for file_info in output_files:
            file_path = file_info.get('path', '')
            if file_path and os.path.basename(file_path) == filename:
                if os.path.exists(file_path):
                    target_file = file_path
                    break
        
        if not target_file:
            return jsonify({
                'error': f'File not found: {filename}',
                'available_files': [os.path.basename(f.get('path', '')) for f in output_files if f.get('path')]
            }), 404
        
        # Determine MIME type based on file extension
        file_ext = os.path.splitext(filename)[1].lower()
        mime_types = {
            '.obj': 'model/obj',
            '.ply': 'application/octet-stream',
            '.mtl': 'text/plain',
            '.txt': 'text/plain',
            '.json': 'application/json',
            '.zip': 'application/zip'
        }
        
        mime_type = mime_types.get(file_ext, 'application/octet-stream')
        
        logger.info(f"Serving individual file {filename} for session {session_id}")
        
        return send_file(
            target_file,
            as_attachment=True,
            download_name=filename,
            mimetype=mime_type
        )
        
    except Exception as e:
        logger.error(f"Error serving file {filename} for session {session_id}: {str(e)}")
        return jsonify({'error': 'Failed to serve file'}), 500


@app.route('/api/sessions/<session_id>/files/<filename>', methods=['GET'])
def serve_file_for_viewing(session_id, filename):
    """Serve a file for inline viewing (e.g., 3D model viewer)."""
    try:
        # Check if session exists and is completed
        with processing_lock:
            if session_id not in processing_status:
                return jsonify({
                    'error': f'No processing found for session {session_id}'
                }), 404
            
            session_status = processing_status[session_id].copy()
        
        if session_status['status'] != 'complete':
            return jsonify({
                'error': 'Processing not completed yet'
            }), 400
        
        # Find the requested file
        output_files = session_status.get('output_files', [])
        target_file = None
        
        for file_info in output_files:
            file_path = file_info.get('path', '')
            if file_path and os.path.basename(file_path) == filename:
                if os.path.exists(file_path):
                    target_file = file_path
                    break
        
        if not target_file:
            return jsonify({
                'error': f'File not found: {filename}',
                'available_files': [os.path.basename(f.get('path', '')) for f in output_files if f.get('path')]
            }), 404
        
        # Determine MIME type based on file extension
        file_ext = os.path.splitext(filename)[1].lower()
        mime_types = {
            '.obj': 'model/obj',
            '.ply': 'application/octet-stream',
            '.gltf': 'model/gltf+json',
            '.glb': 'model/gltf-binary',
            '.fbx': 'application/octet-stream',
            '.mtl': 'text/plain',
            '.txt': 'text/plain',
            '.json': 'application/json'
        }
        
        mime_type = mime_types.get(file_ext, 'application/octet-stream')
        
        logger.info(f"Serving file {filename} for viewing in session {session_id}")
        
        # Serve file inline for viewing
        return send_file(
            target_file,
            as_attachment=False,  # Serve inline for viewing
            mimetype=mime_type
        )
        
    except Exception as e:
        logger.error(f"Error serving file {filename} for viewing in session {session_id}: {str(e)}")
        return jsonify({'error': 'Failed to serve file'}), 500

# COLMAP 3D Reconstruction Endpoints

@app.route('/colmap/process', methods=['POST'])
def colmap_process():
    """Start COLMAP 3D reconstruction processing."""
    try:
        if not colmap_processor:
            return jsonify({
                'error': 'COLMAP processor not available',
                'details': 'COLMAP may not be installed or configured properly'
            }), 503
        
        data = request.get_json()
        
        if not data or 'session_id' not in data:
            return jsonify({'error': 'No session_id provided'}), 400
        
        session_id = data['session_id']
        session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        
        # Verify session directory exists
        if not os.path.exists(session_dir):
            return jsonify({'error': f'Session {session_id} not found'}), 404
        
        # Get all image files from the session directory
        image_files = []
        for filename in os.listdir(session_dir):
            filepath = os.path.join(session_dir, filename)
            if os.path.isfile(filepath) and allowed_file(filename):
                image_files.append(filepath)
        
        if not image_files:
            return jsonify({'error': 'No valid image files found in session'}), 404
        
        # Validate image set for COLMAP processing
        is_valid, validation_message = validate_image_set(image_files)
        if not is_valid:
            return jsonify({
                'error': 'Image validation failed',
                'details': validation_message
            }), 400
        
        # Get processing parameters
        enable_dense = data.get('enable_dense_reconstruction', False)
        enable_mesh = data.get('enable_meshing', False)
        max_image_size = data.get('max_image_size', 1920)
        matcher_type = data.get('matcher_type', 'exhaustive')
        
        # Update processor configuration for this session
        colmap_processor.enable_dense_reconstruction = enable_dense
        colmap_processor.enable_meshing = enable_mesh
        colmap_processor.max_image_size = max_image_size
        colmap_processor.matcher_type = matcher_type.lower()
        
        logger.info(f"Starting COLMAP processing for session {session_id} with {len(image_files)} images")
        
        # Start processing in a separate thread to avoid blocking
        def process_in_background():
            try:
                results = colmap_processor.process_images(session_id, image_files, async_mode=False)
                logger.info(f"COLMAP processing completed for session {session_id}")
            except Exception as e:
                logger.error(f"COLMAP background processing failed for session {session_id}: {str(e)}")
        
        import threading
        processing_thread = threading.Thread(target=process_in_background)
        processing_thread.daemon = True
        processing_thread.start()
        
        return jsonify({
            'message': 'COLMAP processing started',
            'session_id': session_id,
            'input_files_count': len(image_files),
            'processing_parameters': {
                'enable_dense_reconstruction': enable_dense,
                'enable_meshing': enable_mesh,
                'max_image_size': max_image_size,
                'matcher_type': matcher_type
            },
            'status_endpoint': f'/colmap/status/{session_id}',
            'results_endpoint': f'/colmap/results/{session_id}'
        }), 202  # 202 Accepted for async processing
        
    except Exception as e:
        logger.error(f"COLMAP processing error: {str(e)}")
        return jsonify({'error': 'COLMAP processing request failed'}), 500


@app.route('/colmap/status/<session_id>', methods=['GET'])
def colmap_status(session_id):
    """Get COLMAP processing status for a session."""
    try:
        if not colmap_processor:
            return jsonify({
                'error': 'COLMAP processor not available'
            }), 503
        
        progress = colmap_processor.get_progress(session_id)
        
        if not progress:
            return jsonify({
                'error': f'No COLMAP processing found for session {session_id}',
                'suggestion': 'Start processing with POST /colmap/process'
            }), 404
        
        # Note: datetime objects are already converted to ISO strings in get_progress()
        # No additional conversion needed for start_time and end_time
        
        # Convert enum objects to strings for JSON serialization
        def serialize_for_json(obj):
            """Recursively convert enum objects to JSON-serializable values."""
            if hasattr(obj, 'value'):  # Handle enum objects
                return obj.value
            elif isinstance(obj, dict):
                return {k: serialize_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [serialize_for_json(item) for item in obj]
            else:
                return obj
        
        serializable_progress = serialize_for_json(progress)
        
        logger.info(f"Retrieved COLMAP status for session {session_id}: {progress['status']}")
        
        return jsonify({
            'session_id': session_id,
            'colmap_progress': serializable_progress
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving COLMAP status for session {session_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve processing status'}), 500


@app.route('/colmap/results/<session_id>', methods=['GET'])
def colmap_results(session_id):
    """Get COLMAP processing results for a session."""
    try:
        if not colmap_processor:
            return jsonify({
                'error': 'COLMAP processor not available'
            }), 503
        
        progress = colmap_processor.get_progress(session_id)
        
        if not progress:
            return jsonify({
                'error': f'No COLMAP processing found for session {session_id}',
                'suggestion': 'Start processing with POST /colmap/process'
            }), 404
        
        # Check if processing is completed
        if progress['status'] != 'completed':
            return jsonify({
                'error': 'Processing not completed yet',
                'current_status': progress['status'],
                'current_stage': progress.get('stage', 'unknown'),
                'progress_percent': progress.get('progress_percent', 0),
                'status_endpoint': f'/colmap/status/{session_id}'
            }), 202  # 202 Accepted, processing not complete
        
        # Get workspace directory to find output files
        workspace_dir = os.path.join(app.config['OUTPUT_FOLDER'], f"colmap_session_{session_id}")
        
        if not os.path.exists(workspace_dir):
            return jsonify({
                'error': 'Results directory not found',
                'session_id': session_id
            }), 404
        
        # Collect available output files
        output_files = {}
        
        # Sparse reconstruction results
        sparse_dir = os.path.join(workspace_dir, "sparse")
        if os.path.exists(sparse_dir):
            sparse_models = [d for d in os.listdir(sparse_dir) if os.path.isdir(os.path.join(sparse_dir, d))]
            if sparse_models:
                model_dir = os.path.join(sparse_dir, sparse_models[0])
                output_files['sparse_model'] = {
                    'cameras': os.path.join(model_dir, 'cameras.txt') if os.path.exists(os.path.join(model_dir, 'cameras.txt')) else None,
                    'images': os.path.join(model_dir, 'images.txt') if os.path.exists(os.path.join(model_dir, 'images.txt')) else None,
                    'points3D': os.path.join(model_dir, 'points3D.txt') if os.path.exists(os.path.join(model_dir, 'points3D.txt')) else None
                }
        
        # Dense reconstruction results
        dense_ply = os.path.join(workspace_dir, "dense", "fused.ply")
        if os.path.exists(dense_ply):
            output_files['dense_pointcloud'] = dense_ply
        
        # Mesh results
        mesh_ply = os.path.join(workspace_dir, "mesh", "mesh.ply")
        if os.path.exists(mesh_ply):
            output_files['mesh'] = mesh_ply
        
        logger.info(f"Retrieved COLMAP results for session {session_id}")
        
        # Convert enum objects to strings for JSON serialization
        def serialize_for_json(obj):
            """Recursively convert enum objects to JSON-serializable values."""
            if hasattr(obj, 'value'):  # Handle enum objects
                return obj.value
            elif isinstance(obj, dict):
                return {k: serialize_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [serialize_for_json(item) for item in obj]
            else:
                return obj
        
        serializable_progress = serialize_for_json(progress)
        
        # Prepare response data with careful serialization
        response_data = {
            'session_id': session_id,
            'status': 'completed',
            'processing_time': serialize_for_json(progress.get('end_time') or progress.get('start_time')),
            'workspace_directory': workspace_dir,
            'output_files': serialize_for_json(output_files),
            'colmap_progress': serializable_progress
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error retrieving COLMAP results for session {session_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve processing results'}), 500


@app.route('/colmap/cancel/<session_id>', methods=['POST'])
def colmap_cancel(session_id):
    """Cancel COLMAP processing for a session."""
    try:
        if not colmap_processor:
            return jsonify({
                'error': 'COLMAP processor not available'
            }), 503
        
        success = colmap_processor.cancel_processing(session_id)
        
        if success:
            logger.info(f"COLMAP processing cancelled for session {session_id}")
            return jsonify({
                'message': 'Processing cancelled successfully',
                'session_id': session_id
            }), 200
        else:
            return jsonify({
                'error': 'Failed to cancel processing',
                'details': 'Session may not exist or processing may already be finished',
                'session_id': session_id
            }), 400
        
    except Exception as e:
        logger.error(f"Error cancelling COLMAP processing for session {session_id}: {str(e)}")
        return jsonify({'error': 'Failed to cancel processing'}), 500


@app.route('/colmap/cleanup/<session_id>', methods=['POST'])
def colmap_cleanup(session_id):
    """Clean up COLMAP processing data for a session."""
    try:
        if not colmap_processor:
            return jsonify({
                'error': 'COLMAP processor not available'
            }), 503
        
        force_cleanup = request.get_json().get('force', False) if request.get_json() else False
        
        success = colmap_processor.cleanup_session_data(session_id, force=force_cleanup)
        
        if success:
            logger.info(f"COLMAP session data cleaned up for session {session_id}")
            return jsonify({
                'message': 'Session data cleaned up successfully',
                'session_id': session_id
            }), 200
        else:
            return jsonify({
                'error': 'Failed to cleanup session data',
                'details': 'Session may not exist or processing may be ongoing',
                'session_id': session_id,
                'suggestion': 'Use {"force": true} to force cleanup'
            }), 400
        
    except Exception as e:
        logger.error(f"Error cleaning up COLMAP session {session_id}: {str(e)}")
        return jsonify({'error': 'Failed to cleanup session data'}), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    logger.warning(f"404 error: {request.url}")
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"500 error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(413)
def too_large(error):
    """Handle file too large errors."""
    logger.warning("File too large uploaded")
    return jsonify({'error': 'File too large'}), 413


if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(debug=True, host='0.0.0.0', port=5000)