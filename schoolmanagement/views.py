from django.shortcuts import render, get_object_or_404, redirect
# Standard library imports
import time

# Django imports
from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Avg, Q, Sum
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode, url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.views.generic import View, FormView

# Django auth imports
from django.contrib.auth import (
    authenticate, 
    login as auth_login, 
    logout as auth_logout, 
    get_user_model,
    update_session_auth_hash
)
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import (
    AuthenticationForm, 
    UserCreationForm, 
    PasswordResetForm, 
    SetPasswordForm
)
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import default_token_generator

# Local application imports
from .models import (
    Class, Subject, Student, Staff, Guardian, Attendance, Exam, ExamResult, 
    FeeStructure, FeePayment, StudentClass, Timetable, FeeDiscount, FeeFine
)

User = get_user_model()

# Password validation help text
PASSWORD_VALIDATION_HELP_TEXT = """
Your password must contain at least 8 characters and cannot be too common or entirely numeric.
It should include both letters and numbers for better security.
"""

class CustomSetPasswordForm(SetPasswordForm):
    """
    A form that lets a user set their password without entering the old password
    using a custom template and styling.
    """
    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
        'password_too_common': _("This password is too common."),
        'password_entirely_numeric': _("This password is entirely numeric."),
        'password_too_short': _("This password is too short. It must contain at least 8 characters."),
    }
    
    new_password1 = forms.CharField(
        label=_("New password"),
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'class': 'form-control',
            'placeholder': _('Enter new password'),
            'data-toggle': 'tooltip',
            'title': _('Your password must contain at least 8 characters, including letters and numbers.')
        }),
        strip=False,
        help_text=_(PASSWORD_VALIDATION_HELP_TEXT),
    )
    new_password2 = forms.CharField(
        label=_("Confirm new password"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm new password'),
            'data-match': '#id_new_password1',
            'data-match-error': "Passwords don't match",
            'autocomplete': 'new-password'
        }),
        strip=False,
        help_text=_("Enter the same password as before, for verification.")
    )

class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'class': 'form-control',
            'placeholder': _('Enter your email address')
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError(_("There is no user registered with the specified email address."))
        return email

class CustomPasswordResetConfirmView(FormView):
    template_name = 'auth/password_reset_confirm.html'
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy('schoolmanagement:password_reset_complete')

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        # Get the uidb64 and token from the URL
        self.uidb64 = kwargs.get('uidb64')
        self.token = kwargs.get('token')
        
        # Try to get the user
        try:
            uid = force_str(urlsafe_base64_decode(self.uidb64))
            self.user = User._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            self.user = None
        
        # Check if the token is valid
        if self.user is not None and not default_token_generator.check_token(self.user, self.token):
            self.user = None
            
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'uidb64': self.uidb64,
            'token': self.token,
            'validlink': self.user is not None,
        })
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.user
        return kwargs
    
    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Your password has been set. You may now log in with your new password.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


from .decorators import guardian_required, role_required
from .sms_service import sms_service

@login_required
def dashboard(request):
    user = request.user
    
    if user.is_staff:
        # Admin dashboard
        total_students = Student.objects.count()
        total_staff = Staff.objects.count()
        pending_fees = FeePayment.objects.filter(payment_date__isnull=True).count()
        recent_exams = Exam.objects.order_by('-date')[:5]
        
        return render(request, 'dashboard/admin_dashboard.html', {
            'total_students': total_students,
            'total_staff': total_staff,
            'pending_fees': pending_fees,
            'recent_exams': recent_exams
        })
    
    elif hasattr(user, 'student'):
        # Student dashboard
        student = user.student
        classes = student.classes.all()
        recent_exams = Exam.objects.filter(class_level__in=classes).order_by('-date')[:5]
        upcoming_fees = FeeStructure.objects.filter(class_level__in=classes, due_date__gt=timezone.now())
        
        return render(request, 'dashboard/student_dashboard.html', {
            'student': student,
            'classes': classes,
            'recent_exams': recent_exams,
            'upcoming_fees': upcoming_fees
        })
    
    elif hasattr(user, 'staff'):
        # Staff dashboard
        staff = user.staff
        classes = Class.objects.filter(teachers=staff)
        recent_exams = Exam.objects.filter(class_level__in=classes).order_by('-date')[:5]
        
        return render(request, 'dashboard/teacher_dashboard.html', {
            'staff': staff,
            'classes': classes,
            'recent_exams': recent_exams
        })
    
    elif hasattr(user, 'guardian'):
        # Guardian dashboard
        guardian = user.guardian
        students = guardian.students.all()
        recent_exams = Exam.objects.filter(class_level__in=students).order_by('-date')[:5]
        
        return render(request, 'dashboard/guardian_dashboard.html', {
            'guardian': guardian,
            'students': students,
            'recent_exams': recent_exams
        })
    
    return redirect('login')

def guardian_dashboard(request):
    if not hasattr(request.user, 'guardian'):
        return redirect('login')
        
    guardian = request.user.guardian
    students = guardian.students.all()
    recent_exams = Exam.objects.filter(class_level__in=students).order_by('-date')[:5]
    
    return render(request, 'dashboard/guardian_dashboard.html', {
        'guardian': guardian,
        'students': students,
        'recent_exams': recent_exams
    })

def register_view(request):
    if request.user.is_authenticated:
        return redirect('schoolmanagement:dashboard')
    
    context = {
        'values': request.POST,
        'role_choices': User.ROLE_CHOICES,
        'genders': [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    }
    
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        gender = request.POST.get('gender', '')
        date_of_birth = request.POST.get('date_of_birth', '')
        address = request.POST.get('address', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        role = request.POST.get('role', 'student')
        
        # Basic validation
        required_fields = [
            ('username', 'Username is required.'),
            ('email', 'Email is required.'),
            ('first_name', 'First name is required.'),
            ('last_name', 'Last name is required.'),
            ('phone', 'Phone number is required.'),
            ('gender', 'Please select your gender.'),
            ('date_of_birth', 'Date of birth is required.'),
            ('address', 'Address is required.'),
            ('password1', 'Password is required.'),
            ('password2', 'Please confirm your password.')
        ]
        
        for field, error_msg in required_fields:
            if not locals().get(field):
                messages.error(request, error_msg)
                return render(request, 'registration/register.html', context)
        
        if password1 != password2:
            messages.error(request, "Passwords don't match.")
            return render(request, 'registration/register.html', context)
            
        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, 'registration/register.html', context)
            
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username is already taken.')
            return render(request, 'registration/register.html', context)
            
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email is already registered.')
            return render(request, 'registration/register.html', context)
            
        if User.objects.filter(phone=phone).exists():
            messages.error(request, 'Phone number is already registered.')
            return render(request, 'registration/register.html', context)
        
        try:
            # Create the user
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                gender=gender,
                date_of_birth=date_of_birth if date_of_birth else None,
                address=address,
                password=password1,
                role=role
            )
            
            # Log the user in
            user = authenticate(username=username, password=password1)
            if user is not None:
                auth_login(request, user)
                messages.success(request, 'Registration successful! Welcome to School Management System.')
                return redirect('schoolmanagement:dashboard')
            
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return render(request, 'registration/register.html', context)
    
    # GET request or form not submitted yet
    return render(request, 'registration/register.html', context)
        
        
        


def login_view(request):
    """
    Custom login view that supports multiple login methods:
    - Username
    - Email
    - Student Admission Number
    - Staff Number
    - Guardian Number
    """
    if request.user.is_authenticated:
        return redirect('schoolmanagement:dashboard')
        
    error_message = None
    if request.method == 'POST':
        try:
            identifier = request.POST.get('username', '').strip()
            password = request.POST.get('password')
            
            if not (identifier and password):
                raise ValidationError('Both username/ID and password are required')
            
            # Authenticate the user using our custom backend
            user = authenticate(request, username=identifier, password=password)
            
            if user is not None:
                auth_login(request, user)
                
                # Set session expiry to 24 hours (optional)
                if not request.POST.get('remember_me'):
                    request.session.set_expiry(60 * 60 * 24)  # 24 hours
                
                # Welcome message with user's full name if available
                welcome_name = user.get_full_name() or user.username
                messages.success(request, f'Welcome back, {welcome_name}!')
                
                # Redirect to next URL if provided, otherwise to dashboard
                next_url = request.GET.get('next', 'schoolmanagement:dashboard')
                return redirect(next_url)
            else:
                raise ValidationError('Invalid login credentials. Please try again.')
                
        except ValidationError as e:
            error_message = str(e)
        except Exception as e:
            error_message = 'An error occurred during login. Please try again.'
            # Log the actual error for debugging
            print(f"Login error: {str(e)}")
            
        if error_message:
            messages.error(request, error_message)
    
    return render(request, 'auth/login.html')



def logout_view(request):
    if request.user.is_authenticated:
        username = request.user.get_full_name() or request.user.username
        auth_logout(request)
        messages.success(request, f'Goodbye, {username}! You have been logged out.')
    return redirect('login')


def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            
            # Generate a random password
            new_password = User.objects.make_random_password()
            
            # Update the user's password
            user.set_password(new_password)
            user.save()
            
            # Send the password reset email
            send_mail(
                'Password Reset',
                f'Your new password is: {new_password}',
                'from@example.com',
                [email],
                fail_silently=False,
            )
            
            messages.success(request, 'Password reset email sent successfully.')
            return redirect('login')
            
        except User.DoesNotExist:
            messages.error(request, 'User with this email does not exist.')
            
    return render(request, 'auth/forgot_password.html')   

def reset_password(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        
        if not password:
            messages.error(request, 'Password is required.')
            return redirect('reset_password')
        
        request.user.set_password(password)
        request.user.save()
        
        messages.success(request, 'Password reset successfully.')
        return redirect('login')
    
    return render(request, 'auth/reset_password.html')

@login_required
def profile_view(request):
    if request.method == 'POST':
        user = request.user
        if 'profile_picture' in request.FILES:
            if hasattr(user, 'student'):
                user.student.profile_picture = request.FILES['profile_picture']
                user.student.save()
            elif hasattr(user, 'staff'):
                user.staff.profile_picture = request.FILES['profile_picture']
                user.staff.save()
        
        messages.success(request, 'Profile updated successfully')
        return redirect('profile')
    
    return render(request, 'profile/profile.html')

@login_required
def student_profile(request):
    student = get_object_or_404(Student, user=request.user)
    guardians = student.guardians.all()
    classes = student.classes.all()
    recent_attendance = Attendance.objects.filter(student=student).order_by('-date')[:5]
    
    return render(request, 'profile/student_profile.html', {
        'student': student,
        'guardians': guardians,
        'classes': classes,
        'recent_attendance': recent_attendance
    })

@login_required
def staff_profile(request):
    staff = get_object_or_404(Staff, user=request.user)
    classes = Class.objects.filter(teachers=staff)
    subjects = Subject.objects.filter(teachers=staff)
    
    return render(request, 'profile/staff_profile.html', {
        'staff': staff,
        'classes': classes,
        'subjects': subjects
    })

def register_student(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    context = {'values': request.POST}
    
    if request.method == 'POST':
        try:
            # Get form data with validation
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            password1 = request.POST.get('password1', '')
            password2 = request.POST.get('password2', '')
            
            # Student specific fields
            student_id = request.POST.get('student_id', '').strip()
            admission_number = request.POST.get('admission_number', '').strip()
            date_of_birth = request.POST.get('date_of_birth')
            gender = request.POST.get('gender', '').strip()
            phone_number = request.POST.get('phone_number', '').strip()
            address = request.POST.get('address', '').strip()
            
            # Validation
            errors = {}
            
            # Required fields
            required_fields = {
                'username': 'Username is required',
                'email': 'Email is required',
                'first_name': 'First name is required',
                'last_name': 'Last name is required',
                'password1': 'Password is required',
                'student_id': 'Student ID is required',
                'admission_number': 'Admission number is required',
                'date_of_birth': 'Date of birth is required',
                'gender': 'Gender is required',
                'phone_number': 'Phone number is required',
            }
            
            for field, error_msg in required_fields.items():
                if not locals().get(field):
                    errors[field] = error_msg
            
            # Password validation
            if password1 and len(password1) < 8:
                errors['password1'] = 'Password must be at least 8 characters long'
            elif password1 and password1 != password2:
                errors['password2'] = "Passwords don't match"
            
            # Email validation
            if email and User.objects.filter(email=email).exists():
                errors['email'] = 'This email is already registered'
                
            # Username validation
            if username and User.objects.filter(username=username).exists():
                errors['username'] = 'This username is already taken'
                
            if errors:
                for field, error in errors.items():
                    messages.error(request, f"{field.title()}: {error}")
                context['errors'] = errors
                return render(request, 'registration/register_student.html', context)
            
            # Create user and student profile in a transaction
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password1,
                    is_active=True  # Set to False if email verification is required
                )
                
                student = Student.objects.create(
                    user=user,
                    student_id=student_id,
                    admission_number=admission_number,
                    date_of_birth=date_of_birth,
                    gender=gender,
                    phone_number=phone_number,
                    address=address
                )
                
                # Add to Student group
                student_group, created = Group.objects.get_or_create(name='Student')
                user.groups.add(student_group)
            user.groups.add(student_group)
            
            messages.success(request, 'Student registered successfully!')
            return redirect('login')
            
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return render(request, 'registration/register_student.html', {
                'values': request.POST
            })
    
    return render(request, 'registration/register_student.html')

def register_staff(request):
    if not request.user.is_staff:
        messages.error(request, 'Only administrators can register new staff members.')
        return redirect('dashboard')
    
    context = {'values': request.POST, 'roles': Staff.ROLE_CHOICES}
    
    if request.method == 'POST':
        try:
            # Get form data with validation
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            password1 = request.POST.get('password1', '')
            password2 = request.POST.get('password2', '')
            
            # Staff specific fields
            staff_id = request.POST.get('staff_id', '').strip()
            role = request.POST.get('role', '').strip()
            gender = request.POST.get('gender', '').strip()
            date_of_birth = request.POST.get('date_of_birth')
            phone = request.POST.get('phone', '').strip()
            address = request.POST.get('address', '').strip()
            
            # Validation
            errors = {}
            
            # Required fields
            required_fields = {
                'username': 'Username is required',
                'email': 'Email is required',
                'first_name': 'First name is required',
                'last_name': 'Last name is required',
                'password1': 'Password is required',
                'staff_id': 'Staff ID is required',
                'role': 'Role is required',
                'gender': 'Gender is required',
                'date_of_birth': 'Date of birth is required',
                'phone': 'Phone number is required',
            }
            
            for field, error_msg in required_fields.items():
                if not locals().get(field):
                    errors[field] = error_msg
            
            # Password validation
            if password1 and len(password1) < 8:
                errors['password1'] = 'Password must be at least 8 characters long'
            elif password1 and password1 != password2:
                errors['password2'] = "Passwords don't match"
            
            # Email validation
            if email and User.objects.filter(email=email).exists():
                errors['email'] = 'This email is already registered'
                
            # Username validation
            if username and User.objects.filter(username=username).exists():
                errors['username'] = 'This username is already taken'
                
            # Staff ID validation
            if staff_id and Staff.objects.filter(staff_id=staff_id).exists():
                errors['staff_id'] = 'This staff ID is already in use'
            
            if errors:
                for field, error in errors.items():
                    messages.error(request, f"{field.title()}: {error}")
                context['errors'] = errors
                return render(request, 'registration/register_staff.html', context)
            
            # Create user and staff profile in a transaction
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password1,
                    is_staff=True,
                    is_active=True
                )
                
                staff = Staff.objects.create(
                    user=user,
                    staff_id=staff_id,
                    role=role,
                    gender=gender,
                    date_of_birth=date_of_birth,
                    phone=phone,
                    address=address
                )
                
                # Add to appropriate group based on role
                group_name = dict(Staff.ROLE_CHOICES).get(role, 'Staff')
                group, created = Group.objects.get_or_create(name=group_name)
                user.groups.add(group)
                
                messages.success(request, f'Staff member {user.get_full_name()} registered successfully!')
                return redirect('staff_list')
                
        except Exception as e:
            messages.error(request, f'Error creating staff member: {str(e)}')
            # Log the actual error for debugging
            print(f"Staff registration error: {str(e)}")
    
    return render(request, 'registration/register_staff.html', context)

@login_required
def add_guardian(request, student_id):
    """View to add a guardian for a student."""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        relationship = request.POST.get('relationship')
        profession = request.POST.get('profession')
        notes = request.POST.get('notes')
        
        # Validate required fields
        if not all([first_name, last_name, email, relationship]):
            messages.error(request, 'Please fill in all required fields')
            return render(request, 'guardian/add_guardian.html', {
                'student': student,
                'form_data': request.POST
            })
            
        # Check if email already exists
        if Guardian.objects.filter(email=email).exists():
            messages.error(request, 'A guardian with this email already exists')
            return render(request, 'guardian/add_guardian.html', {
                'student': student,
                'form_data': request.POST
            })
            
        # Create guardian
        guardian = Guardian.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email.lower(),
            phone=phone,
            address=address,
            relationship=relationship,
            profession=profession,
            notes=notes
        )
        
        # Create user account for guardian
        user = User.objects.create_user(
            username=email.lower(),
            email=email.lower(),
            password=User.objects.make_random_password(),
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role='guardian'
        )
        
        # Link user to guardian
        guardian.user = user
        guardian.save()
        
        # Link guardian to student
        student.guardians.add(guardian)
        
        # Send welcome email with login credentials
        subject = 'Guardian Account Created'
        message = f"""Dear {first_name} {last_name},

Your guardian account has been created for {student.user.get_full_name()}.

Username: {email}
Password: {user.password}

Please login at: {request.build_absolute_uri(reverse('login'))}

Best regards,
School Management Team"""
        
        try:
            user.email_user(subject, message)
            messages.success(request, 'Guardian added successfully. An email with login credentials has been sent.')
        except Exception as e:
            messages.warning(request, 'Guardian added successfully, but email could not be sent.')
            
        return redirect('student_detail', student_id=student_id)
    
    return render(request, 'guardian/add_guardian.html', {
        'student': student
    })

@login_required
def exam_list(request):
    """View to display all exams"""
    exams = Exam.objects.all().order_by('-date')
    return render(request, 'academics/exam_list.html', {'exams': exams})

@login_required
def create_exam(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        exam_type = request.POST.get('exam_type')
        class_level_id = request.POST.get('class_level')
        subject_id = request.POST.get('subject')
        date = request.POST.get('date')
        total_marks = request.POST.get('total_marks')
        description = request.POST.get('description')
        
        if not all([name, exam_type, class_level_id, subject_id, date, total_marks]):
            messages.error(request, 'Please fill in all required fields')
            return redirect('create_exam')
        
        try:
            class_level = Class.objects.get(id=class_level_id)
            subject = Subject.objects.get(id=subject_id)
            
            exam = Exam.objects.create(
                name=name,
                exam_type=exam_type,
                class_level=class_level,
                subject=subject,
                date=date,
                total_marks=total_marks,
                description=description
            )
            
            messages.success(request, 'Exam created successfully')
            return redirect('exam_list')
            
        except (Class.DoesNotExist, Subject.DoesNotExist):
            messages.error(request, 'Invalid class or subject selected')
            return redirect('create_exam')
    
    classes = Class.objects.all()
    subjects = Subject.objects.all()
    return render(request, 'academics/create_exam.html', {
        'classes': classes,
        'subjects': subjects
    })

@login_required
def edit_exam(request, exam_id):
    """View to edit an existing exam"""
    if not request.user.is_staff:
        return redirect('dashboard')
    
    exam = get_object_or_404(Exam, id=exam_id)
    
    if request.method == 'POST':
        exam.name = request.POST.get('name')
        exam.exam_type = request.POST.get('exam_type')
        exam.class_level_id = request.POST.get('class_level')
        exam.subject_id = request.POST.get('subject')
        exam.date = request.POST.get('date')
        exam.total_marks = request.POST.get('total_marks')
        exam.description = request.POST.get('description')
        
        if not all([exam.name, exam.exam_type, exam.class_level_id, exam.subject_id, exam.date, exam.total_marks]):
            messages.error(request, 'Please fill in all required fields')
            return redirect('edit_exam', exam_id=exam_id)
        
        try:
            exam.save()
            messages.success(request, 'Exam updated successfully')
            return redirect('exam_list')
            
        except Exception as e:
            messages.error(request, f'Error updating exam: {str(e)}')
            return redirect('edit_exam', exam_id=exam_id)
    
    classes = Class.objects.all()
    subjects = Subject.objects.all()
    return render(request, 'academics/edit_exam.html', {
        'exam': exam,
        'classes': classes,
        'subjects': subjects
    })

@login_required
def delete_exam(request, exam_id):
    """View to delete an exam"""
    if not request.user.is_staff:
        return redirect('dashboard')
    
    exam = get_object_or_404(Exam, id=exam_id)
    exam.delete()
    messages.success(request, 'Exam deleted successfully')
    return redirect('exam_list')

@login_required
def exam_results(request, exam_id):
    """View to display exam results"""
    exam = get_object_or_404(Exam, id=exam_id)
    
    # Calculate statistics
    total_students = exam.class_level.students.count()
    passed_students = ExamResult.objects.filter(exam=exam, marks_obtained__gte=exam.passing_marks).count()
    
    if total_students > 0:
        average_score = ExamResult.objects.filter(exam=exam).aggregate(Avg('marks_obtained'))['marks_obtained__avg']
        exam.average_score = average_score or 0
        exam.pass_rate = (passed_students / total_students) * 100
    else:
        exam.average_score = 0
        exam.pass_rate = 0
    
    # Get top student
    top_result = ExamResult.objects.filter(exam=exam).order_by('-marks_obtained').first()
    if top_result:
        exam.highest_score = top_result.marks_obtained
        exam.top_student = top_result.student
    
    # Get all results
    exam_results = ExamResult.objects.filter(exam=exam).select_related('student')
    
    return render(request, 'academics/exam_results.html')

def create_fee_structure(request):
    context = {
        'title': 'Create Fee Structure',
        'classes': Class.objects.all().order_by('name'),
        'terms': FeeStructure.TERM_CHOICES,
        'values': request.POST
    }
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.POST.get('name', '').strip()
            class_level_id = request.POST.get('class_level')
            amount = request.POST.get('amount')
            description = request.POST.get('description', '').strip()
            due_date = request.POST.get('due_date')
            term = request.POST.get('term')
            year = request.POST.get('year', timezone.now().year)
            is_active = request.POST.get('is_active', 'false') == 'true'
            
            # Validation
            errors = {}
            
            # Required fields
            required_fields = {
                'name': 'Name is required',
                'class_level': 'Class is required',
                'amount': 'Amount is required',
                'term': 'Term is required',
                'year': 'Year is required',
                'due_date': 'Due date is required',
            }
            
            for field, error_msg in required_fields.items():
                if not locals().get(field):
                    errors[field] = error_msg
            
            # Numeric validation
            try:
                amount = float(amount) if amount else 0
                if amount <= 0:
                    errors['amount'] = 'Amount must be greater than zero'
            except (ValueError, TypeError):
                errors['amount'] = 'Enter a valid amount'
            
            # Date validation
            if due_date:
                try:
                    due_date = timezone.datetime.strptime(due_date, '%Y-%m-%d').date()
                    if due_date < timezone.now().date():
                        errors['due_date'] = 'Due date cannot be in the past'
                except (ValueError, TypeError):
                    errors['due_date'] = 'Enter a valid date (YYYY-MM-DD)'
            
            if errors:
                for field, error in errors.items():
                    messages.error(request, f"{field.title().replace('_', ' ')}: {error}")
                context['errors'] = errors
                return render(request, 'fees/create_fee_structure.html', context)
            
            # Get class level
            try:
                class_level = Class.objects.get(id=class_level_id)
            except (Class.DoesNotExist, ValueError):
                messages.error(request, 'Selected class does not exist')
                return render(request, 'fees/create_fee_structure.html', context)
            
            # Create fee structure
            fee_structure = FeeStructure.objects.create(
                name=name,
                class_level=class_level,
                amount=amount,
                description=description,
                due_date=due_date,
                term=term,
                year=year,
                is_active=is_active,
                created_by=request.user
            )
            
            messages.success(request, f'Fee structure "{name}" created successfully')
            return redirect('fee_structure_list')
            
        except Exception as e:
            messages.error(request, f'Error creating fee structure: {str(e)}')
            # Log the actual error for debugging
            print(f"Create fee structure error: {str(e)}")
    
    return render(request, 'fees/create_fee_structure.html', context)

@login_required
@user_passes_test(lambda u: u.is_staff)
def mark_attendance(request, class_id):
    try:
        class_obj = get_object_or_404(Class, id=class_id)
        students = class_obj.students.all().order_by('user__last_name', 'user__first_name')
        
        # Check if the current user is a teacher assigned to this class
        if hasattr(request.user, 'staff'):
            teacher = request.user.staff
            if not class_obj.teachers.filter(id=teacher.id).exists() and not request.user.is_superuser:
                messages.error(request, 'You are not assigned to this class')
                return redirect('dashboard')
        
        context = {
            'class_obj': class_obj,
            'students': students,
            'today': timezone.now().date(),
            'selected_date': request.GET.get('date', '')
        }
        
        if request.method == 'POST':
            try:
                date_str = request.POST.get('date')
                if not date_str:
                    raise ValidationError('Date is required')
                
                # Parse and validate date
                try:
                    date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
                    if date > timezone.now().date():
                        raise ValidationError('Cannot mark attendance for future dates')
                except (ValueError, TypeError):
                    raise ValidationError('Invalid date format. Use YYYY-MM-DD')
                
                # Check if attendance is already marked for this date and class
                existing_attendance = Attendance.objects.filter(
                    student__classes=class_obj, 
                    date=date
                ).exists()
                
                if existing_attendance and 'confirm' not in request.POST:
                    context['show_confirm'] = True
                    context['selected_date'] = date_str
                    return render(request, 'attendance/mark_attendance.html', context)
                
                attendance_count = 0
                with transaction.atomic():
                    for student in students:
                        status = request.POST.get(f'status_{student.id}') == 'present'
                        remarks = request.POST.get(f'remarks_{student.id}', '').strip()
                        
                        attendance, created = Attendance.objects.update_or_create(
                            student=student,
                            date=date,
                            defaults={
                                'status': status,
                                'recorded_by': request.user,
                                'remarks': remarks if remarks else None
                            }
                        )
                        attendance_count += 1
                
                messages.success(request, f'Attendance recorded for {attendance_count} students')
                return redirect('attendance_summary', class_id=class_id, date=date_str)
                
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Error recording attendance: {str(e)}')
                # Log the actual error for debugging
                print(f"Mark attendance error: {str(e)}")
        
        return render(request, 'attendance/mark_attendance.html', context)
        
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('dashboard')

@login_required
def add_guardian(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    
    # Check permission - only staff or the student's own guardian can add
    if not (request.user.is_staff or 
           (hasattr(request.user, 'guardian') and 
            request.user.guardian.student_set.filter(id=student_id).exists())):
        messages.error(request, 'You do not have permission to add guardians for this student.')
        return redirect('dashboard')
    
    context = {
        'student': student,
        'values': request.POST
    }
    
    if request.method == 'POST':
        try:
            # Get form data
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            relationship = request.POST.get('relationship', '').strip()
            profession = request.POST.get('profession', '').strip()
            address = request.POST.get('address', '').strip()
            
            # Validation
            errors = {}
            required_fields = {
                'first_name': 'First name is required',
                'last_name': 'Last name is required',
                'phone': 'Phone number is required',
                'relationship': 'Relationship to student is required',
            }
            
            for field, error_msg in required_fields.items():
                if not locals().get(field):
                    errors[field] = error_msg
            
            # Email validation if provided
            if email and not '@' in email:
                errors['email'] = 'Enter a valid email address'
                
            # Phone validation (basic check)
            if phone and len(phone) < 8:
                errors['phone'] = 'Enter a valid phone number'
            
            if errors:
                for field, error in errors.items():
                    messages.error(request, f"{field.title().replace('_', ' ')}: {error}")
                context['errors'] = errors
                return render(request, 'students/add_guardian.html', context)
            
            # Create guardian
            guardian = Guardian.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email if email else None,
                phone=phone,
                relationship=relationship,
                profession=profession if profession else None,
                address=address if address else None,
                user=request.user if not request.user.is_staff else None
            )
            
            # Add student to guardian
            guardian.students.add(student)
            
            messages.success(request, f'Successfully added {first_name} {last_name} as a guardian')
            return redirect('student_profile', student_id=student.id)
            
        except Exception as e:
            messages.error(request, f'Error adding guardian: {str(e)}')
            # Log the actual error for debugging
            print(f"Add guardian error: {str(e)}")
    
    return render(request, 'students/add_guardian.html', context)

@login_required
@login_required
def staff_list(request):
    """
    View to list all staff members.
    Accessible by admin users only.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard')
    
    staff_members = Staff.objects.all().order_by('user__last_name', 'user__first_name')
    return render(request, 'staff/staff_list.html', {'staff_members': staff_members})

@login_required
def view_staff(request, staff_id):
    """
    View to display details of a specific staff member.
    Accessible by admin users and the staff member themselves.
    """
    staff = get_object_or_404(Staff, id=staff_id)
    
    # Check if the current user is an admin or the staff member themselves
    if not (request.user.is_staff or request.user == staff.user):
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('dashboard')
    
    return render(request, 'staff/view_staff.html', {'staff_member': staff})

@login_required
def edit_staff(request, staff_id):
    """
    View to edit a staff member's details.
    Accessible by admin users only.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to edit staff details.')
        return redirect('dashboard')
    
    staff = get_object_or_404(Staff, id=staff_id)
    
    if request.method == 'POST':
        form = StaffProfileForm(request.POST, request.FILES, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, 'Staff details updated successfully.')
            return redirect('view_staff', staff_id=staff.id)
    else:
        form = StaffProfileForm(instance=staff)
    
    return render(request, 'staff/edit_staff.html', {'form': form, 'staff': staff})

@login_required
def delete_staff(request, staff_id):
    """
    View to delete a staff member.
    Accessible by admin users only.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to delete staff members.')
        return redirect('dashboard')
    
    staff = get_object_or_404(Staff, id=staff_id)
    
    if request.method == 'POST':
        user = staff.user
        staff.delete()
        user.delete()
        messages.success(request, 'Staff member deleted successfully.')
        return redirect('staff_list')
    
    return render(request, 'staff/delete_staff.html', {'staff': staff})

@login_required
def assign_subjects(request, staff_id):
    """
    View to assign subjects to a staff member.
    Accessible by admin users only.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to assign subjects.')
        return redirect('dashboard')
    
    staff = get_object_or_404(Staff, id=staff_id)
    
    if request.method == 'POST':
        subject_ids = request.POST.getlist('subjects')
        staff.subjects.set(subject_ids)
        messages.success(request, 'Subjects assigned successfully.')
        return redirect('view_staff', staff_id=staff.id)
    
    all_subjects = Subject.objects.all()
    return render(request, 'staff/assign_subjects.html', {
        'staff': staff,
        'all_subjects': all_subjects
    })

@login_required
def assign_classes(request, staff_id):
    """
    View to assign classes to a staff member.
    Accessible by admin users only.
    """
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to assign classes.')
        return redirect('dashboard')
    
    staff = get_object_or_404(Staff, id=staff_id)
    
    if request.method == 'POST':
        class_ids = request.POST.getlist('classes')
        staff.classes.set(class_ids)
        messages.success(request, 'Classes assigned successfully.')
        return redirect('view_staff', staff_id=staff.id)
    
    all_classes = Class.objects.all()
    return render(request, 'staff/assign_classes.html', {
        'staff': staff,
        'all_classes': all_classes
    })

@login_required
def class_detail(request, class_id):
    """
    View to display details of a specific class.
    Accessible by authenticated users.
    """
    class_obj = get_object_or_404(Class, id=class_id)
    students = class_obj.students.all().order_by('user__last_name', 'user__first_name')
    teachers = class_obj.teachers.all()
    
    return render(request, 'academics/class_detail.html', {
        'class': class_obj,
        'students': students,
        'teachers': teachers
    })

@login_required
def attendance_history(request, student_id):
    """
    View to display attendance history for a student.
    Accessible by the student, their guardians, and staff.
    """
    student = get_object_or_404(Student, id=student_id)
    
    # Check permissions
    if not (request.user.is_staff or 
           hasattr(request.user, 'student') and request.user.student.id == student_id or
           hasattr(request.user, 'guardian') and student in request.user.guardian.students.all()):
        messages.error(request, 'You do not have permission to view this attendance history.')
        return redirect('dashboard')
    
    attendance_records = Attendance.objects.filter(student=student).order_by('-date')
    
    return render(request, 'attendance/attendance_history.html', {
        'student': student,
        'attendance_records': attendance_records
    })

@login_required
def fee_payments(request, student_id):
    """
    View to display fee payment history for a student.
    Accessible by the student, their guardians, and staff.
    """
    student = get_object_or_404(Student, id=student_id)
    
    # Check permissions
    if not (request.user.is_staff or 
           hasattr(request.user, 'student') and request.user.student.id == student_id or
           hasattr(request.user, 'guardian') and student in request.user.guardian.students.all()):
        messages.error(request, 'You do not have permission to view this fee payment history.')
        return redirect('dashboard')
    
    fee_payments = FeePayment.objects.filter(student=student).order_by('-payment_date')
    
    return render(request, 'finance/fee_payments.html', {
        'student': student,
        'fee_payments': fee_payments
    })

def student_detail(request, student_id):
    """
    View to display detailed information about a specific student.
    Accessible by staff and the student themselves.
    """
    try:
        student = get_object_or_404(Student, id=student_id)
        
        # Check if the requesting user has permission to view this student
        if not (request.user.is_staff or 
               (hasattr(request.user, 'student') and request.user.student.id == student_id) or
               (hasattr(request.user, 'guardian') and student in request.user.guardian.students.all())):
            messages.error(request, 'You do not have permission to view this student\'s information.')
            return redirect('dashboard')
        
        # Get related data
        classes = student.classes.all()
        guardians = student.guardians.all()
        
        # Get attendance summary
        attendance_summary = {
            'present': Attendance.objects.filter(student=student, status=True).count(),
            'absent': Attendance.objects.filter(student=student, status=False).count(),
            'total': Attendance.objects.filter(student=student).count(),
        }
        
        # Get recent exam results
        recent_results = ExamResult.objects.filter(
            student=student
        ).select_related('exam', 'exam__subject').order_by('-exam__date')[:5]
        
        # Get fee summary
        fee_summary = {
            'total_fees': FeeStructure.objects.filter(
                class_level__in=classes
            ).aggregate(total=Sum('amount'))['total'] or 0,
            'total_paid': FeePayment.objects.filter(
                student=student
            ).aggregate(total=Sum('amount_paid'))['total'] or 0,
            'balance': 0  # This would be calculated based on fees and payments
        }
        fee_summary['balance'] = fee_summary['total_fees'] - fee_summary['total_paid']
        
        context = {
            'student': student,
            'classes': classes,
            'guardians': guardians,
            'attendance_summary': attendance_summary,
            'recent_results': recent_results,
            'fee_summary': fee_summary,
            'is_own_profile': hasattr(request.user, 'student') and request.user.student.id == student_id,
        }
        
        return render(request, 'students/student_detail.html', context)
        
    except Exception as e:
        messages.error(request, f'Error retrieving student information: {str(e)}')
        return redirect('dashboard')
