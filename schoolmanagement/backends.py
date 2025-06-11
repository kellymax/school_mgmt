from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .models import Student, Staff, Guardian

class CustomAuthBackend(ModelBackend):
    """
    Custom authentication backend that allows users to login with:
    - Username
    - Email
    - Student Admission Number
    - Staff Number
    - Guardian Number
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        
        if username is None or password is None:
            return
            
        try:
            # First try to find user by username or email
            user = UserModel._default_manager.get(
                Q(username__iexact=username) | 
                Q(email__iexact=username)
            )
        except UserModel.DoesNotExist:
            # If not found, check if it's a student admission number
            try:
                student = Student.objects.get(admission_number__iexact=username)
                user = student.user
            except Student.DoesNotExist:
                # If not a student, check if it's a staff number
                try:
                    staff = Staff.objects.get(staff_id__iexact=username)
                    user = staff.user
                except Staff.DoesNotExist:
                    # If not staff, check if it's a guardian number
                    try:
                        guardian = Guardian.objects.get(guardian_number__iexact=username)
                        user = guardian.user
                    except Guardian.DoesNotExist:
                        # No user found with the given identifier
                        return None
        
        # Verify the password for the found user
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
            
        return None
    
    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            user = UserModel._default_manager.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None
