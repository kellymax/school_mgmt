import random
import string
from datetime import datetime
from django.db.models import Max
from .models import Student, Staff, Guardian

def generate_student_admission_number():
    """
    Generate a unique admission number for students in the format: ADM-YYYY-NNNN
    Where YYYY is the current year and NNNN is an auto-incrementing number
    """
    current_year = datetime.now().year
    
    # Get the highest admission number for the current year
    max_admission = Student.objects.filter(
        admission_number__startswith=f'ADM-{current_year}'
    ).aggregate(Max('admission_number'))['admission_number__max']
    
    if max_admission:
        # Extract the numeric part and increment
        last_num = int(max_admission.split('-')[-1])
        new_num = last_num + 1
    else:
        # First admission of the year
        new_num = 1
    
    return f'ADM-{current_year}-{new_num:04d}'

def generate_staff_number():
    """
    Generate a unique staff number in the format: STF-YYYY-NNNN
    Where YYYY is the current year and NNNN is an auto-incrementing number
    """
    current_year = datetime.now().year
    
    # Get the highest staff number for the current year
    max_staff = Staff.objects.filter(
        staff_id__startswith=f'STF-{current_year}'
    ).aggregate(Max('staff_id'))['staff_id__max']
    
    if max_staff:
        # Extract the numeric part and increment
        last_num = int(max_staff.split('-')[-1])
        new_num = last_num + 1
    else:
        # First staff of the year
        new_num = 1
    
    return f'STF-{current_year}-{new_num:04d}'

def generate_guardian_number():
    """
    Generate a unique guardian number in the format: GDN-YYYY-NNNN
    Where YYYY is the current year and NNNN is an auto-incrementing number
    """
    current_year = datetime.now().year
    
    # Get the highest guardian number for the current year
    max_guardian = Guardian.objects.filter(
        guardian_number__startswith=f'GDN-{current_year}'
    ).aggregate(Max('guardian_number'))['guardian_number__max']
    
    if max_guardian:
        # Extract the numeric part and increment
        last_num = int(max_guardian.split('-')[-1])
        new_num = last_num + 1
    else:
        # First guardian of the year
        new_num = 1
    
    return f'GDN-{current_year}-{new_num:04d}'

def generate_random_password(length=12):
    """Generate a random password with letters, digits, and special characters"""
    chars = string.ascii_letters + string.digits + '!@#$%^&*()_+=-'
    return ''.join(random.choice(chars) for _ in range(length))
