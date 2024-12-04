from django.apps import AppConfig

class CommunicationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'  # Optional: specify the type of auto-incrementing primary key
    name = 'communication'  # The name of your app