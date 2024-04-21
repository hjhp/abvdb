from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from django.conf import settings # For the User foreign key: https://docs.djangoproject.com/en/5.0/topics/auth/customizing/#referencing-the-user-model.

# Create your models here.

class Abv(models.Model):
    lwin11 = models.CharField(max_length = 11,
                              validators = [RegexValidator(regex = r"^\d{11}$",
                                                           message = "Must be an 11-digit integer."
                                                           )
                                            ]
                              )
    abv = models.FloatField(max_length = 5,
                            validators = [RegexValidator(regex = r"^\d{1,3}\.\d{1}$",
                                                         message = "Must be a float from 0.0–100.0 with 1 decimal place, e.g. '0.0', '14.0', '100.0'."
                                                         )
                                          ]
                            )
    date_created = models.DateTimeField(auto_now_add = True)
    submittor_ip = models.GenericIPAddressField(protocol = "both")
    user = models.ForeignKey( # This field actually becomes user_id in the database. But it seems it must be called "user" because the related table is called "User"? I deduced that from https://zerotobyte.com/complete-guide-to-django-foreignkey/. And indeed in views.py we must refer to this field as "user_id", not "user", otherwise we get the ValueError '"Abv.user" must be a "User" instance.' 'Setting db_column = "user"' here (and changing views.py to "intermediary_form.user = request.user.id" rather than "intermediary_form.user_id = request.user.id") results in the same ValueError. I don't understand.
        settings.AUTH_USER_MODEL,
        on_delete = models.SET_NULL,
        null = True,
    )

    def __str__(self):
        return self.lwin11
