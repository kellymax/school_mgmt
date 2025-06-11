from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import Student, Guardian, Attendance, ExamResult, FeePayment
from .decorators import guardian_required, role_required

@login_required
def guardian_dashboard(request):
    """
    Dashboard view for guardians to see their students' information.
    """
    if not hasattr(request.user, 'guardian_profile'):
        messages.error(request, "You don't have guardian permissions.")
        return redirect('dashboard')
    
    guardian = request.user.guardian_profile
    students = guardian.get_associated_students()
    
    # Get recent attendance for all students
    recent_attendance = Attendance.objects.filter(
        student__in=students
    ).select_related('student').order_by('-date')[:10]
    
    # Get upcoming exams for all students
    upcoming_exams = ExamResult.objects.filter(
        student__in=students,
        exam__date__gte=timezone.now().date()
    ).select_related('exam', 'student').order_by('exam__date')[:5]
    
    # Get fee dues
    fee_dues = FeePayment.objects.filter(
        student__in=students,
        status__in=['pending', 'partial']
    ).select_related('student', 'fee_structure').order_by('due_date')[:5]
    
    context = {
        'guardian': guardian,
        'students': students,
        'recent_attendance': recent_attendance,
        'upcoming_exams': upcoming_exams,
        'fee_dues': fee_dues,
    }
    
    return render(request, 'guardian/dashboard.html', context)

@login_required
@guardian_required
def student_detail(request, student_id):
    """
    View to show detailed information about a student that the guardian is responsible for.
    """
    student = get_object_or_404(Student, id=student_id)
    guardian = request.user.guardian_profile
    
    # Verify that the guardian has access to this student
    if not guardian.students.filter(id=student_id).exists():
        messages.error(request, "You don't have permission to view this student's information.")
        return redirect('guardian_dashboard')
    
    # Get attendance summary
    attendance_summary = {
        'present': Attendance.objects.filter(
            student=student, 
            status='present'
        ).count(),
        'absent': Attendance.objects.filter(
            student=student, 
            status='absent'
        ).count(),
        'late': Attendance.objects.filter(
            student=student, 
            status='late'
        ).count(),
        'total': Attendance.objects.filter(
            student=student
        ).count(),
    }
    
    # Get recent exam results
    recent_results = ExamResult.objects.filter(
        student=student
    ).select_related('exam', 'exam__subject').order_by('-exam__date')[:5]
    
    # Get fee payment history
    fee_payments = FeePayment.objects.filter(
        student=student
    ).select_related('fee_structure').order_by('-payment_date')[:10]
    
    # Get class schedule
    current_class = student.current_class
    if current_class:
        schedule = current_class.timetable_set.all().order_by('day', 'start_time')
    else:
        schedule = []
    
    context = {
        'student': student,
        'guardian': guardian,
        'attendance_summary': attendance_summary,
        'recent_results': recent_results,
        'fee_payments': fee_payments,
        'schedule': schedule,
        'current_class': current_class
    }
    
    return render(request, 'guardian/student_detail.html', context)

@login_required
@guardian_required
def attendance_history(request, student_id):
    """
    View to show attendance history for a student.
    """
    student = get_object_or_404(Student, id=student_id)
    guardian = request.user.guardian_profile
    
    # Verify that the guardian has access to this student
    if not guardian.students.filter(id=student_id).exists():
        messages.error(request, "You don't have permission to view this student's attendance.")
        return redirect('guardian_dashboard')
    
    # Get all attendance records for the student
    attendance_records = Attendance.objects.filter(
        student=student
    ).select_related('recorded_by').order_by('-date')
    
    # Apply filters if provided
    month = request.GET.get('month')
    status = request.GET.get('status')
    
    if month:
        attendance_records = attendance_records.filter(date__month=month)
    if status:
        attendance_records = attendance_records.filter(status=status)
    
    # Calculate attendance statistics
    total_days = attendance_records.count()
    present_days = attendance_records.filter(status='present').count()
    absent_days = attendance_records.filter(status='absent').count()
    late_days = attendance_records.filter(status='late').count()
    excused_days = attendance_records.filter(status='excused').count()
    
    # Calculate attendance percentage
    attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
    
    # Pagination
    paginator = Paginator(attendance_records, 20)  # Show 20 records per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'student': student,
        'page_obj': page_obj,
        'selected_month': month,
        'selected_status': status,
        'attendance_stats': {
            'total': total_days,
            'present': present_days,
            'absent': absent_days,
            'late': late_days,
            'excused': excused_days,
            'percentage': attendance_percentage
        }
    }
    
    return render(request, 'guardian/attendance_history.html', context)

@login_required
@guardian_required
def exam_results(request, student_id):
    """
    View to show exam results for a student.
    """
    student = get_object_or_404(Student, id=student_id)
    guardian = request.user.guardian_profile
    
    # Verify that the guardian has access to this student
    if not guardian.students.filter(id=student_id).exists():
        messages.error(request, "You don't have permission to view this student's exam results.")
        return redirect('guardian_dashboard')
    
    # Get all exam results for the student
    exam_results = ExamResult.objects.filter(
        student=student
    ).select_related('exam', 'exam__subject').order_by('-exam__date')
    
    # Apply filters if provided
    subject = request.GET.get('subject')
    exam_type = request.GET.get('exam_type')
    
    if subject:
        exam_results = exam_results.filter(exam__subject__id=subject)
    if exam_type:
        exam_results = exam_results.filter(exam__exam_type=exam_type)
    
    # Calculate performance metrics
    total_exams = exam_results.count()
    total_marks = sum(result.marks_obtained for result in exam_results)
    total_max_marks = sum(result.exam.max_marks for result in exam_results)
    
    # Calculate average score
    avg_score = (total_marks / total_max_marks * 100) if total_max_marks > 0 else 0
    
    # Calculate grade distribution
    grade_counts = {
        'A': exam_results.filter(grade='A').count(),
        'B': exam_results.filter(grade='B').count(),
        'C': exam_results.filter(grade='C').count(),
        'D': exam_results.filter(grade='D').count(),
        'E': exam_results.filter(grade='E').count(),
        'F': exam_results.filter(grade='F').count()
    }
    
    # Get distinct subjects for filter
    subjects = Subject.objects.filter(
        exam__examresult__in=exam_results
    ).distinct()
    
    # Pagination
    paginator = Paginator(exam_results, 10)  # Show 10 records per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'student': student,
        'page_obj': page_obj,
        'subjects': subjects,
        'selected_subject': subject,
        'selected_exam_type': exam_type,
        'performance': {
            'total_exams': total_exams,
            'avg_score': avg_score,
            'grade_counts': grade_counts
        }
    }
    
    return render(request, 'guardian/exam_results.html', context)
