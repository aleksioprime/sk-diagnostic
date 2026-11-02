"""Данные для расчёта в том виде, в каком их получали скрипты NocoBase (app.scoring)."""

from datetime import UTC, date, datetime

from sk_common.people.models import Person

from app.modules.attempts.models import Attempt
from app.modules.tests.models import Test

GENDER_VALUES = {'male': 'мужской', 'female': 'женский'}


def age_on(birth_date: date | None, moment: datetime | None) -> int | None:
    """Полных лет на дату прохождения."""
    if birth_date is None:
        return None
    day = (moment or datetime.now()).date()
    return day.year - birth_date.year - ((day.month, day.day) < (birth_date.month, birth_date.day))


def _number_or_text(value: str):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    return int(number) if number.is_integer() else number


def student_data(person: Person, moment: datetime | None) -> dict:
    return {
        'id': person.id,
        'name': ' '.join(part for part in (person.last_name, person.first_name) if part) or None,
        'birth_date': person.birth_date.isoformat() if person.birth_date else None,
        'age': age_on(person.birth_date, moment),
        'gender': person.gender,
        'gender_value': GENDER_VALUES.get(person.gender or ''),
    }


def build_input(attempt: Attempt, test: Test) -> dict:
    questions = {q.id: q for q in test.questions}
    answers = []
    for answer in attempt.answers:
        question = questions.get(answer.question_id)
        if question is None:
            continue
        options = {o.id: o for o in question.options}
        scale_options = {o.id: o for o in question.scale.options} if question.scale else {}
        item = {
            'question_id': question.id,
            'question_number': question.order,
            'question_code': question.code,
            'question_type': question.question_type,
            'question_text': question.text,
            'text': answer.text,
            'number': answer.number,
            'boolean': answer.boolean,
            'value': None,
            'scale_option': None,
            'selected_option': None,
            'ranking': None,
        }
        if answer.scale_option_id in scale_options:
            option = scale_options[answer.scale_option_id]
            item['scale_option'] = {'value': option.value, 'label': option.label, 'score': option.score}
            item['value'] = _number_or_text(option.value)
        elif answer.option_id in options:
            option = options[answer.option_id]
            item['selected_option'] = {'value': option.value, 'label': option.label, 'score': option.score}
            item['value'] = _number_or_text(option.value)
        elif answer.text is not None:
            item['value'] = answer.text
        elif answer.number is not None:
            item['value'] = answer.number
        if answer.ranking:
            item['ranking'] = [
                {
                    'rank': ranked.rank,
                    'option_id': ranked.option_id,
                    'option_value': options[ranked.option_id].value if ranked.option_id in options else None,
                    'option_label': options[ranked.option_id].label if ranked.option_id in options else None,
                }
                for ranked in answer.ranking
            ]
        answers.append(item)
    return {
        'attempt_id': attempt.id,
        'submitted_at': (
            attempt.submitted_at.astimezone(UTC).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            if attempt.submitted_at
            else None
        ),
        'test_id': test.id,
        'test_code': test.code,
        'test_title': test.title,
        'student': student_data(attempt.person, attempt.submitted_at),
        'answers': answers,
    }
