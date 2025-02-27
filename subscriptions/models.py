from django.db import models

class Subscription2(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    tenant = models.CharField(max_length=10)
    past_payments = models.JSONField(null=True, blank=True)
    created_at =models.DateTimeField(auto_now_add=True)
    payment_url = models.URLField(null=True, blank=True)


class Subscription(models.Model):
    STATUS_CHOICES = [
        ("created", "Created"),
        ("authenticated", "Authenticated"),
        ("active", "Active"),
        ("pending", "Pending"),
        ("halted", "Halted"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]

    id = models.CharField(primary_key=True, max_length=50)
    plan_id = models.CharField(max_length=50) #convert to foreign key after creating plan model
    plan_name = models.CharField(max_length=50)
    status = models.CharField(choices=STATUS_CHOICES, max_length=20, default="created")

    current_start = models.DateTimeField(null=True, blank=True)
    current_end = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    notes = models.JSONField(max_length=15, null=True, blank=True)

    charge_at = models.DateTimeField(null=True, blank=True)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)

    total_count = models.IntegerField(default=1)
    paid_count = models.IntegerField(default=0)
    remaining_count = models.IntegerField()

    customer_notify = models.BooleanField(default=True)
    created_at = models.BigIntegerField()
    expire_by = models.DateTimeField(null=True, blank=True)

    short_url = models.URLField(max_length=255, null=True, blank=True)

    has_scheduled_changes = models.BooleanField(default=False)
    change_scheduled_at = models.DateTimeField(null=True, blank=True)

    source = models.CharField(max_length=20, default="api")
    offer_id = models.CharField(max_length=50, null=True, blank=True)
    tenant = models.CharField(max_length=20, null=True, blank=True)
    past_payments = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"Subscription {self.id} - {self.status}"

class Plan(models.Model):
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly')
    ]
    id = models.CharField(primary_key=True, max_length=50)
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    interval = models.IntegerField()
    active = models.BooleanField(default=True)
    name = models.CharField(max_length=20)
    description = models.CharField(max_length=200, null=True, blank=True)
    amount = models.IntegerField()
    currency = models.CharField(max_length=5)
    created_at = models.DateTimeField()
    features = models.JSONField(null=True, blank=True)
