# database_settings.py

def get_database_settings(tenant_id, password):
    # Replace this logic with your own to determine the database settings dynamically
    # For example, you could fetch the settings from a configuration file, database, or environment variables
    return {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'nurenai', 
        'USER': tenant_id,
        'PASSWORD': password,
        'HOST': '127.0.0.1', 
        'PORT': '5432',
    }
