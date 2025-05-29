#!/usr/bin/env python3
"""
Test script for COLMAP integration with the 3D Photogrammetry Flask App

This script demonstrates the complete workflow:
1. Upload test images
2. Start COLMAP processing
3. Monitor progress
4. Retrieve results

Usage:
    python test_colmap_integration.py [test_images_directory]

Requirements:
    - Flask app running on localhost:5000
    - Test images in the specified directory (default: test_images/)
    - requests library: pip install requests
"""

import os
import sys
import time
import json
import requests
from pathlib import Path
from typing import List, Dict, Any


class ColmapTestClient:
    """Test client for COLMAP integration."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
    def health_check(self) -> Dict[str, Any]:
        """Check if the API is healthy and COLMAP is available."""
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Health check failed: {e}")
            return {}
    
    def upload_images(self, image_paths: List[str]) -> Dict[str, Any]:
        """Upload images to the server."""
        files = []
        
        try:
            for image_path in image_paths:
                if not os.path.exists(image_path):
                    print(f"Warning: Image not found: {image_path}")
                    continue
                
                files.append(('files', (
                    os.path.basename(image_path),
                    open(image_path, 'rb'),
                    'image/jpeg'
                )))
            
            if not files:
                raise ValueError("No valid image files found")
            
            print(f"Uploading {len(files)} images...")
            response = self.session.post(f"{self.base_url}/upload", files=files)
            
            # Close file handles
            for _, file_tuple in files:
                file_tuple[1].close()
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            print(f"Upload failed: {e}")
            return {}
        except Exception as e:
            print(f"Error during upload: {e}")
            return {}
    
    def start_processing(self, session_id: str,
                        enable_dense: bool = True,
                        enable_mesh: bool = False,
                        max_image_size: int = 1920,
                        matcher_type: str = "exhaustive") -> Dict[str, Any]:
        """Start processing for a session using the main /process endpoint."""
        try:
            data = {
                'session_id': session_id,
                'enable_dense_reconstruction': enable_dense,
                'enable_meshing': enable_mesh,
                'max_image_size': max_image_size,
                'matcher_type': matcher_type
            }
            
            print(f"Starting processing for session {session_id}...")
            response = self.session.post(
                f"{self.base_url}/process",
                json=data
            )
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            print(f"Processing start failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = e.response.json()
                    print(f"Error details: {json.dumps(error_details, indent=2)}")
                except:
                    print(f"Response text: {e.response.text}")
            return {}
    
    def get_status(self, session_id: str) -> Dict[str, Any]:
        """Get processing status using the main /status endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/status/{session_id}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Status check failed: {e}")
            return {}
    
    def get_download_info(self, session_id: str) -> Dict[str, Any]:
        """Get download information for a session."""
        try:
            response = self.session.get(f"{self.base_url}/download/{session_id}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Download info failed: {e}")
            return {}
    
    def download_file(self, session_id: str, filename: str, save_path: str = None) -> bool:
        """Download an individual file from a session."""
        try:
            response = self.session.get(f"{self.base_url}/download/{session_id}/file/{filename}")
            response.raise_for_status()
            
            if save_path is None:
                save_path = filename
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            print(f"Downloaded: {filename} -> {save_path}")
            return True
        except requests.RequestException as e:
            print(f"Download failed for {filename}: {e}")
            return False
    
    def monitor_processing(self, session_id: str, max_wait_time: int = 600) -> Dict[str, Any]:
        """Monitor processing until completion or timeout."""
        start_time = time.time()
        last_status = None
        
        print("Monitoring processing progress...")
        
        while time.time() - start_time < max_wait_time:
            status_data = self.get_status(session_id)
            
            if not status_data:
                print("Failed to get status")
                break
            
            current_status = status_data.get('status', 'unknown')
            current_message = status_data.get('message', 'No message')
            
            # Print status updates only when status changes
            if current_status != last_status:
                print(f"Status: {current_status} - {current_message}")
                last_status = current_status
                
                # Show detailed progress if available
                if 'detailed_progress' in status_data:
                    detailed = status_data['detailed_progress']
                    progress_percent = detailed.get('progress_percent', 0)
                    stage = detailed.get('stage', 'unknown')
                    stage_message = detailed.get('stage_message', '')
                    print(f"  Progress: {progress_percent:.1f}% ({stage}: {stage_message})")
            
            if current_status == 'complete':
                print("✅ Processing completed successfully!")
                return status_data
            elif current_status == 'error':
                print("❌ Processing failed!")
                error_msg = status_data.get('error', 'Unknown error')
                print(f"Error: {error_msg}")
                return status_data
            
            time.sleep(5)  # Wait 5 seconds before next check
        
        print("⏰ Timeout waiting for processing to complete")
        return self.get_status(session_id)


def find_test_images(directory: str = "test_images") -> List[str]:
    """Find test images in the specified directory."""
    if not os.path.exists(directory):
        print(f"Test images directory not found: {directory}")
        return []
    
    valid_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp'}
    image_files = []
    
    for file_path in Path(directory).iterdir():
        if file_path.is_file() and file_path.suffix.lower() in valid_extensions:
            image_files.append(str(file_path))
    
    return sorted(image_files)


def create_sample_images_info():
    """Provide information about sample images for testing."""
    info = """
To test the COLMAP integration, you need a set of overlapping images of the same object/scene.

Sample image requirements:
- At least 3-5 images (more is better for reconstruction quality)
- Images should have significant overlap (50-80%)
- Object/scene should be photographed from different angles
- Good lighting and sharp focus
- Avoid pure rotation around a single axis

You can download sample datasets from:
- COLMAP datasets: https://colmap.github.io/datasets.html
- Computer Vision datasets: https://cvg.ethz.ch/research/local-features/
- Or create your own by photographing an object from multiple angles

Place your test images in a directory called 'test_images/' in the project root.
"""
    return info


def main():
    """Main test function."""
    print("🔧 COLMAP Integration Test")
    print("=" * 50)
    
    # Get test images directory from command line or use default
    test_dir = sys.argv[1] if len(sys.argv) > 1 else "test_images"
    
    # Find test images
    image_files = find_test_images(test_dir)
    
    if not image_files:
        print(f"❌ No test images found in directory: {test_dir}")
        print(create_sample_images_info())
        return 1
    
    print(f"📸 Found {len(image_files)} test images:")
    for img in image_files[:5]:  # Show first 5
        print(f"   - {os.path.basename(img)}")
    if len(image_files) > 5:
        print(f"   ... and {len(image_files) - 5} more")
    
    # Initialize test client
    client = ColmapTestClient()
    
    # Health check
    print("\n🏥 Checking API health...")
    health = client.health_check()
    
    if not health:
        print("❌ API health check failed - is the Flask app running?")
        return 1
    
    print(f"✅ API Status: {health.get('status', 'unknown')}")
    
    # Check COLMAP availability
    services = health.get('services', {})
    if not services.get('colmap', False):
        print("❌ COLMAP not available - check installation")
        return 1
    
    print("✅ COLMAP is available")
    
    # Upload images
    print("\n📤 Uploading images...")
    upload_result = client.upload_images(image_files)
    
    if not upload_result or upload_result.get('upload_status') != 'success':
        print("❌ Image upload failed")
        if upload_result:
            print(f"Error details: {json.dumps(upload_result, indent=2)}")
        return 1
    
    session_id = upload_result['session_id']
    print(f"✅ Images uploaded successfully - Session ID: {session_id}")
    print(f"   Uploaded: {upload_result['files_uploaded']} files")
    
    # Start processing
    print("\n🚀 Starting processing...")
    processing_result = client.start_processing(
        session_id,
        enable_dense=True,
        enable_mesh=False,  # Disable mesh for faster testing
        max_image_size=1920,
        matcher_type="exhaustive"
    )
    
    if not processing_result:
        print("❌ Failed to start processing")
        return 1
    
    print("✅ Processing started")
    print(f"   Parameters: {json.dumps(processing_result.get('processing_parameters', {}), indent=2)}")
    
    # Monitor processing
    final_result = client.monitor_processing(session_id, max_wait_time=600)  # 10 minute timeout
    
    if not final_result:
        print("❌ Failed to get final results")
        return 1
    
    # Display results
    print("\n📊 Final Results:")
    print("=" * 30)
    
    if 'output_files' in final_result and final_result['output_files']:
        output_files = final_result['output_files']
        print("Generated output files:")
        
        for file_info in output_files:
            if isinstance(file_info, dict):
                file_type = file_info.get('type', 'unknown')
                file_format = file_info.get('format', 'unknown')
                file_path = file_info.get('path', '')
                file_size = file_info.get('size', 0)
                print(f"   {file_type} ({file_format}): {file_path} ({file_size:,} bytes)")
                
                # Show metadata if available
                metadata = file_info.get('metadata', {})
                if metadata:
                    vertex_count = metadata.get('vertex_count')
                    face_count = metadata.get('face_count')
                    if vertex_count:
                        print(f"     - Vertices: {vertex_count:,}")
                    if face_count:
                        print(f"     - Faces: {face_count:,}")
            else:
                print(f"   {file_info}")
    else:
        print("No output files information available")
    
    # Test download functionality
    if final_result.get('status') == 'complete':
        print("\n📥 Testing Download Functionality:")
        print("-" * 35)
        
        download_info = client.get_download_info(session_id)
        if download_info and 'available_files' in download_info:
            available_files = download_info['available_files']
            print(f"Available files for download: {len(available_files)}")
            
            # Try to download a few files
            download_count = 0
            for file_info in available_files[:3]:  # Download first 3 files
                filename = os.path.basename(file_info.get('download_url', ''))
                if filename:
                    download_path = f"downloaded_{filename}"
                    success = client.download_file(session_id, filename, download_path)
                    if success:
                        download_count += 1
                        # Check downloaded file
                        if os.path.exists(download_path):
                            downloaded_size = os.path.getsize(download_path)
                            print(f"   ✅ {filename} ({downloaded_size:,} bytes)")
                            # Clean up downloaded file
                            os.remove(download_path)
                        else:
                            print(f"   ❌ {filename} (file not found after download)")
                    else:
                        print(f"   ❌ {filename} (download failed)")
            
            if download_count > 0:
                print(f"✅ Successfully tested download of {download_count} files")
            else:
                print("❌ No files could be downloaded")
                
            # Show model metadata if available
            model_metadata = download_info.get('model_metadata', {})
            if model_metadata:
                print(f"\n📊 Model Metadata:")
                for model_type, metadata in model_metadata.items():
                    print(f"   {model_type}:")
                    if 'vertex_count' in metadata:
                        print(f"     - Vertices: {metadata['vertex_count']:,}")
                    if 'face_count' in metadata:
                        print(f"     - Faces: {metadata['face_count']:,}")
                    if 'bounding_box' in metadata:
                        bbox = metadata['bounding_box']
                        print(f"     - Bounding box: {bbox}")
        else:
            print("❌ No download information available")
    
    # Show processing summary
    if 'start_time' in final_result:
        start_time_str = final_result['start_time']
        end_time_str = final_result.get('end_time')
        
        if end_time_str:
            # Calculate processing time if both times available
            try:
                from datetime import datetime
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                processing_time = (end_time - start_time).total_seconds()
                print(f"\n⏱️ Processing completed in: {processing_time:.1f} seconds")
            except:
                print(f"\n⏱️ Started: {start_time_str}")
                if end_time_str:
                    print(f"   Completed: {end_time_str}")
    
    print("\n🎉 Test completed successfully!")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)