# core/models.py
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
import uuid

# -------------------------
# Utility / choices
# -------------------------
class VisitPurpose(models.TextChoices):
    CHECKUP = "checkup", "Check-up"
    DELIVERY = "delivery", "Delivery"
    PROMO = "promo", "Promotion"

class PaymentMethod(models.TextChoices):
    CASH = "cash", "Cash"
    CREDIT = "credit", "Credit"
    MPESA = "mpesa", "M-Pesa"
    CARD = "card", "Card"

class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"

class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    AGENT = "agent", "Agent"
    MANAGER = "manager", "Manager"

class MovementType(models.TextChoices):
    ALLOCATION = "allocation", "Allocation"
    TRANSFER = "transfer", "Transfer"
    SALE = "sale", "Sale"
    RETURN = "return", "Return"
    ADJUSTMENT = "adjustment", "Adjustment"

class CampaignType(models.TextChoices):
    PROMO = "promo", "Promotion"
    SAMPLING = "sampling", "Sampling"
    DISCOUNT = "discount", "Discount"
    EVENT = "event", "Event"

class CampaignStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"

class TransferStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    COMPLETED = "completed", "Completed"

class ReturnStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RECEIVED = "received", "Received"
    REJECTED = "rejected", "Rejected"

class PriceListStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"

# -------------------------
# Abstracts
# -------------------------
class TimeStampedModel(models.Model):
    """Abstract base with created/updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True



class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=32, blank=True, null=True)
    phone_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.AGENT)
    region = models.CharField(max_length=128, blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    is_soft_deleted = models.BooleanField(default=False)
    manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team",
        limit_choices_to={"role": Role.MANAGER},
    )
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.username} ({self.role})"

# -------------------------
# Products, Packs, Pricing
# -------------------------
class Product(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sku = models.CharField(max_length=128, unique=True, blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.category})"

class PackSize(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=50)  # "50g"
    sku = models.CharField(max_length=128, unique=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="packs")
    unit = models.CharField(max_length=32, default="g")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = (("product", "label"),)
        ordering = ["product__name", "label"]

    def __str__(self):
        return f"{self.product.name} — {self.label}"

class PriceList(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pack = models.ForeignKey(PackSize, on_delete=models.PROTECT, related_name="prices")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_policy = models.JSONField(blank=True, null=True)
    effective_from = models.DateField()
    effective_to = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=16, choices=PriceListStatus.choices, default=PriceListStatus.ACTIVE)

    class Meta:
        ordering = ["-effective_from"]
        indexes = [models.Index(fields=["pack", "effective_from", "effective_to"])]

    def __str__(self):
        return f"Price[{self.pack}] {self.unit_price} ({self.effective_from} → {self.effective_to})"

# -------------------------
# Market & Outlets
# -------------------------
class Market(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    region = models.CharField(max_length=128)
    gps_lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    gps_long = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    status = models.BooleanField(default=True)

    class Meta:
        unique_together = (("name", "region"),)
        ordering = ["region", "name"]

    def __str__(self):
        return f"{self.name} — {self.region}"

class Outlet(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name="outlets")
    name = models.CharField(max_length=200)
    descriptor = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = (("market", "name"),)

    def __str__(self):
        return f"{self.name} ({self.market.name})"

# -------------------------
# Campaigns & Activities
# -------------------------
class Campaign(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=32, choices=CampaignType.choices, default=CampaignType.PROMO)
    budget_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    budget_spent = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    objectives = models.JSONField(blank=True, null=True)
    target_regions = models.JSONField(blank=True, null=True)
    target_markets = models.ManyToManyField(Market, blank=True, related_name="campaigns")
    target_products = models.ManyToManyField(Product, blank=True, related_name="campaigns")
    status = models.CharField(max_length=32, choices=CampaignStatus.choices, default=CampaignStatus.DRAFT)
    approval_required = models.BooleanField(default=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.name} ({self.type})"

class Activity(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="activities", null=True, blank=True)
    visit = models.ForeignKey("Visit", on_delete=models.SET_NULL, related_name="activities", null=True, blank=True)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    activity_type = models.CharField(max_length=64)
    count = models.PositiveIntegerField(default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    media = models.ManyToManyField("Attachment", blank=True)
    notes = models.TextField(blank=True, null=True)
    executed_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Activity {self.activity_type} by {self.agent} ({self.campaign})"

class PromoCode(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, unique=True)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="promo_codes", null=True, blank=True)
    discount_type = models.CharField(max_length=32, blank=True, null=True)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.code} ({self.campaign})"

# -------------------------
# Attachment / Media
# -------------------------
class Attachment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to="attachments/%Y/%m/%d/")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    associated_type = models.CharField(max_length=64, blank=True, null=True)
    associated_id = models.UUIDField(null=True, blank=True)
    mime_type = models.CharField(max_length=128, blank=True, null=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"Attachment {self.file.name}"

# -------------------------
# Visit, Sale & Payment
# -------------------------
class Visit(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="visits")
    market = models.ForeignKey(Market, on_delete=models.PROTECT, related_name="visits")
    outlet = models.ForeignKey(Outlet, on_delete=models.SET_NULL, null=True, blank=True)
    datetime = models.DateTimeField(default=timezone.now)
    geo_lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    geo_long = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    media = models.ManyToManyField(Attachment, blank=True, related_name="visits")
    purpose = models.CharField(max_length=20, choices=VisitPurpose.choices, blank=True, null=True)

    class Meta:
        ordering = ["-datetime"]

    def __str__(self):
        return f"Visit {self.agent} @ {self.market} on {self.datetime}"

class Sale(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="sales")
    market = models.ForeignKey(Market, on_delete=models.PROTECT, related_name="sales")
    visit = models.ForeignKey(Visit, on_delete=models.SET_NULL, null=True, blank=True, related_name="sales")
    pack = models.ForeignKey(PackSize, on_delete=models.PROTECT)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    promo_code = models.ForeignKey(PromoCode, on_delete=models.SET_NULL, null=True, blank=True)
    revenue = models.DecimalField(max_digits=14, decimal_places=2, editable=False, default=0)
    timestamp = models.DateTimeField(default=timezone.now)
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name="sales")
    ledger_ref = models.UUIDField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["-timestamp"]

    def save(self, *args, **kwargs):
        self.revenue = (self.unit_price * self.quantity) - (self.discount_amount or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Sale {self.id} {self.pack} x{self.quantity} by {self.agent}"

class Payment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="payments")
    method = models.CharField(max_length=32, choices=PaymentMethod.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=32, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    transaction_ref = models.CharField(max_length=128, blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.method} {self.amount} ({self.status})"

# -------------------------
# Stock Operations & Ledger
# -------------------------
class Allocation(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slip_number = models.CharField(max_length=100, unique=True)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="allocations")
    pack = models.ForeignKey(PackSize, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    processed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Allocation {self.slip_number} → {self.agent}"

class Transfer(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="transfers_out")
    to_agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="transfers_in", null=True, blank=True)
    to_market = models.ForeignKey(Market, on_delete=models.PROTECT, null=True, blank=True)
    pack = models.ForeignKey(PackSize, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    reason = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=32, choices=TransferStatus.choices, default=TransferStatus.PENDING)
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_transfers")
    processed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Transfer {self.id} {self.pack} x{self.quantity}"

class Return(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="returns")
    pack = models.ForeignKey(PackSize, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    reason_code = models.CharField(max_length=128)
    attachments = models.ManyToManyField(Attachment, blank=True)
    status = models.CharField(max_length=32, choices=ReturnStatus.choices, default=ReturnStatus.PENDING)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"Return {self.id} by {self.agent}"

class Adjustment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pack = models.ForeignKey(PackSize, on_delete=models.PROTECT)
    quantity = models.IntegerField(help_text="Signed quantity: + inbound, - outbound")
    reason_code = models.CharField(max_length=128)
    notes = models.TextField(blank=True, null=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"Adjustment {self.pack} {self.quantity}"

class StockLedger(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    movement_type = models.CharField(max_length=32, choices=MovementType.choices)
    source_ref = models.UUIDField(null=True, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="ledger_entries")
    market = models.ForeignKey(Market, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    pack = models.ForeignKey(PackSize, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    balance_after = models.IntegerField(null=True, blank=True)
    reason_code = models.CharField
