import logging
import traceback
import re
from django.template import Template, Context, TemplateDoesNotExist
from django.template.loader import get_template
from django.http import HttpResponse

logger = logging.getLogger('template_debug')

class TemplateRenderDebugMiddleware:
    """
    Middleware to debug template rendering issues
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Patch Django's Template render method to add debugging
        self._patch_template_render()
        logger.info("Template debugging middleware initialized")
    
    def _patch_template_render(self):
        """Monkey patch Django's Template.render to add debugging"""
        original_render = Template.render
        
        def debug_render(template_self, context):
            try:
                logger.info(f"Rendering template: {getattr(template_self, 'name', 'unknown')}")
                result = original_render(template_self, context)
                return result
            except Exception as e:
                logger.error(f"Error rendering template: {getattr(template_self, 'name', 'unknown')}")
                logger.error(f"Error details: {str(e)}")
                logger.error(traceback.format_exc())
                raise
        
        Template.render = debug_render
    
    def __call__(self, request):
        # Log request path
        logger.info(f"Processing request for: {request.path}")
        
        try:
            response = self.get_response(request)
            
            # Log template responses
            if hasattr(response, 'templates') and response.templates:
                for template in response.templates:
                    logger.info(f"Template used: {template.name}")
            
            # Special handling for /admin_panel/categories/ path
            if request.path == '/admin_panel/categories/':
                # Force render the template if it's not already rendered
                logger.info("Special handling for categories list page")
                
                # Try to directly render the template as a test
                try:
                    template = get_template('admin_panel/categories_list.html')
                    logger.info(f"Found template: {template.origin.name}")
                except TemplateDoesNotExist:
                    logger.error("Template 'admin_panel/categories_list.html' could not be found")
            
            return response
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            logger.error(traceback.format_exc())
            
            # Try to provide a helpful error page
            if 'TemplateDoesNotExist' in str(e):
                match = re.search(r"TemplateDoesNotExist: ([^'\"]+)", str(e))
                if match:
                    missing_template = match.group(1)
                    return HttpResponse(f"""
                    <html>
                        <head><title>Template Error</title></head>
                        <body>
                            <h1>Template Not Found</h1>
                            <p>The template <strong>{missing_template}</strong> could not be found.</p>
                            <p>Error details: {str(e)}</p>
                            <pre>{traceback.format_exc()}</pre>
                        </body>
                    </html>
                    """, content_type='text/html', status=500)
            
            # Re-raise the exception for the standard error handling
            raise 