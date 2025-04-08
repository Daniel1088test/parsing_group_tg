import os
import logging
from django.conf import settings
from django.http import FileResponse, HttpResponseNotFound
import re
import shutil
import mimetypes
from pathlib import Path

logger = logging.getLogger('middleware')

class MediaFilesMiddleware:
    """Middleware to handle missing media files and create placeholders on demand"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # One-time configuration during initialization
        # Setup paths
        self.media_url = getattr(settings, 'MEDIA_URL', '/media/').rstrip('/') + '/'
        self.media_root = getattr(settings, 'MEDIA_ROOT', 'media')
        self.static_root = getattr(settings, 'STATIC_ROOT', 'staticfiles')
        
        # Ensure placeholder directories exist
        self._create_directories()
        
        # Create placeholder images if they don't exist
        self.create_placeholders()
        
        # Set up cache of known missing files to avoid multiple warnings
        self.known_missing_files = set()
        
        # Run a comprehensive scan to create placeholders for all missing files
        self._fix_missing_media_files()
        
        logger.info(f"MediaFilesMiddleware initialized (MEDIA_ROOT: {self.media_root})")
        
    def _create_directories(self):
        """Create necessary directories with proper permissions"""
        dirs_to_create = [
            os.path.join(self.static_root, 'img'),
            os.path.join(self.media_root, 'messages'),
            'data/sessions',
            os.path.join(self.static_root, 'media'),
            os.path.join(self.static_root, 'media', 'messages')
        ]
        
        for directory in dirs_to_create:
            try:
                # Check if directory exists before trying to create it
                if not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)
                    logger.info(f"Created directory: {directory}")
                
                # Set directory permissions to 0755
                try:
                    os.chmod(directory, 0o755)
                except Exception as e:
                    logger.warning(f"Could not set permissions on directory {directory}: {e}")
            except Exception as e:
                # Only log as error if it's not a "File exists" error
                if "File exists" not in str(e):
                    logger.error(f"Error creating directory {directory}: {e}")
                else:
                    # Log as info instead of error for "File exists"
                    logger.debug(f"Directory already exists: {directory}")
        
    def create_placeholders(self):
        """Create placeholder images if they don't exist"""
        try:
            # Define placeholder paths
            image_placeholder = os.path.join(self.static_root, 'img', 'placeholder-image.png')
            video_placeholder = os.path.join(self.static_root, 'img', 'placeholder-video.png')
            
            # Copy placeholders to media directory for direct access
            media_image = os.path.join(self.static_root, 'media', 'placeholder-image.png')
            media_video = os.path.join(self.static_root, 'media', 'placeholder-video.png')
            messages_image = os.path.join(self.media_root, 'messages', 'placeholder-image.png')
            messages_video = os.path.join(self.media_root, 'messages', 'placeholder-video.png')
            media_msg_image = os.path.join(self.static_root, 'media', 'messages', 'placeholder-image.png')
            media_msg_video = os.path.join(self.static_root, 'media', 'messages', 'placeholder-video.png')
            
            # Create image placeholder
            if not os.path.exists(image_placeholder):
                try:
                    from PIL import Image, ImageDraw
                    img = Image.new('RGB', (300, 200), color=(240, 240, 240))
                    draw = ImageDraw.Draw(img)
                    draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
                    draw.text((150, 100), "IMAGE", fill=(100, 100, 100))
                    img.save(image_placeholder)
                    logger.info(f"Created placeholder image: {image_placeholder}")
                    
                    # Set file permissions
                    os.chmod(image_placeholder, 0o644)
                except ImportError:
                    # If PIL is not available, create a simple 1x1 transparent PNG
                    with open(image_placeholder, 'wb') as f:
                        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
                    logger.warning(f"Created basic placeholder: {image_placeholder} (PIL not available)")
                    
            # Create video placeholder
            if not os.path.exists(video_placeholder):
                try:
                    from PIL import Image, ImageDraw
                    img = Image.new('RGB', (300, 200), color=(240, 240, 240))
                    draw = ImageDraw.Draw(img)
                    draw.rectangle([(0, 0), (299, 199)], outline=(200, 200, 200), width=2)
                    draw.text((150, 100), "VIDEO", fill=(100, 100, 100))
                    img.save(video_placeholder)
                    logger.info(f"Created placeholder video: {video_placeholder}")
                    
                    # Set file permissions
                    os.chmod(video_placeholder, 0o644)
                except ImportError:
                    # If PIL is not available, create a simple 1x1 transparent PNG
                    with open(video_placeholder, 'wb') as f:
                        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
                    logger.warning(f"Created basic placeholder: {video_placeholder} (PIL not available)")
                    
            # Copy placeholder to various directories for direct access
            for src, dest in [
                (image_placeholder, media_image),
                (video_placeholder, media_video),
                (image_placeholder, messages_image),
                (video_placeholder, messages_video),
                (image_placeholder, media_msg_image),
                (video_placeholder, media_msg_video)
            ]:
                if os.path.exists(src) and not os.path.exists(dest):
                    try:
                        # Ensure directory exists
                        os.makedirs(os.path.dirname(dest), exist_ok=True)
                        shutil.copy2(src, dest)
                        logger.info(f"Copied placeholder to directory: {dest}")
                        os.chmod(dest, 0o644)
                    except Exception as e:
                        logger.warning(f"Could not copy placeholder {src} to {dest}: {e}")
                        
        except Exception as e:
            logger.error(f"Error creating placeholders: {e}")
    
    def _fix_missing_media_files(self):
        """Create placeholders for all media files referenced in the DB but missing from filesystem"""
        try:
            # Import here to avoid circular imports
            from django.apps import apps
            
            # Check if media model exists
            try:
                Message = apps.get_model('admin_panel', 'Message')
                
                # Get all messages with media
                messages_with_media = Message.objects.exclude(media='').exclude(media__isnull=True)
                logger.info(f"Found {len(messages_with_media)} messages with media references")
                
                for message in messages_with_media:
                    try:
                        media_path = message.media.path if hasattr(message.media, 'path') else os.path.join(self.media_root, str(message.media))
                        
                        # Check if file exists
                        if not os.path.exists(media_path):
                            # Create directory structure if needed
                            os.makedirs(os.path.dirname(media_path), exist_ok=True)
                            
                            # Select placeholder based on media type
                            is_video = message.media_type == 'video' if hasattr(message, 'media_type') else False
                            placeholder_src = os.path.join(self.static_root, 'img', 'placeholder-video.png' if is_video else 'placeholder-image.png')
                            
                            try:
                                # Copy placeholder to location
                                shutil.copy2(placeholder_src, media_path)
                                logger.info(f"Created placeholder for {media_path}")
                                
                                # Set permissions
                                os.chmod(media_path, 0o644)
                            except Exception as e:
                                # Fall through to next attempt
                                logger.warning(f"Could not create placeholder at {media_path}: {e}")
                                
                                # Try alternate location
                                alt_path = os.path.join(self.static_root, 'media', str(message.media))
                                try:
                                    os.makedirs(os.path.dirname(alt_path), exist_ok=True)
                                    shutil.copy2(placeholder_src, alt_path)
                                    logger.info(f"Created alternate placeholder at {alt_path}")
                                except Exception as inner_e:
                                    logger.warning(f"Could not create alternate placeholder: {inner_e}")
                            
                            # Add to known missing files
                            self.known_missing_files.add(media_path)
                    except Exception as e:
                        logger.warning(f"Error processing message media: {e}")
                
            except LookupError:
                logger.warning("Could not find Message model, skipping database media check")
                
        except Exception as e:
            logger.error(f"Error fixing missing media files: {e}")
    
    def __call__(self, request):
        # Check if this is a media file request before running the main view
        if request.path.startswith(self.media_url):
            # Extract the relative path
            rel_path = request.path[len(self.media_url):]
            
            # Handle paths that might have no extension or incorrect extension
            file_ext = os.path.splitext(rel_path)[1].lower()
            
            # For files without extensions, try to detect media type from filename patterns
            is_image = file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
            is_video = file_ext in ['.mp4', '.webm', '.ogg', '.mov']
            
            # If no extension, try to infer from filename patterns
            if not file_ext:
                # Check for typical telegram naming patterns
                if re.search(r'_\d{8}_\d{6}(_[a-f0-9]+)?$', rel_path):
                    # If filename ends with timestamp (and optional hash), assume image
                    is_image = True
                    # Try both with and without extension
                    rel_paths_to_check = [rel_path, f"{rel_path}.jpg", f"{rel_path}.png"]
                elif 'video' in rel_path.lower():
                    is_video = True
                    rel_paths_to_check = [rel_path, f"{rel_path}.mp4"]
                else:
                    # Default to image if unsure
                    is_image = True
                    rel_paths_to_check = [rel_path, f"{rel_path}.jpg"]
            else:
                rel_paths_to_check = [rel_path]
            
            # Try to find the file with various paths
            file_found = False
            for path_to_check in rel_paths_to_check:
                full_path = os.path.join(self.media_root, path_to_check)
                if os.path.exists(full_path) and os.path.isfile(full_path):
                    try:
                        # Serve the file directly
                        logger.info(f"Serving media file: {full_path}")
                        return FileResponse(open(full_path, 'rb'))
                    except Exception as e:
                        logger.error(f"Error serving media file {full_path}: {e}")
                    else:
                        file_found = True
                        break
            
            # If file not found in primary location, check static/media directory
            if not file_found:
                static_media_path = os.path.join(self.static_root, 'media', rel_path)
                if os.path.exists(static_media_path) and os.path.isfile(static_media_path):
                    try:
                        # Serve the file from static/media
                        logger.info(f"Serving static media file: {static_media_path}")
                        return FileResponse(open(static_media_path, 'rb'))
                    except Exception as e:
                        logger.error(f"Error serving static media file {static_media_path}: {e}")
                    else:
                        file_found = True
            
            # If no file was found through any of the attempts
            if not file_found:
                # Only log warning if we haven't seen this file before
                if full_path not in self.known_missing_files:
                    logger.warning(f"Media file not found: {rel_path}")
                    self.known_missing_files.add(full_path)
                
                # Create a placeholder at the requested location
                try:
                    # Select appropriate placeholder
                    placeholder = os.path.join(self.static_root, 'img', 'placeholder-video.png' if is_video else 'placeholder-image.png')
                    
                    # Create directory if needed
                    target_dir = os.path.dirname(full_path)
                    if not os.path.exists(target_dir):
                        os.makedirs(target_dir, exist_ok=True)
                        logger.info(f"Created directory for placeholder: {target_dir}")
                    
                    # Only create placeholder if we have write access
                    if os.access(target_dir, os.W_OK):
                        # Copy placeholder to requested location
                        try:
                            shutil.copy2(placeholder, full_path)
                            os.chmod(full_path, 0o644)
                            logger.info(f"Created placeholder at {full_path}")
                        except Exception as e:
                            logger.warning(f"Could not create placeholder at {full_path}: {e}")
                except Exception as e:
                    logger.warning(f"Error creating placeholder directory structure: {e}")
                
                # Return appropriate placeholder directly
                try:
                    placeholder = os.path.join(self.static_root, 'img', 'placeholder-video.png' if is_video else 'placeholder-image.png')
                    if os.path.exists(placeholder):
                        response = FileResponse(open(placeholder, 'rb'))
                        # Set appropriate content type for the placeholder
                        response['Content-Type'] = 'image/png'
                        return response
                    else:
                        logger.error(f"Placeholder not found: {placeholder}")
                        return HttpResponseNotFound("Media file not found")
                except Exception as e:
                    logger.error(f"Error serving placeholder: {e}")
                    return HttpResponseNotFound("Media file not found")

        # For non-media requests or if we didn't handle the media, pass to the next middleware
        response = self.get_response(request)
        
        # Post-processing for 404 responses that might be media files
        if response.status_code == 404:
            # Check if this is a media-like path that wasn't caught earlier (could be server-side routing issues)
            media_path_match = re.match(r'^/(?:media/)?(.+?)(?:\.\w+)?$', request.path)
            if media_path_match:
                try:
                    file_name = media_path_match.group(1)
                    # Only log warning if we haven't seen this file before
                    full_path = os.path.join(self.media_root, file_name)
                    if full_path not in self.known_missing_files:
                        logger.warning(f"404 for possible media file: {file_name}")
                        self.known_missing_files.add(full_path)
                    
                    # Try to detect if this is a video or image
                    file_ext = os.path.splitext(file_name)[1].lower()
                    is_video = file_ext in ['.mp4', '.webm', '.ogg', '.mov', '.avi'] or 'video' in file_name.lower()
                    
                    placeholder = os.path.join(self.static_root, 'img', 'placeholder-video.png' if is_video else 'placeholder-image.png')
                    
                    # Try to use the placeholder
                    if os.path.exists(placeholder):
                        response = FileResponse(open(placeholder, 'rb'))
                        response['Content-Type'] = 'image/png'
                        response['X-Media-Placeholder'] = 'true'
                        return response
                        
                except Exception as e:
                    logger.error(f"Error serving placeholder for {request.path}: {e}")
                
        return response 