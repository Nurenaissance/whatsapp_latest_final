from django.db import models

def deduplicate_model(model_class: models.Model, unique_field: str):
    from django.db.models import Count
    
    duplicates = model_class.objects.values(unique_field).annotate(count=Count('id')).filter(count__gt=1)

    for duplicate in duplicates:
        objs = model_class.objects.filter(**{unique_field: duplicate[unique_field]})
        objs_to_delete = objs[1:]
        for obj in objs_to_delete:
            obj.delete()
