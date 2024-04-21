from django.contrib import admin
from .models import Abv

# Register your models here.
@admin.register(Abv)
class AbvAdmin(admin.ModelAdmin):
    list_display = ("lwin11",
                    "abv",
                    "date_created",
                    )
