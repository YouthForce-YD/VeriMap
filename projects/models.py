from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models

def validate_max_file_size(file):
    max_size = 5 * 1024 * 1024
    if file and hasattr(file, 'size') and file.size and file.size > max_size:
        raise ValidationError('File size must not exceed 5MB.')

validate_image_extension = FileExtensionValidator(
    allowed_extensions=['jpg', 'jpeg', 'png', 'webp']
)

validate_document_extension = FileExtensionValidator(
    allowed_extensions=['pdf', 'jpg', 'jpeg', 'png']
)

class Demand(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('canceled', 'Canceled'),
        ('paid', 'Paid / Ongoing'),
        ('completed', 'Completed'),
    )

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
        validators=[
            MinValueValidator(Decimal('1000.00')),
            MaxValueValidator(Decimal('50000000.00'))
        ]
    )
    donor_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    collected_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    problem_image = models.ImageField(
        upload_to='demands/images/',
        null=True,
        blank=True,
        validators=[validate_image_extension, validate_max_file_size]
    )
    supporting_document = models.FileField(
        upload_to='demands/docs/',
        null=True,
        blank=True,
        validators=[validate_document_extension, validate_max_file_size]
    )

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        if self.requested_amount is not None:
            self.requested_amount = Decimal(str(self.requested_amount)).quantize(Decimal('0.01'))
            if self.requested_amount < Decimal('1000.00') or self.requested_amount > Decimal('50000000.00'):
                raise ValidationError({'requested_amount': 'Requested amount must be between 1000.00 and 50000000.00.'})
            self.donor_amount = (self.requested_amount * Decimal('1.10')).quantize(Decimal('0.01'))
        if self.collected_amount is not None:
            self.collected_amount = Decimal(str(self.collected_amount)).quantize(Decimal('0.01'))
        if self.problem_image:
            validate_image_extension(self.problem_image)
            validate_max_file_size(self.problem_image)
        if self.supporting_document:
            validate_document_extension(self.supporting_document)
            validate_max_file_size(self.supporting_document)

    def save(self, *args, **kwargs):
        if self.requested_amount is not None:
            self.requested_amount = Decimal(str(self.requested_amount)).quantize(Decimal('0.01'))
            self.donor_amount = (self.requested_amount * Decimal('1.10')).quantize(Decimal('0.01'))
        if self.collected_amount is not None:
            self.collected_amount = Decimal(str(self.collected_amount)).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)

    @property
    def remaining_amount(self):
        return max(Decimal('0.00'), (self.donor_amount - self.collected_amount).quantize(Decimal('0.01')))

    @property
    def funding_percentage(self):
        if self.donor_amount > Decimal('0.00'):
            pct = (self.collected_amount / self.donor_amount) * Decimal('100')
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
    proof_image = models.ImageField(
        upload_to='progress/proofs/',
        null=True,
        blank=True,
        validators=[validate_image_extension, validate_max_file_size]
    )
    update_note = models.TextField(blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        old_progress = None
        if self.pk:
            old = ProjectProgress.objects.filter(pk=self.pk).values('progress_percent').first()
            if old:
                old_progress = old['progress_percent']
        elif self.demand_id:
            old = ProjectProgress.objects.filter(demand_id=self.demand_id).values('progress_percent').first()
            if old:
                old_progress = old['progress_percent']

        if old_progress is not None:
            if old_progress == 100 and self.progress_percent < 100:
                raise ValidationError('Cannot revert a 100% completed project.')
            if self.progress_percent < old_progress:
                raise ValidationError('Progress percentage cannot be reduced below its existing value.')

        if self.demand_id:
            demand_status = Demand.objects.filter(pk=self.demand_id).values_list('status', flat=True).first()
            if demand_status == 'completed' and self.progress_percent < 100:
                raise ValidationError('Cannot revert a 100% completed project.')

        if self.proof_image:
            validate_image_extension(self.proof_image)
            validate_max_file_size(self.proof_image)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        if self.progress_percent == 100 and self.demand.status != 'completed':
            self.demand.status = 'completed'
            self.demand.save(update_fields=['status'])

    def __str__(self):
        return f"{self.demand.demand_name} - {self.progress_percent}%"
