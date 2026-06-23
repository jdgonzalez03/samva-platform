from celery import shared_task

from django.utils import timezone

@shared_task
def what_time_is_it():
    now = timezone.now()
    print("The current time is {}".format(now))
