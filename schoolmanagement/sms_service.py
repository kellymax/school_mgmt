import os
from django.conf import settings

# Check if Twilio is installed
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

class SMSService:
    def __init__(self):
        self.twilio_available = TWILIO_AVAILABLE
        self.client = None
        self.from_number = None
        
        if self.twilio_available and hasattr(settings, 'TWILIO_ACCOUNT_SID') and hasattr(settings, 'TWILIO_AUTH_TOKEN'):
            try:
                self.client = Client(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN
                )
                self.from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
            except Exception as e:
                print(f"Error initializing Twilio client: {e}")
                self.twilio_available = False

    def send_sms(self, to_number, message):
        if not self.twilio_available or not self.client or not self.from_number:
            print(f"SMS not sent (Twilio not configured): {to_number} - {message}")
            return None
            
        try:
            message = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )
            return message.sid
        except Exception as e:
            raise Exception(f"Failed to send SMS: {str(e)}")

    def send_fee_reminder(self, student, amount_due):
        message = f"Dear parent of {student.user.first_name} {student.user.last_name},\n" \
                 f"Please note that there is an outstanding fee of KES {amount_due} due for your child.\n" \
                 f"Please make the payment at your earliest convenience."
        
        for guardian in student.guardians.all():
            self.send_sms(guardian.phone_number, message)

    def send_absence_alert(self, student, date, remarks):
        message = f"Dear parent of {student.user.first_name} {student.user.last_name},\n" \
                 f"Your child was absent from school on {date}.\n" \
                 f"Remarks: {remarks if remarks else 'No remarks'}"
        
        for guardian in student.guardians.all():
            self.send_sms(guardian.phone_number, message)

    def send_exam_results(self, student, exam, marks):
        message = f"Dear parent of {student.user.first_name} {student.user.last_name},\n" \
                 f"Your child's exam results for {exam.name} in {exam.subject.name}: {marks} marks."
        
        for guardian in student.guardians.all():
            self.send_sms(guardian.phone_number, message)

# Initialize the SMS service
sms_service = SMSService()
