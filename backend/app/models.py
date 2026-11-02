"""Реестр моделей для Alembic. Люди, вход и журнал — из sk_common."""

from sk_common import models as common_models
from sk_common.db import Base

from app.modules.attempts import models as attempts_models
from app.modules.staff import models as staff_models
from app.modules.tests import models as tests_models

__all__ = ['Base', 'attempts_models', 'common_models', 'staff_models', 'tests_models']
