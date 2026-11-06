from sk_common.people.models import AcademicYear, Person, StudyClass
from sk_common.testing import login_as

from app.modules.staff.models import Psychologist
from app.modules.tests.models import Option, Question, Scale, ScaleOption, Test
from app.scoring import nocobase_script

FREQUENCY = ['Почти никогда', 'Иногда', 'Часто', 'Почти всегда']


async def motivation_test(db) -> Test:
    """Методика «Мотивация учения»: 40 вопросов со шкалой частоты 1–4."""
    scale = Scale(title='Частота переживания', code='freq_1_4')
    scale.options = [ScaleOption(label=label, value=str(n), score=n, order=n) for n, label in enumerate(FREQUENCY, 1)]
    test = Test(
        title='Диагностика мотивации учения',
        code='motivation_learning',
        needs_birth_date=True,
        scoring_script=nocobase_script('motivation_learning'),
    )
    test.questions = [
        Question(order=n, text=f'Утверждение {n}', question_type='scale', scale=scale) for n in range(1, 41)
    ]
    db.add(test)
    await db.commit()
    return test


async def ranking_test(db) -> Test:
    test = Test(title='Порядок цветов', code='colors_demo', scoring_script='return { total: data.answers.length }')
    question = Question(order=1, code='color_preference', text='Расположи цвета', question_type='ranking')
    question.options = [Option(label=c, value=c, order=n) for n, c in enumerate(['red', 'green', 'blue'], 1)]
    test.questions = [question]
    db.add(test)
    await db.commit()
    return test


async def school_class(db, name='7В', students=3) -> tuple[StudyClass, list[Person]]:
    year = AcademicYear(name='2026-2027', is_current=True)
    study_class = StudyClass(name=name, grade=7, letter=name[-1], academic_year=year)
    db.add(study_class)
    await db.flush()
    persons = [
        Person(
            last_name=f'Ученик{n}',
            first_name='Тест',
            email=f'student{n}@example.org',
            is_student=True,
            gender='female' if n % 2 else 'male',
            class_id=study_class.id,
        )
        for n in range(1, students + 1)
    ]
    db.add_all(persons)
    await db.commit()
    return study_class, persons


async def login_psychologist(db, client, email='psy@skolkovo.example.org'):
    user = await login_as(db, client, email=email, last_name='Психологова')
    db.add(Psychologist(user_id=user.id))
    await db.commit()
    return user


async def login_student(db, client, person: Person):
    """Вход ученика: учётная запись привязана к его персоне из справочника."""
    from sk_common.auth.service import open_session
    from sk_common.people.service import ensure_user

    user = await ensure_user(db, person, person.email)
    access, _ = await open_session(db, user, 'skolstream', 'pytest', '127.0.0.1')
    await db.commit()
    from app.core.config import settings

    client.cookies.set(settings.auth.access_cookie, access)
    return user
