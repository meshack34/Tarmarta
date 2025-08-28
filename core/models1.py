from django.db import models
from django.contrib.auth.models import AbstractUser

# ============================================================
# Custom User Model
# ============================================================
class User(AbstractUser):
    ROLE_CHOICES = [
        ("ADMIN", "Administrator"),
        ("AGENT", "Distribution Agent"),
        ("MANAGER", "Manager"),
        ("MARKETING", "Marketing Officer"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="AGENT")
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_soft_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


# ============================================================
# Product Catalog
# ============================================================
class Product(models.Model):
    CATEGORY_CHOICES = [
        ("BLACK", "Black Tea"),
        ("GREEN", "Green Tea"),
    ]
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_soft_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PackSize(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="pack_sizes")
    size_grams = models.PositiveIntegerField()
    unit = models.CharField(max_length=10, default="g")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} - {self.size_grams}{self.unit}"


class PriceList(models.Model):
    pack = models.ForeignKey(PackSize, on_delete=models.CASCADE, related_name="prices")
    market = models.ForeignKey("Market", on_delete=models.CASCADE, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    effective_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("pack", "market", "effective_date")

    def clean(self):
        # TODO: enforce no overlapping dates per pack-market
        pass

    def __str__(self):
        return f"{self.pack} @ {self.price}"


# ============================================================
# Market & Outlet
# ============================================================
class Market(models.Model):
    MARKET_TYPES = [
        ("URBAN", "Urban"),
        ("RURAL", "Rural"),
        ("SUPERMARKET", "Supermarket"),
        ("WHOLESALE", "Wholesale"),
    ]
    name = models.CharField(max_length=120, unique=True)
    region = models.CharField(max_length=120)
    type = models.CharField(max_length=20, choices=MARKET_TYPES, default="URBAN")
    is_active = models.BooleanField(default=True)
    is_soft_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Outlet(models.Model):
    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name="outlets")
    name = models.CharField(max_length=120)
    owner_name = models.CharField(max_length=120, blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.market.name})"


# ============================================================
# Marketing Campaigns & Promotions
# ============================================================
class Campaign(models.Model):
    CAMPAIGN_TYPES = [
        ("TRADE", "Trade Promotion"),
        ("CONSUMER", "Consumer Promotion"),
        ("EVENT", "Event"),
    ]
    STATUS_CHOICES = [
        ("PLANNED", "Planned"),
        ("ACTIVE", "Active"),
        ("CLOSED", "Closed"),
    ]
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    campaign_type = models.CharField(max_length=20, choices=CAMPAIGN_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PLANNED")
    objectives = models.TextField(blank=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    approval_required = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="approved_campaigns")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="created_campaigns")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Activity(models.Model):
    ACTIVITY_TYPES = [
        ("SAMPLING", "Product Sampling"),
        ("MERCHANDISING", "Merchandising"),
        ("DEMOS", "Demonstrations"),
        ("SPONSORSHIP", "Sponsorship"),
    ]
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="activities")
    name = models.CharField(max_length=200)
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    market = models.ForeignKey(Market, on_delete=models.SET_NULL, null=True, blank=True)
    outlet = models.ForeignKey(Outlet, on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_activities")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PromoCode(models.Model):
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    discount_percent = models.PositiveIntegerField()
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


# ============================================================
# Stock Operations (Allocations, Transfers, Returns, Adjustments)
# ============================================================
class Allocation(models.Model):
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="allocations")
    pack = models.ForeignKey(PackSize, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    slip_number = models.CharField(max_length=100, unique=True)
    allocation_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Transfer(models.Model):
    from_agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transfers_out")
    to_agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transfers_in")
    pack = models.ForeignKey(PackSize, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    transfer_date = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_transfers")
    created_at = models.DateTimeField(auto_now_add=True)


class Return(models.Model):
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="returns")
    pack = models.ForeignKey(PackSize, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    reason = models.CharField(max_length=255)
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Adjustment(models.Model):
    pack = models.ForeignKey(PackSize, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    reason = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="adjustments")
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="approved_adjustments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


# ============================================================
# Visits & Sales
# ============================================================
class Visit(models.Model):
    PURPOSE_CHOICES = [
        ("CHECKUP", "Check-up"),
        ("DELIVERY", "Delivery"),
        ("PROMO", "Promotion"),
    ]
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="visits")
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE, null=True, blank=True)
    datetime = models.DateTimeField()
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, blank=True)
    gps_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    gps_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Sale(models.Model):
    PAYMENT_METHODS = [
        ("CASH", "Cash"),
        ("CREDIT", "Credit"),
        ("MPESA", "M-Pesa"),
    ]
    agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sales")
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE, null=True, blank=True)
    pack = models.ForeignKey(PackSize, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default="CASH")
    currency = models.CharField(max_length=10, default="KES")
    timestamp = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.revenue = self.quantity * self.price
        super().save(*args, **kwargs)


# ============================================================
# Stock Ledger & Snapshots
# ============================================================
class StockLedger(models.Model):
    MOVEMENT_TYPES = [
        ("ALLOCATION", "Allocation"),
        ("TRANSFER_OUT", "Transfer Out"),
        ("TRANSFER_IN", "Transfer In"),
        ("SALE", "Sale"),
        ("RETURN", "Return"),
        ("ADJUSTMENT", "Adjustment"),
    ]
    agent = models.ForeignKey(User, on_delete=models.CASCADE)
    pack = models.ForeignKey(PackSize, on_delete=models.CASCADE)
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()
    balance_after = models.IntegerField()
    related_object_id = models.CharField(max_length=100, null=True, blank=True)
    checksum = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["agent", "pack", "created_at"]),
        ]


class InventorySnapshot(models.Model):
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
class SyncRecord(models.Model):
    object_type = models.CharField(max_length=50)
    object_id = models.CharField(max_length=100)
    action = models.CharField(max_length=20, choices=[("CREATE", "Create"), ("UPDATE", "Update"), ("DELETE", "Delete")])
    external_ref = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=[("PENDING", "Pending"), ("SENT", "Sent"), ("FAILED", "Failed")], default="PENDING")
    last_attempt = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AuditTrail(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=200)
    model = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
