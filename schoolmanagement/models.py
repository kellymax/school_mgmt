from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, Group, Permission
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class CustomUserManager(BaseUserManager):
    """Custom user model manager where email is the unique identifier."""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    """Custom user model with role-based access control."""
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('guardian', 'Guardian'),
        ('accountant', 'Accountant'),
        ('librarian', 'Librarian'),
        ('other', 'Other Staff'),
    ]
    
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    phone = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    objects = CustomUserManager()
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.username
    
    def has_role(self, role):
        """Check if user has the specified role."""
        return self.role == role
    
    def is_admin(self):
        return self.role == 'admin' or self.is_superuser
    
    def is_teacher(self):
        return self.role == 'teacher' or self.is_admin()
    
    def is_student(self):
        return self.role == 'student'
    
    def is_guardian(self):
        return self.role == 'guardian'
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

class Staff(models.Model):
    ROLE_CHOICES = [
        ('teacher', 'Teacher'),
        ('admin', 'Administrator'),
        ('accountant', 'Accountant'),
        ('librarian', 'Librarian'),
        ('other', 'Other Staff'),
    ]
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    staff_id = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='teacher')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='staff/profile_pics/', null=True, blank=True)
    date_joined = models.DateField(default=timezone.now)
    
    # Relationships
    subjects = models.ManyToManyField('Subject', related_name='teachers', blank=True)
    classes = models.ManyToManyField('Class', related_name='teachers', blank=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_role_display()})"
    
    class Meta:
        verbose_name_plural = 'Staff'
        ordering = ['user__last_name', 'user__first_name']

class Subject(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    class Meta:
        ordering = ['name']

class Class(models.Model):
    name = models.CharField(max_length=100)
    stream = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Relationships
    students = models.ManyToManyField('Student', through='StudentClass', related_name='enrolled_classes', blank=True)
    teaching_staff = models.ManyToManyField('Staff', through='ClassSubject', related_name='teaching_in_classes', blank=True)
    subjects = models.ManyToManyField(Subject, through='ClassSubject', related_name='classes', blank=True)
    
    class Meta:
        verbose_name_plural = 'Classes'
        ordering = ['name']
        
    def __str__(self):
        return f"{self.name} ({self.stream})" if self.stream else self.name
        
    def get_student_count(self):
        return self.students.count()
        
    def get_teacher_count(self):
        return self.teachers.count()
        
    def get_subject_count(self):
        return self.subjects.count()



class Timetable(models.Model):
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
    ]
    
    PERIOD_CHOICES = [
        ('1', '1st Period'),
        ('2', '2nd Period'),
        ('3', '3rd Period'),
        ('4', '4th Period'),
        ('5', '5th Period'),
        ('6', '6th Period'),
        ('7', '7th Period'),
        ('8', '8th Period'),
    ]
    
    class_level = models.ForeignKey('Class', on_delete=models.CASCADE, related_name='timetable')
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    teacher = models.ForeignKey('Staff', on_delete=models.CASCADE)
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    period = models.CharField(max_length=2, choices=PERIOD_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('class_level', 'day', 'period')
        ordering = ['day', 'period']
        verbose_name = 'Timetable Entry'
        verbose_name_plural = 'Timetable'
    
    def __str__(self):
        return f"{self.class_level} - {self.subject} ({self.get_day_display()}) {self.start_time} - {self.end_time}"
    
    def clean(self):
        """Ensure that start_time is before end_time."""
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError('Start time must be before end time')
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Guardian(models.Model):
    RELATIONSHIP_CHOICES = [
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('brother', 'Brother'),
        ('sister', 'Sister'),
        ('grandfather', 'Grandfather'),
        ('grandmother', 'Grandmother'),
        ('uncle', 'Uncle'),
        ('aunt', 'Aunt'),
        ('other', 'Other'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, 
                              related_name='guardian_profile')
    guardian_number = models.CharField(max_length=20, unique=True, blank=True, null=True, 
                                     help_text="Auto-generated guardian number")
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES, default='other')
    profession = models.CharField(max_length=100, blank=True)
    is_primary = models.BooleanField(default=False, help_text='Primary guardian for communication')
    can_pickup = models.BooleanField(default=True, help_text='Authorized to pick up the student')
    can_view_reports = models.BooleanField(default=True, help_text='Can view student reports')
    can_authorize = models.BooleanField(default=False, help_text='Can authorize school trips and activities')
    notes = models.TextField(blank=True, help_text='Additional notes about the guardian')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_relationship_display()})"
    
    def save(self, *args, **kwargs):
        # If this is a new guardian and no user is linked, create a user
        if not self.pk and not self.user_id:
            from django.contrib.auth import get_user_model
            from .utils import generate_guardian_number
            
            User = get_user_model()
            
            # Generate a username based on email or name
            username = self.email.split('@')[0]
            base_username = username
            counter = 1
            
            # Ensure username is unique
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Generate a random password
            password = User.objects.make_random_password()
            
            # Create a new user
            user = User.objects.create_user(
                username=username,
                email=self.email,
                password=password,
                first_name=self.first_name,
                last_name=self.last_name,
                role='guardian',
                phone=self.phone
            )
            self.user = user
            
            # Generate guardian number if not provided
            if not self.guardian_number:
                self.guardian_number = generate_guardian_number()
        
        super().save(*args, **kwargs)
    
    def get_associated_students(self):
        """Return a queryset of all students associated with this guardian."""
        return self.students.all()
    
    def get_primary_phone(self):
        """Return the primary phone number (user's phone or guardian's phone)."""
        return self.user.phone if self.user and self.user.phone else self.phone
    
    def get_primary_email(self):
        """Return the primary email address (user's email or guardian's email)."""
        return self.user.email if self.user and self.user.email else self.email
    
    @classmethod
    def get_guardian_by_user(cls, user):
        """Get guardian profile for a User instance."""
        try:
            return cls.objects.get(user=user)
        except cls.DoesNotExist:
            return None
    
    class Meta:
        ordering = ['-is_primary', 'last_name', 'first_name']
        verbose_name = 'Guardian'
        verbose_name_plural = 'Guardians'

class Student(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)
    admission_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    admission_date = models.DateField(default=timezone.now)
    profile_picture = models.ImageField(upload_to='students/profile_pics/', null=True, blank=True)
    current_class = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, blank=True, related_name='current_students')
    guardians = models.ManyToManyField(Guardian, related_name='students', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['user__last_name', 'user__first_name']
        
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.student_id})"
        
    def get_full_name(self):
        return self.user.get_full_name()
        
    def get_email(self):
        return self.user.email
        
    def get_phone(self):
        return self.user.phone
        
    def get_age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None
        
    def get_current_class(self):
        return self.current_class.name if self.current_class else 'Not assigned'
        
    def get_guardians(self):
        return self.guardians.all()
        
    def get_primary_guardian(self):
        return self.guardians.filter(is_primary=True).first()
        
    def has_guardian_permission(self, user):
        """Check if the given user is a guardian of this student."""
        return self.guardians.filter(user=user).exists()

class StudentClass(models.Model):
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    class_level = models.ForeignKey('Class', on_delete=models.CASCADE)
    admission_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('student', 'class_level')
        ordering = ['-admission_date']
        
    def __str__(self):
        return f"{self.student} - {self.class_level}"

class ClassSubject(models.Model):
    class_level = models.ForeignKey('Class', on_delete=models.CASCADE)
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    teacher = models.ForeignKey('Staff', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('class_level', 'subject')

class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    enrollment_date = models.DateField(auto_now_add=True)
    
    class Meta:
        unique_together = ('student',)
    
    def __str__(self):
        return f"{self.student}"

class Grade(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    grade = models.DecimalField(max_digits=5, decimal_places=2)
    semester = models.CharField(max_length=20)
    year = models.IntegerField()
    
    def __str__(self):
        return f"{self.enrollment.student} - {self.enrollment.course} ({self.grade})"



class Exam(models.Model):
    EXAM_TYPES = [
        ('quiz', 'Quiz'),
        ('midterm', 'Midterm Exam'),
        ('final', 'Final Exam'),
        ('test', 'Test'),
        ('assignment', 'Assignment'),
    ]
    
    name = models.CharField(max_length=200)
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPES, default='quiz')
    class_level = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='exams')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exams')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    total_marks = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    passing_marks = models.DecimalField(max_digits=5, decimal_places=2, default=40.00)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.class_level} - {self.subject}"
    
    class Meta:
        ordering = ['-date', 'start_time']


class ExamResult(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exam_results')
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=2, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Calculate grade based on marks obtained
        percentage = (self.marks_obtained / self.exam.total_marks) * 100
        
        if percentage >= 90:
            self.grade = 'A+'
        elif percentage >= 80:
            self.grade = 'A'
        elif percentage >= 70:
            self.grade = 'B+'
        elif percentage >= 60:
            self.grade = 'B'
        elif percentage >= 50:
            self.grade = 'C+'
        elif percentage >= 40:
            self.grade = 'C'
        else:
            self.grade = 'F'
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.student} - {self.exam}: {self.marks_obtained}/{self.exam.total_marks} ({self.grade})"
    
    class Meta:
        unique_together = ('exam', 'student')
        ordering = ['-exam__date', 'student__user__last_name']

class FeeStructure(models.Model):
    TERM_CHOICES = [
        (1, 'Term 1'),
        (2, 'Term 2'),
        (3, 'Term 3'),
    ]
    
    name = models.CharField(max_length=100)
    class_level = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='fee_structures')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    term = models.PositiveSmallIntegerField(choices=TERM_CHOICES)
    year = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.class_level} - ${self.amount} (Term {self.term}, {self.year})"
    
    class Meta:
        ordering = ['-year', 'term', 'class_level__name']


class FeePayment(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('other', 'Other'),
    ]
    
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_payments')
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    receipt_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_payments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        # Generate receipt number if not provided
        if not self.receipt_number:
            self.receipt_number = f"RCPT-{self.id:06d}" if self.id else None
        
        # Update payment status based on amount paid
        if self.amount_paid >= self.fee_structure.amount:
            self.status = 'paid'
        elif self.amount_paid > 0:
            self.status = 'partial'
        else:
            self.status = 'pending'
            
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.student} - {self.fee_structure}: ${self.amount_paid}"
    
    class Meta:
        ordering = ['-payment_date', 'student__user__last_name']


class Attendance(models.Model):
    ATTENDANCE_STATUS = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    class_level = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS, default='present')
    remarks = models.TextField(blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recorded_attendances')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.student} - {self.class_level} - {self.date}: {self.get_status_display()}"
    
    class Meta:
        verbose_name_plural = 'Attendance'
        unique_together = ('student', 'class_level', 'date')
        ordering = ['-date', 'student__user__last_name']

class FeeDiscount(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    
    def __str__(self):
        return f"{self.student} - {self.amount}"

class FeeFine(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    due_date = models.DateField()
    created_date = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.student} - {self.amount}"
