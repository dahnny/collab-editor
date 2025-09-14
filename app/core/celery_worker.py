from celery import Celery
import time
# import app.tasks.email


celery_app = Celery(
    "collab_editor",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["app.tasks.email"],
)



