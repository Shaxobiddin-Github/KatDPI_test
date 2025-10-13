from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Set modern security and caching headers; avoid deprecated ones.
    - Use CSP frame-ancestors instead of X-Frame-Options
    - Drop X-XSS-Protection header
    - Prefer Cache-Control over Expires
    """

    def process_response(self, request, response):
        # Content Security Policy: forbid framing by default
        csp = "frame-ancestors 'none'"
        # If you need to allow your own domain/subdomains, adjust accordingly
        response.headers['Content-Security-Policy'] = csp

        # Remove deprecated X-XSS-Protection if present
        if 'X-XSS-Protection' in response.headers:
            del response.headers['X-XSS-Protection']

        # Prefer Cache-Control; avoid Expires
        if 'Expires' in response.headers:
            del response.headers['Expires']

        # For static-like paths, encourage caching; adjust as needed
        path = request.path or ''
        if any(path.startswith(p) for p in (settings.STATIC_URL, settings.MEDIA_URL)):
            # hashed filenames will be cache-busted; set long cache
            response.headers.setdefault('Cache-Control', 'public, max-age=31536000, immutable')
        else:
            # dynamic responses: short/no cache
            response.headers.setdefault('Cache-Control', 'no-store')
        return response
