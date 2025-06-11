from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse_lazy

def role_required(allowed_roles=None):
    """
    Decorator to check if the user has the required role.
    Usage: @role_required(['admin', 'teacher'])
    """
    if allowed_roles is None:
        allowed_roles = []
        
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(reverse_lazy('login'))
                
            # Superusers have access to everything
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
                
            # Check if user has one of the allowed roles
            user_role = getattr(request.user, 'role', None)
            if user_role not in allowed_roles:
                return HttpResponseForbidden("You don't have permission to access this page.")
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def guardian_required(view_func):
    """
    Decorator to check if the user is a guardian and has access to the student.
    Expects student_id in the view's kwargs.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse_lazy('login'))
            
        # Superusers and staff have access
        if request.user.is_superuser or request.user.is_staff:
            return view_func(request, *args, **kwargs)
            
        # Check if user is a guardian
        if not hasattr(request.user, 'guardian_profile'):
            return HttpResponseForbidden("Only guardians can access this page.")
            
        # Check if the guardian has access to the student
        student_id = kwargs.get('student_id')
        if student_id:
            if not request.user.guardian_profile.students.filter(id=student_id).exists():
                return HttpResponseForbidden("You don't have permission to access this student's data.")
                
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    """Decorator to check if the user is an admin."""
    return role_required(['admin'])(view_func)

def teacher_required(view_func):
    """Decorator to check if the user is a teacher or admin."""
    return role_required(['admin', 'teacher'])(view_func)

def accountant_required(view_func):
    """Decorator to check if the user is an accountant or admin."""
    return role_required(['admin', 'accountant'])(view_func)

def student_required(view_func):
    """Decorator to check if the user is a student."""
    return role_required(['student'])(view_func)

def guardian_only(view_func):
    """Decorator to check if the user is a guardian."""
    return role_required(['guardian'])(view_func)
