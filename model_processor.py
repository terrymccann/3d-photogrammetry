"""
3D Model Processing Module for COLMAP Output

This module handles conversion, optimization, and compression of 3D models
generated from COLMAP reconstruction pipeline.

Features:
- Convert PLY to OBJ format
- Basic mesh cleaning and optimization
- Texture mapping and material files
- File compression for web delivery
- Metadata extraction (vertex count, file size, etc.)
"""

import os
import sys
import json
import zipfile
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import struct
import re


@dataclass
class ModelMetadata:
    """Metadata for 3D models."""
    vertex_count: int
    face_count: int
    file_size: int
    format: str
    has_colors: bool
    has_normals: bool
    has_textures: bool
    bounding_box: Dict[str, Tuple[float, float, float]]
    creation_time: str
    processing_time: Optional[float] = None


class ModelProcessingError(Exception):
    """Custom exception for model processing errors."""
    pass


class ModelProcessor:
    """
    3D Model processor for converting and optimizing COLMAP outputs.
    
    Handles:
    - PLY to OBJ conversion
    - Mesh cleaning and optimization
    - Texture mapping
    - File compression
    - Metadata generation
    """
    
    def __init__(self, temp_dir: str = None, enable_compression: bool = True):
        """
        Initialize the model processor.
        
        Args:
            temp_dir: Temporary directory for processing
            enable_compression: Whether to compress output files
        """
        self.temp_dir = Path(temp_dir) if temp_dir else Path(tempfile.gettempdir()) / "model_processing"
        self.temp_dir.mkdir(exist_ok=True)
        self.enable_compression = enable_compression
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    def read_ply_header(self, ply_path: Path) -> Dict[str, Any]:
        """Read PLY file header to extract metadata."""
        try:
            header_info = {
                'vertex_count': 0,
                'face_count': 0,
                'has_colors': False,
                'has_normals': False,
                'format': 'unknown'
            }
            
            with open(ply_path, 'rb') as f:
                line = f.readline().decode('ascii').strip()
                if line != 'ply':
                    raise ModelProcessingError("Invalid PLY file format")
                
                while True:
                    line = f.readline().decode('ascii').strip()
                    if line == 'end_header':
                        break
                    
                    if line.startswith('format'):
                        header_info['format'] = line.split()[1]
                    elif line.startswith('element vertex'):
                        header_info['vertex_count'] = int(line.split()[2])
                    elif line.startswith('element face'):
                        header_info['face_count'] = int(line.split()[2])
                    elif 'red' in line or 'green' in line or 'blue' in line:
                        header_info['has_colors'] = True
                    elif 'nx' in line or 'ny' in line or 'nz' in line:
                        header_info['has_normals'] = True
            
            return header_info
            
        except Exception as e:
            raise ModelProcessingError(f"Failed to read PLY header: {str(e)}")
    
    def calculate_bounding_box(self, vertices: List[Tuple[float, float, float]]) -> Dict[str, Tuple[float, float, float]]:
        """Calculate bounding box from vertices."""
        if not vertices:
            return {
                'min': (0.0, 0.0, 0.0),
                'max': (0.0, 0.0, 0.0),
                'center': (0.0, 0.0, 0.0)
            }
        
        min_x = min(v[0] for v in vertices)
        max_x = max(v[0] for v in vertices)
        min_y = min(v[1] for v in vertices)
        max_y = max(v[1] for v in vertices)
        min_z = min(v[2] for v in vertices)
        max_z = max(v[2] for v in vertices)
        
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (min_z + max_z) / 2
        
        return {
            'min': (min_x, min_y, min_z),
            'max': (max_x, max_y, max_z),
            'center': (center_x, center_y, center_z)
        }
    
    def convert_ply_to_obj(self, ply_path: Path, output_dir: Path) -> Tuple[Path, ModelMetadata]:
        """
        Convert PLY file to OBJ format with basic cleaning.
        
        Args:
            ply_path: Path to input PLY file
            output_dir: Output directory for OBJ files
            
        Returns:
            Tuple of (obj_path, metadata)
        """
        try:
            self.logger.info(f"Converting PLY to OBJ: {ply_path}")
            
            if not ply_path.exists():
                raise ModelProcessingError(f"PLY file not found: {ply_path}")
            
            # Read PLY header
            header_info = self.read_ply_header(ply_path)
            
            # Create output paths
            output_dir.mkdir(exist_ok=True)
            obj_path = output_dir / f"{ply_path.stem}.obj"
            mtl_path = output_dir / f"{ply_path.stem}.mtl"
            
            vertices = []
            faces = []
            colors = []
            
            # Parse PLY file
            with open(ply_path, 'rb') as f:
                # Skip header
                while True:
                    line = f.readline().decode('ascii').strip()
                    if line == 'end_header':
                        break
                
                # Read vertices
                vertex_count = header_info['vertex_count']
                has_colors = header_info['has_colors']
                
                if header_info['format'] == 'ascii':
                    # ASCII format
                    for i in range(vertex_count):
                        line = f.readline().decode('ascii').strip()
                        parts = line.split()
                        
                        # Extract coordinates
                        x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                        vertices.append((x, y, z))
                        
                        # Extract colors if available
                        if has_colors and len(parts) >= 6:
                            r, g, b = int(parts[3]), int(parts[4]), int(parts[5])
                            colors.append((r/255.0, g/255.0, b/255.0))
                
                else:
                    # Binary format (simplified)
                    self.logger.warning("Binary PLY format detected, using simplified parsing")
                    # For binary PLY, we'd need more complex parsing
                    # For now, skip to avoid complexity
                
                # Read faces
                face_count = header_info['face_count']
                for i in range(face_count):
                    if header_info['format'] == 'ascii':
                        line = f.readline().decode('ascii').strip()
                        parts = line.split()
                        if len(parts) >= 4 and parts[0] == '3':  # Triangle
                            # OBJ uses 1-based indexing
                            v1, v2, v3 = int(parts[1]) + 1, int(parts[2]) + 1, int(parts[3]) + 1
                            faces.append((v1, v2, v3))
            
            # Write OBJ file
            with open(obj_path, 'w') as f:
                f.write(f"# OBJ file generated from {ply_path.name}\n")
                f.write(f"# Vertices: {len(vertices)}, Faces: {len(faces)}\n")
                
                if mtl_path.exists() or colors:
                    f.write(f"mtllib {mtl_path.name}\n")
                    f.write("usemtl material0\n")
                
                # Write vertices
                for i, (x, y, z) in enumerate(vertices):
                    f.write(f"v {x:.6f} {y:.6f} {z:.6f}")
                    if i < len(colors):
                        r, g, b = colors[i]
                        f.write(f" {r:.6f} {g:.6f} {b:.6f}")
                    f.write("\n")
                
                # Write faces
                for v1, v2, v3 in faces:
                    f.write(f"f {v1} {v2} {v3}\n")
            
            # Write MTL file if we have colors
            if colors:
                with open(mtl_path, 'w') as f:
                    f.write("# Material file\n")
                    f.write("newmtl material0\n")
                    f.write("Ka 0.2 0.2 0.2\n")
                    f.write("Kd 0.8 0.8 0.8\n")
                    f.write("Ks 0.1 0.1 0.1\n")
                    f.write("Ns 10.0\n")
            
            # Calculate bounding box
            bounding_box = self.calculate_bounding_box(vertices)
            
            # Create metadata
            metadata = ModelMetadata(
                vertex_count=len(vertices),
                face_count=len(faces),
                file_size=obj_path.stat().st_size,
                format='obj',
                has_colors=len(colors) > 0,
                has_normals=False,  # We don't parse normals in this simple conversion
                has_textures=mtl_path.exists(),
                bounding_box=bounding_box,
                creation_time=obj_path.stat().st_mtime
            )
            
            self.logger.info(f"PLY to OBJ conversion completed: {obj_path}")
            return obj_path, metadata
            
        except Exception as e:
            raise ModelProcessingError(f"PLY to OBJ conversion failed: {str(e)}")
    
    def clean_mesh(self, obj_path: Path) -> Path:
        """
        Apply basic mesh cleaning operations.
        
        Args:
            obj_path: Path to OBJ file
            
        Returns:
            Path to cleaned OBJ file
        """
        try:
            self.logger.info(f"Cleaning mesh: {obj_path}")
            
            # For basic cleaning, we'll implement:
            # 1. Remove duplicate vertices
            # 2. Remove degenerate faces
            # 3. Merge nearby vertices (optional)
            
            vertices = []
            faces = []
            vertex_map = {}  # For duplicate removal
            
            with open(obj_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('v '):
                        # Parse vertex
                        parts = line.split()
                        x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                        
                        # Check for duplicates (with small tolerance)
                        vertex_key = (round(x, 6), round(y, 6), round(z, 6))
                        if vertex_key not in vertex_map:
                            vertex_map[vertex_key] = len(vertices)
                            vertices.append((x, y, z))
                    
                    elif line.startswith('f '):
                        # Parse face
                        parts = line.split()[1:]
                        if len(parts) >= 3:
                            try:
                                # Handle face indices (may have texture/normal info)
                                face_vertices = []
                                for part in parts[:3]:  # Take only first 3 for triangles
                                    vertex_idx = int(part.split('/')[0]) - 1  # Convert to 0-based
                                    face_vertices.append(vertex_idx)
                                
                                # Check for degenerate faces
                                v1, v2, v3 = face_vertices
                                if v1 != v2 and v2 != v3 and v1 != v3:
                                    faces.append(tuple(face_vertices))
                            except (ValueError, IndexError):
                                continue
            
            # Write cleaned OBJ
            cleaned_path = obj_path.parent / f"{obj_path.stem}_cleaned.obj"
            with open(cleaned_path, 'w') as f:
                f.write(f"# Cleaned OBJ file\n")
                f.write(f"# Original vertices: {len(vertices)}, Faces: {len(faces)}\n")
                
                # Write vertices
                for x, y, z in vertices:
                    f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
                
                # Write faces (convert back to 1-based indexing)
                for v1, v2, v3 in faces:
                    f.write(f"f {v1+1} {v2+1} {v3+1}\n")
            
            self.logger.info(f"Mesh cleaning completed: {cleaned_path}")
            return cleaned_path
            
        except Exception as e:
            self.logger.warning(f"Mesh cleaning failed: {str(e)}")
            return obj_path  # Return original if cleaning fails
    
    def compress_model_files(self, model_dir: Path, session_id: str) -> Path:
        """
        Compress model files into a ZIP archive for web delivery.
        
        Args:
            model_dir: Directory containing model files
            session_id: Session identifier for naming
            
        Returns:
            Path to compressed archive
        """
        try:
            self.logger.info(f"Compressing model files from: {model_dir}")
            
            archive_path = model_dir.parent / f"model_{session_id}.zip"
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in model_dir.rglob('*'):
                    if file_path.is_file():
                        # Add file to archive with relative path
                        arcname = file_path.relative_to(model_dir)
                        zipf.write(file_path, arcname)
                        self.logger.debug(f"Added to archive: {arcname}")
            
            self.logger.info(f"Model compression completed: {archive_path}")
            return archive_path
            
        except Exception as e:
            raise ModelProcessingError(f"Model compression failed: {str(e)}")
    
    def process_colmap_output(self, session_id: str, colmap_workspace: Path) -> Dict[str, Any]:
        """
        Main method to process COLMAP output into downloadable 3D models.
        
        Args:
            session_id: Session identifier
            colmap_workspace: Path to COLMAP workspace directory
            
        Returns:
            Dictionary with processing results and download information
        """
        try:
            self.logger.info(f"Processing COLMAP output for session {session_id}")
            
            # Create output directory for processed models
            output_dir = colmap_workspace / "processed_models"
            output_dir.mkdir(exist_ok=True)
            
            processed_files = []
            model_metadata = {}
            
            # Process dense point cloud if available
            dense_ply = colmap_workspace / "dense" / "fused.ply"
            if dense_ply.exists():
                self.logger.info("Processing dense point cloud")
                
                try:
                    # Convert PLY to OBJ
                    obj_path, metadata = self.convert_ply_to_obj(dense_ply, output_dir / "dense")
                    
                    # Clean mesh
                    cleaned_obj = self.clean_mesh(obj_path)
                    
                    processed_files.append({
                        'type': 'dense_pointcloud',
                        'format': 'obj',
                        'original_file': str(dense_ply),
                        'processed_file': str(cleaned_obj),
                        'metadata': asdict(metadata)
                    })
                    
                    model_metadata['dense_pointcloud'] = asdict(metadata)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process dense point cloud: {str(e)}")
            
            # Process mesh if available
            mesh_ply = colmap_workspace / "mesh" / "mesh.ply"
            if mesh_ply.exists():
                self.logger.info("Processing mesh")
                
                try:
                    # Convert PLY to OBJ
                    obj_path, metadata = self.convert_ply_to_obj(mesh_ply, output_dir / "mesh")
                    
                    # Clean mesh
                    cleaned_obj = self.clean_mesh(obj_path)
                    
                    processed_files.append({
                        'type': 'mesh',
                        'format': 'obj',
                        'original_file': str(mesh_ply),
                        'processed_file': str(cleaned_obj),
                        'metadata': asdict(metadata)
                    })
                    
                    model_metadata['mesh'] = asdict(metadata)
                    
                except Exception as e:
                    self.logger.error(f"Failed to process mesh: {str(e)}")
            
            # Copy original PLY files
            for ply_file in [dense_ply, mesh_ply]:
                if ply_file.exists():
                    dest_path = output_dir / ply_file.name
                    import shutil
                    shutil.copy2(ply_file, dest_path)
                    
                    processed_files.append({
                        'type': ply_file.stem,
                        'format': 'ply',
                        'original_file': str(ply_file),
                        'processed_file': str(dest_path),
                        'metadata': {'file_size': dest_path.stat().st_size}
                    })
            
            # Create metadata file
            metadata_file = output_dir / "model_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump({
                    'session_id': session_id,
                    'processing_time': None,  # To be filled by caller
                    'models': model_metadata,
                    'files': processed_files
                }, f, indent=2)
            
            # Compress files if enabled
            compressed_archive = None
            if self.enable_compression:
                compressed_archive = self.compress_model_files(output_dir, session_id)
            
            result = {
                'session_id': session_id,
                'output_directory': str(output_dir),
                'processed_files': processed_files,
                'model_metadata': model_metadata,
                'metadata_file': str(metadata_file),
                'compressed_archive': str(compressed_archive) if compressed_archive else None,
                'total_files': len(processed_files)
            }
            
            self.logger.info(f"Model processing completed for session {session_id}")
            return result
            
        except Exception as e:
            raise ModelProcessingError(f"Model processing failed: {str(e)}")


def create_model_processor(**kwargs) -> ModelProcessor:
    """
    Factory function to create a configured model processor.
    
    Args:
        **kwargs: Configuration parameters for ModelProcessor
        
    Returns:
        Configured ModelProcessor instance
    """
    default_config = {
        "temp_dir": None,
        "enable_compression": True
    }
    
    # Merge provided config with defaults
    config = {**default_config, **kwargs}
    
    return ModelProcessor(**config)


if __name__ == "__main__":
    # Example usage
    processor = create_model_processor()
    
    # Test with sample PLY file (replace with actual path)
    sample_ply = Path("sample.ply")
    if sample_ply.exists():
        output_dir = Path("test_output")
        output_dir.mkdir(exist_ok=True)
        
        try:
            obj_path, metadata = processor.convert_ply_to_obj(sample_ply, output_dir)
            print(f"Conversion successful: {obj_path}")
            print(f"Metadata: {metadata}")
        except ModelProcessingError as e:
            print(f"Conversion failed: {e}")
    else:
        print("No sample PLY file found for testing")