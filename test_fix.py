#!/usr/bin/env python3
"""
Test script to verify the COLMAP archive creation fix
"""

import sys
import logging
from pathlib import Path
from colmap_wrapper import ColmapProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_colmap_fix():
    """Test COLMAP processing with the archive creation fix"""
    
    # Use the images from the previous failed session
    session_id = "test-fix-session"
    image_dir = Path("uploads/9318337b-e7a2-4662-8d44-4401f83fef44")
    
    if not image_dir.exists():
        logger.error(f"Image directory not found: {image_dir}")
        return False
    
    # Get all images from the directory
    image_files = list(image_dir.glob("*.jpg"))
    if not image_files:
        logger.error("No images found in directory")
        return False
    
    logger.info(f"Found {len(image_files)} images to process")
    
    # Create COLMAP processor
    try:
        processor = ColmapProcessor(
            base_output_dir="outputs",
            enable_dense_reconstruction=False,  # Keep it simple for this test
            enable_meshing=False,
            cleanup_temp_files=False
        )
        logger.info("COLMAP processor initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize COLMAP processor: {str(e)}")
        return False
    
    # Process images synchronously
    try:
        logger.info("Starting COLMAP processing...")
        result = processor.process_images(
            session_id=session_id,
            image_files=[str(f) for f in image_files],
            async_mode=False
        )
        
        logger.info(f"Processing result: {result}")
        
        if result.get("status") == "completed":
            logger.info("✅ SUCCESS! COLMAP processing completed successfully")
            output_files = result.get("output_files", [])
            for file_info in output_files:
                logger.info(f"  - Generated: {file_info}")
            return True
        else:
            logger.error(f"❌ FAILED! Processing status: {result.get('status')}")
            logger.error(f"Error: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ FAILED! Exception during processing: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_colmap_fix()
    sys.exit(0 if success else 1)