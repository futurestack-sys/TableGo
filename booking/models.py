from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

SLOTS = ["11:00", "12:00", "13:00", "18:00", "19:00", "20:00"]
LIVE = ["pending", "confirmed"]


class Restaurant(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    cuisine = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    fixtures = models.JSONField(default=list, blank=True, help_text="Floor-plan areas: label, x, y, w, h")
    location = models.CharField(max_length=80, blank=True)
    hours = models.CharField(max_length=60, blank=True)
    active = models.BooleanField(default=True)

    def free_table(self, date, time, guests):
        """Smallest table that fits the party and is not booked at that date/time."""
        busy = self.reservation_set.filter(date=date, time=time, status__in=LIVE).values_list("table_id", flat=True)
        return self.table_set.filter(seats__gte=guests).exclude(id__in=busy).order_by("seats").first()

    def __str__(self):
        return self.name


class RestaurantManager(models.Model):
    """Links a user account to the one restaurant they manage."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="manager")
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user} manages {self.restaurant}"


class Table(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    name = models.CharField(max_length=20)
    seats = models.PositiveSmallIntegerField()
    shape = models.CharField(max_length=10, default="square",
                             choices=[("square", "Square"), ("rect", "Rectangle"), ("long", "Long"), ("banquet", "Banquet"), ("round", "Round")])
    x = models.PositiveSmallIntegerField(default=50, help_text="Left position on the floor plan, 0-100")
    y = models.PositiveSmallIntegerField(default=50, help_text="Top position on the floor plan, 0-100")

    def __str__(self):
        return f"{self.restaurant.name} {self.name} ({self.seats})"


class Reservation(models.Model):
    STATUS = [("pending", "Pending"), ("confirmed", "Confirmed"), ("declined", "Declined"), ("cancelled", "Cancelled")]
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=100, blank=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    table = models.ForeignKey(Table, null=True, blank=True, on_delete=models.SET_NULL)
    date = models.DateField()
    time = models.CharField(max_length=5, choices=[(s, s) for s in SLOTS])
    guests = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(20)])
    phone = models.CharField(max_length=30, blank=True)
    occasion = models.CharField(max_length=30, blank=True)
    note = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "time"]

    def __str__(self):
        return f"R{self.pk} {self.restaurant} {self.date} {self.time}"
