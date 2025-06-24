from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Sum
from .models import Student, Staff, FeePayment, Exam, FeeStructure, Class, Guardian


def login_view(request):
    if request.user.is_authenticated:
        return redirect('schoolmanagement:dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'schoolmanagement:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'auth/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('schoolmanagement:login')


@login_required
def dashboard(request):
    user = request.user
    
    # Check user role and redirect to appropriate dashboard
    if user.is_staff:
        # Admin dashboard
        total_students = Student.objects.count()
        total_staff = Staff.objects.count()
        pending_fees = FeePayment.objects.filter(payment_date__isnull=True).count()
        recent_exams = Exam.objects.order_by('-date')[:5]
        
        context = {
            'total_students': total_students,
            'total_staff': total_staff,
            'pending_fees': pending_fees,
            'recent_exams': recent_exams
        }
        return render(request, 'dashboard/admin_dashboard.html', context)
    
    elif hasattr(user, 'student'):
        # Student dashboard
        student = user.student
        classes = student.classes.all()
        recent_exams = Exam.objects.filter(class_level__in=classes).order_by('-date')[:5]
        upcoming_fees = FeeStructure.objects.filter(
            class_level__in=classes,
            due_date__gte=timezone.now().date()
        ).order_by('due_date')
        
        context = {
            'student': student,
            'classes': classes,
            'recent_exams': recent_exams,
            'upcoming_fees': upcoming_fees
        }
        return render(request, 'dashboard/student_dashboard.html', context)
    
    elif hasattr(user, 'staff'):
        # Staff/Teacher dashboard
        staff = user.staff
        classes_taught = Class.objects.filter(teachers=staff)
        recent_exams = Exam.objects.filter(
            class_level__in=classes_taught,
            date__gte=timezone.now().date()
        ).order_by('date')[:5]
        
        context = {
            'staff': staff,
            'classes_taught': classes_taught,
            'recent_exams': recent_exams
        }
        return render(request, 'dashboard/teacher_dashboard.html', context)
    
    elif hasattr(user, 'guardian'):
        # Guardian dashboard
        guardian = user.guardian
        students = guardian.students.all()
        recent_exams = Exam.objects.filter(
            class_level__in=students.values('class_level')
        ).order_by('-date')[:5]
        
        context = {
            'guardian': guardian,
            'students': students,
            'recent_exams': recent_exams
        }
        return render(request, 'dashboard/guardian_dashboard.html', context)
    
    # If user has no recognized role
    messages.error(request, 'Your account type is not supported. Please contact the administrator.')
    return redirect('schoolmanagement:login')
