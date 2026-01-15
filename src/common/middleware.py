"""
Organization Middleware

Extracts organization context from HTTP requests and stores it for use
throughout the request lifecycle.
"""

from django.utils.deprecation import MiddlewareMixin
from .models import Organization


class OrganizationMiddleware(MiddlewareMixin):
    """
    Middleware to extract and store organization context from requests.
    
    Expects the organization code in the 'X-Organization' header or
    'organization' query parameter.
    
    If no organization is found, all attributes are set to None,
    which will cause permission checks to fail.
    """
    
    ORGANIZATION_HEADER = 'HTTP_X_ORGANIZATION'
    ORGANIZATION_QUERY_PARAM = 'organization'
    
    def process_request(self, request):
        """
        Extract organization from request and store in request object.
        """
        
        request.organization = None
        request.organization_id = None
        request.organization_code = None
        
        org_code = self._get_organization_code(request)
        
        if not org_code:
            return None
        
        try:
            org = Organization.objects.get(
                code=org_code,
                is_active=True
            )
            request.organization = org
            request.organization_id = org.id
            request.organization_code = org.code
            
        except Organization.DoesNotExist:
            pass
        except Organization.MultipleObjectsReturned:
            pass
        
        return None
    
    def _get_organization_code(self, request):
        """
        Extract organization code from request.
        """
        if self.ORGANIZATION_HEADER in request.META:
            code = request.META.get(self.ORGANIZATION_HEADER, '').strip()
            if code:
                return code
        
        code = request.GET.get(self.ORGANIZATION_QUERY_PARAM, '').strip()
        if code:
            return code
        
        return None


__all__ = ['OrganizationMiddleware']
