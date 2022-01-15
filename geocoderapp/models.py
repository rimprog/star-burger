from django.db import models
from django.utils import timezone


class Place(models.Model):
    address = models.CharField(
        'адрес',
        max_length=100,
        unique=True
    )
    latitude = models.FloatField(
        'широта',
        null=True,
        blank=True
    )
    longitude = models.FloatField(
        'долгота',
        null=True,
        blank=True
    )
    refreshed_at = models.DateTimeField(
        'обновлено',
        default=timezone.now,
        blank=True,
        null=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'место'
        verbose_name_plural = 'места'

    def __str__(self):
        return self.address
