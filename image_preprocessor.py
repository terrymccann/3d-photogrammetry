import os
import logging
import math
from typing import Dict, List, Tuple, Optional, Any
from PIL import Image, ImageStat, ExifTags
from PIL.ExifTags import TAGS
import cv2
import numpy as np
import exifread
from datetime import datetime

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Image preprocessing module for photogrammetry applications.
    Handles image validation, resizing, EXIF extraction, and quality assessment.
    """
    
    def __init__(self, max_dimension: int = 1920, quality_threshold: float = 0.1):
        """
        Initialize the image preprocessor.
        
        Args:
            max_dimension: Maximum width or height for resized images
            quality_threshold: Minimum quality threshold for image validation
        """
        self.max_dimension = max_dimension
        self.quality_threshold = quality_threshold
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        
    def process_session_images(self, session_dir: str) -> Dict[str, Any]:
        """
        Process all images in a session directory.
        
        Args:
            session_dir: Path to the session directory containing images
            
        Returns:
            Dictionary containing processing results and statistics
        """
        if not os.path.exists(session_dir):
            raise FileNotFoundError(f"Session directory not found: {session_dir}")
        
        results = {
            'session_dir': session_dir,
            'processed_images': [],
            'failed_images': [],
            'statistics': {
                'total_images': 0,
                'processed_count': 0,
                'failed_count': 0,
                'average_dimensions': {'width': 0, 'height': 0},
                'total_file_size': 0,
                'quality_scores': []
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Get all image files in the directory
        image_files = self._get_image_files(session_dir)
        results['statistics']['total_images'] = len(image_files)
        
        if not image_files:
            logger.warning(f"No image files found in session directory: {session_dir}")
            return results
        
        logger.info(f"Processing {len(image_files)} images in session: {session_dir}")
        
        # Process each image
        total_width, total_height = 0, 0
        for image_file in image_files:
            try:
                image_info = self._process_single_image(image_file)
                results['processed_images'].append(image_info)
                results['statistics']['processed_count'] += 1
                
                # Accumulate statistics
                total_width += image_info['dimensions']['width']
                total_height += image_info['dimensions']['height']
                results['statistics']['total_file_size'] += image_info['file_size']
                results['statistics']['quality_scores'].append(image_info['quality_metrics']['overall_score'])
                
            except Exception as e:
                error_info = {
                    'filename': os.path.basename(image_file),
                    'filepath': image_file,
                    'error': str(e)
                }
                results['failed_images'].append(error_info)
                results['statistics']['failed_count'] += 1
                logger.error(f"Failed to process image {image_file}: {str(e)}")
        
        # Calculate average dimensions
        if results['statistics']['processed_count'] > 0:
            results['statistics']['average_dimensions'] = {
                'width': total_width // results['statistics']['processed_count'],
                'height': total_height // results['statistics']['processed_count']
            }
        
        logger.info(f"Session processing complete: {results['statistics']['processed_count']} processed, "
                   f"{results['statistics']['failed_count']} failed")
        
        return results
    
    def _get_image_files(self, directory: str) -> List[str]:
        """Get all image files from a directory."""
        image_files = []
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                _, ext = os.path.splitext(filename.lower())
                if ext in self.supported_formats:
                    image_files.append(filepath)
        return sorted(image_files)
    
    def _process_single_image(self, image_path: str) -> Dict[str, Any]:
        """
        Process a single image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing image information and processing results
        """
        filename = os.path.basename(image_path)
        logger.debug(f"Processing image: {filename}")
        
        # Basic file information
        file_size = os.path.getsize(image_path)
        
        # Validate and read image
        is_valid, validation_message = self._validate_image(image_path)
        if not is_valid:
            raise ValueError(f"Image validation failed: {validation_message}")
        
        # Load image with PIL for EXIF and basic processing
        with Image.open(image_path) as pil_image:
            original_dimensions = pil_image.size
            color_mode = pil_image.mode
            
            # Extract EXIF data
            exif_data = self._extract_exif_data(pil_image, image_path)
            
            # Convert to RGB if necessary
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Resize image if needed
            resized_image, resize_info = self._resize_image(pil_image)
            
            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(resized_image)
        
        # Load with OpenCV for additional analysis
        cv_image = cv2.imread(image_path)
        if cv_image is not None:
            # Additional OpenCV-based analysis
            blur_score = self._calculate_blur_score(cv_image)
            quality_metrics['blur_score'] = blur_score
        
        # Compile image information
        image_info = {
            'filename': filename,
            'filepath': image_path,
            'file_size': file_size,
            'original_dimensions': {
                'width': original_dimensions[0],
                'height': original_dimensions[1]
            },
            'dimensions': {
                'width': resized_image.size[0],
                'height': resized_image.size[1]
            },
            'color_mode': color_mode,
            'resize_info': resize_info,
            'exif_data': exif_data,
            'quality_metrics': quality_metrics,
            'processing_timestamp': datetime.now().isoformat()
        }
        
        return image_info
    
    def _validate_image(self, image_path: str) -> Tuple[bool, str]:
        """
        Validate an image file for common issues.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            # Check file exists and is readable
            if not os.path.exists(image_path):
                return False, "File does not exist"
            
            if not os.access(image_path, os.R_OK):
                return False, "File is not readable"
            
            # Check file size
            file_size = os.path.getsize(image_path)
            if file_size == 0:
                return False, "File is empty"
            
            if file_size > 50 * 1024 * 1024:  # 50MB limit
                return False, "File too large (>50MB)"
            
            # Try to open with PIL
            try:
                with Image.open(image_path) as img:
                    # Verify image
                    img.verify()
                
                # Re-open for further checks (verify() closes the image)
                with Image.open(image_path) as img:
                    # Check dimensions
                    width, height = img.size
                    if width < 100 or height < 100:
                        return False, "Image dimensions too small (minimum 100x100)"
                    
                    if width > 10000 or height > 10000:
                        return False, "Image dimensions too large (maximum 10000x10000)"
                    
                    # Check if image can be loaded
                    img.load()
                    
            except Exception as e:
                return False, f"PIL validation failed: {str(e)}"
            
            # Try to open with OpenCV as additional validation
            try:
                cv_image = cv2.imread(image_path)
                if cv_image is None:
                    return False, "OpenCV could not read the image"
            except Exception as e:
                return False, f"OpenCV validation failed: {str(e)}"
            
            return True, "Image validation passed"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def _extract_exif_data(self, pil_image: Image.Image, image_path: str) -> Dict[str, Any]:
        """Extract EXIF data from an image."""
        exif_data = {
            'has_exif': False,
            'camera_info': {},
            'gps_info': {},
            'datetime_info': {},
            'technical_info': {}
        }
        
        try:
            # Try PIL EXIF extraction first
            if hasattr(pil_image, '_getexif') and pil_image._getexif():
                exif_dict = pil_image._getexif()
                exif_data['has_exif'] = True
                
                for tag_id, value in exif_dict.items():
                    tag = TAGS.get(tag_id, tag_id)
                    
                    # Camera information
                    if tag in ['Make', 'Model', 'Software']:
                        exif_data['camera_info'][tag.lower()] = str(value)
                    
                    # Technical information
                    elif tag in ['ExposureTime', 'FNumber', 'ISO', 'FocalLength', 
                                'WhiteBalance', 'Flash', 'ExposureMode']:
                        exif_data['technical_info'][tag.lower()] = str(value)
                    
                    # Date/time information
                    elif tag in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                        exif_data['datetime_info'][tag.lower()] = str(value)
                    
                    # GPS information
                    elif tag == 'GPSInfo':
                        exif_data['gps_info'] = self._parse_gps_info(value)
            
            # Fallback to exifread for more detailed extraction
            if not exif_data['has_exif']:
                with open(image_path, 'rb') as f:
                    tags = exifread.process_file(f, details=False)
                    if tags:
                        exif_data['has_exif'] = True
                        for tag_name, tag_value in tags.items():
                            if 'GPS' in tag_name:
                                exif_data['gps_info'][tag_name] = str(tag_value)
                            elif any(cam_tag in tag_name for cam_tag in ['Make', 'Model', 'Software']):
                                exif_data['camera_info'][tag_name] = str(tag_value)
                            elif any(tech_tag in tag_name for tech_tag in 
                                   ['ExposureTime', 'FNumber', 'ISO', 'FocalLength']):
                                exif_data['technical_info'][tag_name] = str(tag_value)
        
        except Exception as e:
            logger.warning(f"EXIF extraction failed for {image_path}: {str(e)}")
        
        return exif_data
    
    def _parse_gps_info(self, gps_info: Dict) -> Dict[str, Any]:
        """Parse GPS information from EXIF data."""
        parsed_gps = {}
        try:
            if gps_info:
                for key, value in gps_info.items():
                    gps_tag = ExifTags.GPSTAGS.get(key, key)
                    parsed_gps[gps_tag] = str(value)
        except Exception as e:
            logger.warning(f"GPS parsing failed: {str(e)}")
        return parsed_gps
    
    def _resize_image(self, image: Image.Image) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Resize image to maximum dimension while maintaining aspect ratio.
        
        Args:
            image: PIL Image object
            
        Returns:
            Tuple of (resized_image, resize_info)
        """
        original_size = image.size
        width, height = original_size
        
        resize_info = {
            'was_resized': False,
            'original_size': original_size,
            'resize_factor': 1.0,
            'method': 'none'
        }
        
        # Check if resizing is needed
        max_dim = max(width, height)
        if max_dim <= self.max_dimension:
            return image, resize_info
        
        # Calculate new dimensions
        resize_factor = self.max_dimension / max_dim
        new_width = int(width * resize_factor)
        new_height = int(height * resize_factor)
        
        # Resize image using high-quality resampling
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        resize_info.update({
            'was_resized': True,
            'new_size': (new_width, new_height),
            'resize_factor': resize_factor,
            'method': 'LANCZOS'
        })
        
        logger.debug(f"Resized image from {original_size} to {(new_width, new_height)} "
                    f"(factor: {resize_factor:.3f})")
        
        return resized_image, resize_info
    
    def _calculate_quality_metrics(self, image: Image.Image) -> Dict[str, float]:
        """
        Calculate various quality metrics for an image.
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary containing quality metrics
        """
        try:
            # Convert to numpy array for calculations
            img_array = np.array(image)
            
            # Basic statistics
            stats = ImageStat.Stat(image)
            
            # Calculate brightness (average luminance)
            if len(img_array.shape) == 3:  # Color image
                # Convert to grayscale for brightness calculation
                gray = np.dot(img_array[...,:3], [0.2989, 0.5870, 0.1140])
                brightness = np.mean(gray) / 255.0
                
                # Calculate color variance (measure of color diversity)
                color_variance = np.mean([np.var(img_array[:,:,i]) for i in range(3)])
            else:  # Grayscale image
                brightness = np.mean(img_array) / 255.0
                color_variance = np.var(img_array)
            
            # Calculate contrast (standard deviation of pixel intensities)
            contrast = np.std(img_array) / 255.0
            
            # Calculate sharpness estimate using gradient magnitude
            if len(img_array.shape) == 3:
                gray_for_sharpness = np.dot(img_array[...,:3], [0.2989, 0.5870, 0.1140])
            else:
                gray_for_sharpness = img_array
            
            # Sobel operators for edge detection
            sobel_x = cv2.Sobel(gray_for_sharpness.astype(np.uint8), cv2.CV_64F, 1, 0, ksize=3)
            sobel_y = cv2.Sobel(gray_for_sharpness.astype(np.uint8), cv2.CV_64F, 0, 1, ksize=3)
            sharpness = np.mean(np.sqrt(sobel_x**2 + sobel_y**2)) / 255.0
            
            # Calculate overall quality score (weighted combination)
            overall_score = (
                0.3 * min(brightness, 1.0 - brightness) * 2 +  # Favor mid-range brightness
                0.3 * min(contrast, 1.0) +                     # Higher contrast is better
                0.4 * min(sharpness, 1.0)                      # Higher sharpness is better
            )
            
            quality_metrics = {
                'brightness': round(brightness, 3),
                'contrast': round(contrast, 3),
                'sharpness': round(sharpness, 3),
                'color_variance': round(color_variance, 3),
                'overall_score': round(overall_score, 3)
            }
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Quality metric calculation failed: {str(e)}")
            return {
                'brightness': 0.0,
                'contrast': 0.0,
                'sharpness': 0.0,
                'color_variance': 0.0,
                'overall_score': 0.0
            }
    
    def _calculate_blur_score(self, cv_image: np.ndarray) -> float:
        """
        Calculate blur score using Laplacian variance method.
        
        Args:
            cv_image: OpenCV image array
            
        Returns:
            Blur score (higher values indicate less blur)
        """
        try:
            # Convert to grayscale if needed
            if len(cv_image.shape) == 3:
                gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = cv_image
            
            # Calculate Laplacian variance
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Normalize to 0-1 range (higher = sharper)
            # Using log transformation to compress the range
            blur_score = min(1.0, math.log(laplacian_var + 1) / 10.0)
            
            return round(blur_score, 3)
            
        except Exception as e:
            logger.error(f"Blur score calculation failed: {str(e)}")
            return 0.0


def preprocess_session_images(session_dir: str, max_dimension: int = 1920) -> Dict[str, Any]:
    """
    Convenience function to preprocess images in a session directory.
    
    Args:
        session_dir: Path to session directory
        max_dimension: Maximum dimension for resized images
        
    Returns:
        Processing results dictionary
    """
    preprocessor = ImagePreprocessor(max_dimension=max_dimension)
    return preprocessor.process_session_images(session_dir)


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        session_path = sys.argv[1]
        results = preprocess_session_images(session_path)
        print(f"Processed {results['statistics']['processed_count']} images")
        print(f"Failed: {results['statistics']['failed_count']}")
        print(f"Average dimensions: {results['statistics']['average_dimensions']}")
    else:
        print("Usage: python image_preprocessor.py <session_directory>")