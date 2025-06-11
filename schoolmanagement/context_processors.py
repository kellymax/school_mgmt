def user_roles(request):
    """
    Add user role information to the template context.
    """
    context = {}
    
    if hasattr(request, 'user') and request.user.is_authenticated:
        user = request.user
        context.update({
            'is_admin': user.role == 'admin' or user.is_superuser,
            'is_teacher': user.role == 'teacher',
            'is_student': user.role == 'student',
            'is_guardian': user.role == 'guardian',
            'is_accountant': user.role == 'accountant',
            'is_librarian': user.role == 'librarian',
            'user_role': user.get_role_display(),
            'user_role_code': user.role,
        })
        
        # Add guardian-specific context
        if hasattr(user, 'guardian_profile'):
            context.update({
                'guardian_profile': user.guardian_profile,
                'guardian_students': user.guardian_profile.get_associated_students(),
            })
    
    return context
