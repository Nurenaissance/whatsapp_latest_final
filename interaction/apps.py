from django.apps import AppConfig


class InteractionConfig(AppConfig):
    name = 'interaction'

class callsConfig(AppConfig):
    name = 'calls'

class meetingsConfig(AppConfig):
    name = 'meetings'
    
class WhatsappChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'whatsapp_chat'
