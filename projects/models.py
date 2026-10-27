from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

class Demand(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('canceled', 'Canceled'),
        ('paid', 'Paid / Ongoing'),
        ('completed', 'Completed'),
    )

    # receiver field is a ForeignKey to the custom User model defined in accounts/models.py
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='demands'
    )
    zilla = models.CharField(max_length=100)
    upozilla = models.CharField(max_length=100)
    detail_location = models.CharField(max_length=255)
    demand_name = models.CharField(max_length=200)
    problem_detail = models.TextField()
    contact_no = models.CharField(max_length=15)

    requested_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('1000.00'))]
    )
    donor_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    collected_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    problem_image = models.ImageField(upload_to='demands/images/', null=True, blank=True)
    supporting_document = models.FileField(upload_to='demands/docs/', null=True, blank=True)

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # adding 10% extra to the requested amount for platform fees and other overheads
        if self.requested_amount:
            self.donor_amount = (self.requested_amount * Decimal('1.10')).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)

    @property
    def remaining_amount(self):
        return max(Decimal('0.00'), self.donor_amount - self.collected_amount)

    @property
    def funding_percentage(self):
        if self.donor_amount > 0:
            pct = (self.collected_amount / self.donor_amount) * 100
            return min(100, int(pct))
        return 0

    def __str__(self):
        return f"{self.demand_name} ({self.upozilla}, {self.zilla})"


class ProjectProgress(models.Model):
    MILESTONE_CHOICES = (
        (0, 'Not Started (0%)'),
        (25, 'Started (25%)'),
        (50, 'Halfway (50%)'),
        (75, 'Almost Done (75%)'),
        (100, 'Completed (100%)'),
    )

    demand = models.OneToOneField(
        Demand,
        on_delete=models.CASCADE,
        related_name='progress'
    )
    progress_percent = models.PositiveSmallIntegerField(choices=MILESTONE_CHOICES, default=0)


    proof_image = models.ImageField(upload_to='progress/proofs/', null=True, blank=True)
    update_note = models.TextField(blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.pk:
            old = ProjectProgress.objects.get(pk=self.pk)
            if old.progress_percent == 100 and self.progress_percent < 100:
                raise ValidationError("you cannot reduce the progress of a completed project.")
            if self.progress_percent < old.progress_percent:
                raise ValidationError("you cannot reduce the progress percentage of a project.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        if self.progress_percent == 100 and self.demand.status != 'completed':
            self.demand.status = 'completed'
            self.demand.save(update_fields=['status'])

    def __str__(self):
        return f"{self.demand.demand_name} - {self.progress_percent}%"