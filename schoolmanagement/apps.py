from django.apps import AppConfig

class SchoolmanagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'schoolmanagement'
    
    def ready(self):
        import schoolmanagement.signals
