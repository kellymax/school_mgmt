from django.http import HttpResponseForbidden
from django.urls import reverse_lazy, resolve
from django.shortcuts import redirect

class RoleBasedAccessMiddleware:
    """
    Middleware to handle role-based access control.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Define public URLs that don't require authentication
        self.public_urls = [
            '/',  # Root URL (login page)
            '/logout/',
            '/password_reset/',
            '/password_reset/done/',
            '/reset/confirm/',
            '/reset/complete/',
            '/admin/login/',  # Admin login
        ]
        
        # Define role-based access rules (url_name: [allowed_roles])
        self.role_access_rules = {
            # Admin URLs
            'admin:index': ['admin'],
            'admin:auth_user_changelist': ['admin'],
            'admin:auth_user_add': ['admin'],
            'admin:auth_user_change': ['admin'],
            'admin:auth_user_delete': ['admin'],
            
            # Staff URLs
            'staff_dashboard': ['admin', 'teacher', 'accountant', 'librarian'],
            'view_staff': ['admin', 'teacher'],
            'edit_staff': ['admin'],
            'delete_staff': ['admin'],
            'assign_subjects': ['admin', 'teacher'],
            'assign_classes': ['admin', 'teacher'],
            
            # Student URLs
            'student_dashboard': ['student'],
            'register_student': ['admin'],
            'student_profile': ['student'],
            'edit_student': ['admin', 'teacher'],
            'delete_student': ['admin'],
            
            # Guardian URLs
            'guardian_dashboard': ['guardian'],
            'add_guardian': ['admin', 'teacher'],
            'edit_guardian': ['admin', 'teacher', 'guardian'],
            'delete_guardian': ['admin'],
            'view_guardian': ['admin', 'teacher', 'guardian'],
            
            # Class URLs
            'class_list': ['admin', 'teacher'],
            'class_detail': ['admin', 'teacher', 'guardian'],
            'create_class': ['admin'],
            'edit_class': ['admin'],
            'delete_class': ['admin'],
            
            # Attendance URLs
            'mark_attendance': ['admin', 'teacher'],
            'view_attendance': ['admin', 'teacher', 'guardian'],
            
            # Exam URLs
            'create_exam': ['admin', 'teacher'],
            'edit_exam': ['admin', 'teacher'],
            'delete_exam': ['admin'],
            'exam_results': ['admin', 'teacher', 'guardian'],
            
            # Fee URLs
            'create_fee_structure': ['admin', 'accountant'],
            'view_fees': ['admin', 'accountant', 'guardian'],
            'process_payment': ['admin', 'accountant'],
        }

    def __call__(self, request):
        # Get the current URL name
        current_url_name = resolve(request.path_info).url_name
        
        # Skip middleware for public URLs
        if any(request.path.startswith(url) for url in self.public_urls):
            return self.get_response(request)
            
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return redirect('schoolmanagement:login')
            
        # Superusers have access to everything
        if request.user.is_superuser:
            return self.get_response(request)
            
        # Get the user's role
        user_role = getattr(request.user, 'role', None)
        
        # Check if the current URL has access rules
        if current_url_name in self.role_access_rules:
            allowed_roles = self.role_access_rules[current_url_name]
            
            # Check if user's role is in the allowed roles
            if user_role not in allowed_roles:
                return HttpResponseForbidden("You don't have permission to access this page.")
        
        # Special case for guardian access
        if user_role == 'guardian':
            # Check if guardian is trying to access their own data
            if current_url_name in ['guardian_profile', 'view_guardian']:
                guardian_id = request.resolver_match.kwargs.get('guardian_id')
                if guardian_id and str(guardian_id) != str(request.user.guardian_profile.id):
                    return HttpResponseForbidden("You can only view your own profile.")
            
            # Check if guardian is trying to access their student's data
            if current_url_name in ['student_profile', 'view_attendance', 'exam_results']:
                student_id = request.resolver_match.kwargs.get('student_id')
                if student_id:
                    if not request.user.guardian_profile.students.filter(id=student_id).exists():
                        return HttpResponseForbidden("You can only view your own students' data.")
        
        return self.get_response(request)
