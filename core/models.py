# core/models.py
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
import uuid
# ============================================================
# Utility Choices
# ============================================================
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
    TRADE = "trade", "Trade Promotion"
    CONSUMER = "consumer", "Consumer Promotion"
    EVENT = "event", "Event"
    PROMO = "promo", "Promotion"
    SAMPLING = "sampling", "Sampling"
    DISCOUNT = "discount", "Discount"

class CampaignStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    ACTIVE = "active", "Active"
    CLOSED = "closed", "Closed"
    DRAFT = "draft", "Draft"
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

# ============================================================
# Abstracts
# ============================================================
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

# ============================================================
# User Model
# ============================================================


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username must be set")
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Role.ADMIN)  # 👈 Force admin role

        return self.create_user(username, email, password, **extra_fields)


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
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="team", limit_choices_to={"role": Role.MANAGER},
    )

    objects = UserManager()   # 👈 attach your manager here

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.username} ({self.role})"

# ============================================================
# Products, Packs, Pricing
# ============================================================
# core/models.py

class Product(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)   # e.g. "Green Tea", "Black Tea"
    category = models.CharField(
        max_length=50,
        choices=[("GREEN", "Green Tea"), ("BLACK", "Black Tea")],
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sku = models.CharField(max_length=128, unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.category})"


class PackSize(TimeStampedModel):
    PACKAGING_CHOICES = [
        ("SINGLE", "Single Pack"),
        ("BOX", "Box/Carton"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="packs")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="packs")

    label = models.CharField(max_length=50)  # e.g. "40g", "80g", "36 pieces"
    packaging_type = models.CharField(max_length=20, choices=PACKAGING_CHOICES, default="SINGLE")
    unit = models.CharField(max_length=32, default="g")  # grams or pieces
    sku = models.CharField(max_length=128, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = (("product", "label", "packaging_type"),)

    def __str__(self):
        return f"{self.product.name} — {self.label} ({self.get_packaging_type_display()})"


class PriceList(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pack = models.ForeignKey(PackSize, on_delete=models.CASCADE, related_name="prices")
    market = models.ForeignKey("Market", on_delete=models.CASCADE, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    discount_policy = models.JSONField(blank=True, null=True)
    effective_from = models.DateField()
    effective_to = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=16, choices=PriceListStatus.choices, default=PriceListStatus.ACTIVE)

    class Meta:
        unique_together = ("pack", "market", "effective_from")
        indexes = [models.Index(fields=["pack", "market", "effective_from", "effective_to"])]

    def __str__(self):
        return f"{self.pack} @ {self.unit_price} KES"


# ============================================================
# Market & Outlet
# ============================================================
class Market(TimeStampedModel):
    MARKET_TYPES = [
        ("URBAN", "Urban"),
        ("RURAL", "Rural"),
        ("SUPERMARKET", "Supermarket"),
        ("WHOLESALE", "Wholesale"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    region = models.CharField(max_length=128)
    type = models.CharField(max_length=20, choices=MARKET_TYPES, default="URBAN")
    gps_lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    gps_long = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    status = models.BooleanField(default=True)

    class Meta:
        unique_together = (("name", "region"),)

    def __str__(self):
        return f"{self.name} — {self.region}"

class Outlet(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name="outlets")
    name = models.CharField(max_length=200)
    owner_name = models.CharField(max_length=120, blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    descriptor = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = (("market", "name"),)

    def __str__(self):
        return f"{self.name} ({self.market.name})"

# ============================================================
# Campaigns & Promotions
# ============================================================
class Campaign(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=32, choices=CampaignType.choices, default=CampaignType.PROMO)
    description = models.TextField(blank=True)
    budget_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    budget_spent = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    objectives = models.JSONField(blank=True, null=True)
    target_regions = models.JSONField(blank=True, null=True)
    target_markets = models.ManyToManyField(Market, blank=True, related_name="campaigns")
    target_products = models.ManyToManyField(Product, blank=True, related_name="campaigns")
    status = models.CharField(max_length=32, choices=CampaignStatus.choices, default=CampaignStatus.PLANNED)
    approval_required = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_campaigns")
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_campaigns")

    def __str__(self):
        return f"{self.name} ({self.type})"

class Activity(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="activities", null=True, blank=True)
    visit = models.ForeignKey("Visit", on_delete=models.SET_NULL, related_name="activities", null=True, blank=True)
    agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_activities")
    name = models.CharField(max_length=200)
    activity_type = models.CharField(max_length=64)
    market = models.ForeignKey(Market, on_delete=models.SET_NULL, null=True, blank=True)
    outlet = models.ForeignKey(Outlet, on_delete=models.SET_NULL, null=True, blank=True)
    count = models.PositiveIntegerField(default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    media = models.ManyToManyField("Attachment", blank=True)
    notes = models.TextField(blank=True, null=True)
    executed_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} ({self.activity_type})"

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
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.code} ({self.campaign})"

class Attachment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to="attachments/%Y/%m/%d/")
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    associated_type = models.CharField(max_length=64, blank=True, null=True)
    associated_id = models.UUIDField(null=True, blank=True)
    mime_type = models.CharField(max_length=128, blank=True, null=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"Attachment {self.file.name}"

# ============================================================
# Visits, Sales, Payments
# ============================================================
class Visit(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(User, on_delete=models.PROTECT, related_name="visits")
    market = models.ForeignKey(Market, on_delete=models.PROTECT, related_name="visits")
    outlet = models.ForeignKey(Outlet, on_delete=models.SET_NULL, null=True, blank=True)
    datetime = models.DateTimeField(default=timezone.now)
    geo_lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    geo_long = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    media = models.ManyToManyField(Attachment, blank=True, related_name="visits")
    purpose = models.CharField(max_length=20, choices=VisitPurpose.choices, blank=True, null=True)

    def __str__(self):
        return f"Visit {self.agent} @ {self.market}"

class Sale(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(User, on_delete=models.PROTECT, related_name="sales")
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
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    currency = models.CharField(max_length=10, default="KES")

    def save(self, *args, **kwargs):
        self.revenue = (self.unit_price * self.quantity) - (self.discount_amount or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Sale {self.id} {self.pack} x{self.quantity}"

class Payment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="payments")
    method = models.CharField(max_length=32, choices=PaymentMethod.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=32, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    transaction_ref = models.CharField(max_length=128, blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Payment {self.method} {self.amount} ({self.status})"

# ============================================================
# Stock Operations & Ledger
# ============================================================
class Allocation(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slip_number = models.CharField(max_length=100, unique=True)
    agent = models.ForeignKey(User, on_delete=models.PROTECT, related_name="allocations")
    pack = models.ForeignKey(PackSize, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"Allocation {self.slip_number}"

class Transfer(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_agent = models.ForeignKey(User, on_delete=models.PROTECT, related_name="transfers_out")
    to_agent = models.ForeignKey(User, on_delete=models.PROTECT, related_name="transfers_in", null=True, blank=True)
    to_market = models.ForeignKey(Market, on_delete=models.PROTECT, null=True, blank=True)
    pack = models.ForeignKey(PackSize, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    reason = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=32, choices=TransferStatus.choices, default=TransferStatus.PENDING)
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_transfers")
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"Transfer {self.id}"

class Return(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(User, on_delete=models.PROTECT, related_name="returns")
    pack = models.ForeignKey(PackSize, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    reason_code = models.CharField(max_length=128)
    attachments = models.ManyToManyField(Attachment, blank=True)
    status = models.CharField(max_length=32, choices=ReturnStatus.choices, default=ReturnStatus.PENDING)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"Return {self.id}"

class Adjustment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pack = models.ForeignKey(PackSize, on_delete=models.PROTECT)
    quantity = models.IntegerField(help_text="Signed quantity: + inbound, - outbound")
    reason_code = models.CharField(max_length=128)
    notes = models.TextField(blank=True, null=True)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"Adjustment {self.pack}"

class StockLedger(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    movement_type = models.CharField(max_length=32, choices=MovementType.choices)
    source_ref = models.UUIDField(null=True, blank=True)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="actor_ledger")
    agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="ledger_entries")
    market = models.ForeignKey(Market, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    pack = models.ForeignKey(PackSize, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    balance_after = models.IntegerField(null=True, blank=True)
    reason_code = models.CharField(max_length=128, blank=True, null=True)

class InventorySnapshot(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(User, on_delete=models.CASCADE)
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    pack = models.ForeignKey(PackSize, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    snapshot_date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ("agent", "market", "pack", "snapshot_date")

# ============================================================
# Integration & Audit
# ============================================================
class SyncRecord(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    object_type = models.CharField(max_length=50)
    object_id = models.CharField(max_length=100)
    action = models.CharField(max_length=20, choices=[("CREATE", "Create"), ("UPDATE", "Update"), ("DELETE", "Delete")])
    external_ref = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=[("PENDING", "Pending"), ("SENT", "Sent"), ("FAILED", "Failed")], default="PENDING")
    last_attempt = models.DateTimeField(null=True, blank=True)

class AuditTrail(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=200)
    model = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)