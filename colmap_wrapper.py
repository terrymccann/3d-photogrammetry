"""
COLMAP Wrapper for 3D Photogrammetry Processing

This module provides a Python wrapper around COLMAP (COLorless Multi-View Architecture)
for Structure-from-Motion and Multi-View Stereo reconstruction.

Features:
- Automatic COLMAP pipeline execution
- Progress tracking and status monitoring
- Sparse and dense reconstruction
- Mesh generation support
- Session-based processing management
"""

import os
import sys
import json
import time
import shutil
import zipfile
import logging
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from datetime import datetime


class ProcessingStage(Enum):
    """Enumeration of COLMAP processing stages."""
    INITIALIZATION = "initialization"
    FEATURE_EXTRACTION = "feature_extraction"
    FEATURE_MATCHING = "feature_matching"
    SPARSE_RECONSTRUCTION = "sparse_reconstruction"
    DENSE_RECONSTRUCTION = "dense_reconstruction"
    MESH_GENERATION = "mesh_generation"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class ProcessingStatus(Enum):
    """Enumeration of processing status values."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class ColmapProgress:
    """Progress tracking for COLMAP processing."""
    session_id: str
    stage: ProcessingStage
    status: ProcessingStatus
    progress_percent: float
    message: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    error_message: Optional[str] = None
    output_files: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.output_files is None:
            self.output_files = []


class ColmapError(Exception):
    """Custom exception for COLMAP processing errors."""
    pass


class ColmapProcessor:
    """
    COLMAP processor for automated 3D reconstruction from images.
    
    Handles the complete Structure-from-Motion pipeline including:
    - Feature extraction and matching
    - Sparse 3D reconstruction
    - Dense reconstruction (optional)
    - Mesh generation (optional)
    """
    
    def __init__(self,
                 base_output_dir: str,
                 enable_dense_reconstruction: bool = False,
                 enable_meshing: bool = False,
                 max_image_size: int = 1920,
                 matcher_type: str = "exhaustive",
                 cleanup_temp_files: bool = False):
        """
        Initialize COLMAP processor.
        
        Args:
            base_output_dir: Base directory for output files
            enable_dense_reconstruction: Whether to perform dense reconstruction
            enable_meshing: Whether to generate mesh from dense point cloud
            max_image_size: Maximum image dimension for processing
            matcher_type: Type of feature matching ("exhaustive" or "sequential")
            cleanup_temp_files: Whether to automatically clean up temporary files
        """
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(exist_ok=True)
        
        self.enable_dense_reconstruction = enable_dense_reconstruction
        self.enable_meshing = enable_meshing
        self.max_image_size = max_image_size
        self.matcher_type = matcher_type.lower()
        
        # Progress tracking
        self._progress: Dict[str, ColmapProgress] = {}
        self._processing_threads: Dict[str, threading.Thread] = {}
        self._cancel_flags: Dict[str, threading.Event] = {}
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Verify COLMAP installation
        self._verify_colmap_installation()
    
    def _verify_colmap_installation(self):
        """Verify that COLMAP is installed and accessible."""
        try:
            result = subprocess.run(['colmap', '-h'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            if result.returncode == 0:
                self.logger.info("COLMAP installation verified")
            else:
                raise ColmapError("COLMAP command failed")
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError) as e:
            raise ColmapError(f"COLMAP not found or not working: {str(e)}")
    
    def process_images(self, session_id: str, image_files: List[str], async_mode: bool = False) -> Dict[str, Any]:
        """
        Start COLMAP processing for a session.
        
        Args:
            session_id: Unique session identifier
            image_files: List of image file paths
            async_mode: If True, process in background thread; if False, process synchronously
            
        Returns:
            Dictionary with processing information
        """
        if session_id in self._processing_threads:
            if self._processing_threads[session_id].is_alive():
                raise ColmapError(f"Processing already in progress for session {session_id}")
        
        # Initialize progress tracking
        self._progress[session_id] = ColmapProgress(
            session_id=session_id,
            stage=ProcessingStage.INITIALIZATION,
            status=ProcessingStatus.PENDING,
            progress_percent=0.0,
            message="Initializing COLMAP processing",
            start_time=datetime.now().isoformat()
        )
        
        # Create cancel flag
        self._cancel_flags[session_id] = threading.Event()
        
        if async_mode:
            # Start processing in background thread
            thread = threading.Thread(
                target=self._process_session,
                args=(session_id, image_files),
                daemon=True
            )
            self._processing_threads[session_id] = thread
            thread.start()
            
            return {
                "message": "COLMAP processing started",
                "session_id": session_id,
                "input_files_count": len(image_files),
                "status": "started"
            }
        else:
            # Process synchronously
            try:
                self._process_session(session_id, image_files)
                
                # Get final progress status
                final_progress = self.get_progress(session_id)
                if final_progress and final_progress['status'] == ProcessingStatus.COMPLETED:
                    return {
                        "message": "COLMAP processing completed successfully",
                        "session_id": session_id,
                        "input_files_count": len(image_files),
                        "status": "completed",
                        "output_files": final_progress.get('output_files', [])
                    }
                else:
                    error_msg = final_progress.get('error_message', 'Processing failed') if final_progress else 'Processing failed'
                    return {
                        "message": "COLMAP processing failed",
                        "session_id": session_id,
                        "status": "error",
                        "error": error_msg
                    }
            except Exception as e:
                self.logger.error(f"Synchronous COLMAP processing failed for session {session_id}: {str(e)}")
                return {
                    "message": "COLMAP processing failed",
                    "session_id": session_id,
                    "status": "error",
                    "error": str(e)
                }
    
    def _process_session(self, session_id: str, image_files: List[str]):
        """Internal method to process a session in background thread."""
        try:
            workspace_dir = self.base_output_dir / f"colmap_session_{session_id}"
            workspace_dir.mkdir(exist_ok=True)
            
            # Update progress
            self._update_progress(session_id, ProcessingStage.INITIALIZATION, 
                                ProcessingStatus.RUNNING, 5.0, 
                                "Setting up workspace and copying images")
            
            # Copy images to workspace
            images_dir = workspace_dir / "images"
            images_dir.mkdir(exist_ok=True)
            
            copied_images = []
            for i, image_path in enumerate(image_files):
                if self._cancel_flags[session_id].is_set():
                    self._handle_cancellation(session_id)
                    return
                
                # Copy image with sequential naming
                image_name = f"image_{i+1:04d}.jpg"
                dest_path = images_dir / image_name
                shutil.copy2(image_path, dest_path)
                copied_images.append(str(dest_path))
                
                progress = 5.0 + (i / len(image_files)) * 5.0
                self._update_progress(session_id, ProcessingStage.INITIALIZATION,
                                    ProcessingStatus.RUNNING, progress,
                                    f"Copied {i+1}/{len(image_files)} images")
            
            # Create database
            database_dir = workspace_dir / "database"
            database_dir.mkdir(exist_ok=True)
            database_path = database_dir / "database.db"
            
            self._update_progress(session_id, ProcessingStage.FEATURE_EXTRACTION,
                                ProcessingStatus.RUNNING, 15.0,
                                "Extracting features from images")
            
            # Feature extraction
            self._run_colmap_command([
                "colmap", "feature_extractor",
                "--database_path", str(database_path),
                "--image_path", str(images_dir),
                "--ImageReader.single_camera", "1",
                "--SiftExtraction.max_image_size", str(self.max_image_size)
            ], session_id)
            
            if self._cancel_flags[session_id].is_set():
                self._handle_cancellation(session_id)
                return
            
            self._update_progress(session_id, ProcessingStage.FEATURE_MATCHING,
                                ProcessingStatus.RUNNING, 35.0,
                                "Matching features between images")
            
            # Feature matching
            if self.matcher_type == "sequential":
                self._run_colmap_command([
                    "colmap", "sequential_matcher",
                    "--database_path", str(database_path)
                ], session_id)
            else:
                self._run_colmap_command([
                    "colmap", "exhaustive_matcher",
                    "--database_path", str(database_path)
                ], session_id)
            
            if self._cancel_flags[session_id].is_set():
                self._handle_cancellation(session_id)
                return
            
            self._update_progress(session_id, ProcessingStage.SPARSE_RECONSTRUCTION,
                                ProcessingStatus.RUNNING, 55.0,
                                "Performing sparse 3D reconstruction")
            
            # Sparse reconstruction
            sparse_dir = workspace_dir / "sparse"
            sparse_dir.mkdir(exist_ok=True)
            
            self._run_colmap_command([
                "colmap", "mapper",
                "--database_path", str(database_path),
                "--image_path", str(images_dir),
                "--output_path", str(sparse_dir)
            ], session_id)
            
            if self._cancel_flags[session_id].is_set():
                self._handle_cancellation(session_id)
                return
            
            # Convert sparse model to PLY format
            sparse_ply_path = workspace_dir / "sparse_model.ply"
            model_dir = sparse_dir / "0"
            if model_dir.exists():
                self._run_colmap_command([
                    "colmap", "model_converter",
                    "--input_path", str(model_dir),
                    "--output_path", str(sparse_ply_path),
                    "--output_type", "PLY"
                ], session_id)
            
            output_files = [{"type": "sparse_model", "path": str(sparse_ply_path)}]
            
            # Dense reconstruction (optional)
            if self.enable_dense_reconstruction:
                if self._cancel_flags[session_id].is_set():
                    self._handle_cancellation(session_id)
                    return
                
                self._update_progress(session_id, ProcessingStage.DENSE_RECONSTRUCTION,
                                    ProcessingStatus.RUNNING, 75.0,
                                    "Performing dense reconstruction")
                
                dense_dir = workspace_dir / "dense"
                dense_dir.mkdir(exist_ok=True)
                
                # Image undistortion
                self._run_colmap_command([
                    "colmap", "image_undistorter",
                    "--image_path", str(images_dir),
                    "--input_path", str(model_dir),
                    "--output_path", str(dense_dir),
                    "--output_type", "COLMAP"
                ], session_id)
                
                # Patch match stereo
                self._run_colmap_command([
                    "colmap", "patch_match_stereo",
                    "--workspace_path", str(dense_dir)
                ], session_id)
                
                # Stereo fusion
                self._run_colmap_command([
                    "colmap", "stereo_fusion",
                    "--workspace_path", str(dense_dir),
                    "--output_path", str(dense_dir / "fused.ply")
                ], session_id)
                
                dense_ply_path = dense_dir / "fused.ply"
                if dense_ply_path.exists():
                    output_files.append({"type": "dense_pointcloud", "path": str(dense_ply_path)})
            
            # Mesh generation (optional)
            if self.enable_meshing and self.enable_dense_reconstruction:
                if self._cancel_flags[session_id].is_set():
                    self._handle_cancellation(session_id)
                    return
                
                self._update_progress(session_id, ProcessingStage.MESH_GENERATION,
                                    ProcessingStatus.RUNNING, 90.0,
                                    "Generating mesh from dense point cloud")
                
                mesh_dir = workspace_dir / "mesh"
                mesh_dir.mkdir(exist_ok=True)
                
                # Poisson meshing
                self._run_colmap_command([
                    "colmap", "poisson_mesher",
                    "--input_path", str(dense_dir / "fused.ply"),
                    "--output_path", str(mesh_dir / "mesh.ply")
                ], session_id)
                
                mesh_ply_path = mesh_dir / "mesh.ply"
                if mesh_ply_path.exists():
                    output_files.append({"type": "mesh", "path": str(mesh_ply_path)})
            
            # Create compressed archive
            self._create_model_archive(session_id, workspace_dir, output_files)
            
            # Update final progress
            self._update_progress(session_id, ProcessingStage.COMPLETED,
                                ProcessingStatus.COMPLETED, 100.0,
                                "COLMAP processing completed successfully",
                                output_files=output_files)
            
        except Exception as e:
            self.logger.error(f"COLMAP processing failed for session {session_id}: {str(e)}")
            self._update_progress(session_id, ProcessingStage.ERROR,
                                ProcessingStatus.ERROR, 0.0,
                                f"Processing failed: {str(e)}",
                                error_message=str(e))
    
    def _run_colmap_command(self, command: List[str], session_id: str):
        """Run a COLMAP command with error handling and cancellation support."""
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Monitor for cancellation
            while process.poll() is None:
                if self._cancel_flags[session_id].is_set():
                    process.terminate()
                    process.wait(timeout=5)
                    raise ColmapError("Processing cancelled by user")
                time.sleep(0.1)
            
            if process.returncode != 0:
                stderr_output = process.stderr.read()
                raise ColmapError(f"COLMAP command failed: {stderr_output}")
                
        except subprocess.TimeoutExpired:
            process.kill()
            raise ColmapError("COLMAP command timed out")
    
    def _create_model_archive(self, session_id: str, workspace_dir: Path, output_files: List[Dict]):
        """Create a compressed archive of the generated models."""
        archive_path = workspace_dir / f"model_{session_id}.zip"
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add model files
            for file_info in output_files:
                file_path = Path(file_info['path'])
                if file_path.exists():
                    arcname = f"{file_info['type']}/{file_path.name}"
                    zipf.write(file_path, arcname)
            
            # Add metadata
            metadata = {
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "output_files": output_files,
                "processing_parameters": {
                    "enable_dense_reconstruction": self.enable_dense_reconstruction,
                    "enable_meshing": self.enable_meshing,
                    "max_image_size": self.max_image_size,
                    "matcher_type": self.matcher_type
                }
            }
            
            metadata_path = workspace_dir / "model_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            zipf.write(metadata_path, "metadata.json")
    
    def _update_progress(self, session_id: str, stage: ProcessingStage, 
                        status: ProcessingStatus, progress_percent: float, 
                        message: str, error_message: str = None, 
                        output_files: List[Dict] = None):
        """Update progress for a session."""
        if session_id in self._progress:
            self._progress[session_id].stage = stage
            self._progress[session_id].status = status
            self._progress[session_id].progress_percent = progress_percent
            self._progress[session_id].message = message
            if error_message:
                self._progress[session_id].error_message = error_message
            if output_files:
                self._progress[session_id].output_files = output_files
            if status in [ProcessingStatus.COMPLETED, ProcessingStatus.ERROR, ProcessingStatus.CANCELLED]:
                self._progress[session_id].end_time = datetime.now().isoformat()
    
    def _handle_cancellation(self, session_id: str):
        """Handle processing cancellation."""
        self._update_progress(session_id, ProcessingStage.CANCELLED,
                            ProcessingStatus.CANCELLED, 0.0,
                            "Processing cancelled by user")
    
    def get_progress(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get progress information for a session."""
        if session_id not in self._progress:
            return None
        
        progress = self._progress[session_id]
        return {
            "session_id": progress.session_id,
            "stage": progress.stage,
            "status": progress.status,
            "progress_percent": progress.progress_percent,
            "message": progress.message,
            "start_time": progress.start_time,
            "end_time": progress.end_time,
            "error_message": progress.error_message,
            "output_files": progress.output_files or []
        }
    
    def cancel_processing(self, session_id: str) -> bool:
        """Cancel processing for a session."""
        if session_id in self._cancel_flags:
            self._cancel_flags[session_id].set()
            return True
        return False
    
    def cleanup_session_data(self, session_id: str, force: bool = False) -> bool:
        """Clean up session data and temporary files."""
        try:
            # Cancel processing if still running
            if session_id in self._processing_threads:
                if self._processing_threads[session_id].is_alive() and not force:
                    return False
                self.cancel_processing(session_id)
            
            # Remove workspace directory
            workspace_dir = self.base_output_dir / f"colmap_session_{session_id}"
            if workspace_dir.exists():
                shutil.rmtree(workspace_dir)
            
            # Clean up tracking data
            if session_id in self._progress:
                del self._progress[session_id]
            if session_id in self._processing_threads:
                del self._processing_threads[session_id]
            if session_id in self._cancel_flags:
                del self._cancel_flags[session_id]
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to cleanup session {session_id}: {str(e)}")
            return False


def create_colmap_processor(base_output_dir: str, **kwargs) -> ColmapProcessor:
    """
    Factory function to create a COLMAP processor instance.
    
    Args:
        base_output_dir: Base directory for output files
        **kwargs: Additional parameters for ColmapProcessor
        
    Returns:
        Configured ColmapProcessor instance
    """
    return ColmapProcessor(base_output_dir, **kwargs)


def validate_image_set(image_files: List[str]) -> Tuple[bool, str]:
    """
    Validate a set of images for COLMAP processing.
    
    Args:
        image_files: List of image file paths
        
    Returns:
        Tuple of (is_valid, validation_message)
    """
    if not image_files:
        return False, "No image files provided"
    
    if len(image_files) < 2:
        return False, "At least 2 images are required for 3D reconstruction"
    
    # Check if files exist and are accessible
    for image_path in image_files:
        if not os.path.exists(image_path):
            return False, f"Image file not found: {image_path}"
        
        if not os.access(image_path, os.R_OK):
            return False, f"Image file not readable: {image_path}"
    
    return True, f"Image set validation passed: {len(image_files)} images"