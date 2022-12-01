INSTALLED_APPS = ("testapp",)

SECRET_KEY = "0VHAq7X9g5QCIoym4WTTarYEIhyXAu4H0rxcsu2FqzIjx4BOJXsdlxchKTpJkCCK"

DEBUG = True

USE_TZ = True

ROOT_URLCONF = "testapp.testapp.urls"

MIDDLEWARE = ["boston_logger.middleware.RequestResponseLoggerMiddleware"]
