from celery import Celery

def make_celery(app):
    """
    Creates a Celery instance and ties it to the Flask app context.

    Without this, Celery workers run in separate processes and don't have
    access to Flask's app context (database, config, extensions).

    This factory ensures tasks execute inside Flask's application context.
    """
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL'],
        backend=app.config['CELERY_RESULT_BACKEND']
    )

    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery