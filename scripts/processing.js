/*
    Скрипт в WorkFlow NocoBase для обработки данных попытки тестирования и подготовки их к отображению в шаблоне.
*/

function getAgeFromBirthDate(birthDate) {
  if (!birthDate) return null;

  const today = new Date();
  const dob = new Date(birthDate);

  if (Number.isNaN(dob.getTime())) return null;

  let age = today.getFullYear() - dob.getFullYear();

  const monthDiff = today.getMonth() - dob.getMonth();
  const dayDiff = today.getDate() - dob.getDate();

  if (monthDiff < 0 || (monthDiff === 0 && dayDiff < 0)) {
    age -= 1;
  }

  return age;
}

function toNumberOrNull(value) {
  if (value == null || value === '') return null;
  const num = Number(value);
  return Number.isNaN(num) ? null : num;
}

function normalizeGenderValue(gender) {
  if (!gender) return null;

  const map = {
    male: 'мужской',
    female: 'женский',
  };

  return map[gender] ?? gender;
}

function normalizeRanking(answer) {
  const items = Array.isArray(answer.answer_ranking_items)
    ? answer.answer_ranking_items
    : [];

  return items
    .map((item) => ({
      option_id: item.option_id ?? item.option?.id ?? null,
      option_label: item.option?.label ?? item.option?.title ?? null,
      option_value: item.option?.value ?? null,
      option_score: item.option?.score ?? null,
      rank: item.rank != null ? Number(item.rank) : null,
      score: item.score != null ? Number(item.score) : null,
    }))
    .sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999));
}

function normalizeMultipleChoice(answer) {
  const options = Array.isArray(answer.options) ? answer.options : [];

  return options.map((option) => ({
    option_id: option.id,
    option_label: option.label ?? option.title ?? null,
    option_value: option.value ?? null,
    option_score: option.score ?? null,
  }));
}

function normalizeSingleChoice(answer) {
  if (answer.scale_option) {
    return {
      option_id: answer.scale_option.id,
      label: answer.scale_option.label ?? null,
      value: answer.scale_option.value ?? null,
      score: answer.scale_option.score ?? null,
      source: 'scale_option',
    };
  }

  if (answer.option) {
    return {
      option_id: answer.option.id,
      label: answer.option.label ?? answer.option.title ?? null,
      value: answer.option.value ?? null,
      score: answer.option.score ?? null,
      source: 'option',
    };
  }

  return null;
}

function normalizeAnswer(answer) {
  const question = answer.question || {};
  const questionType = question.question_type || null;

  const questionNumber =
    question.order ??
    question.number ??
    answer.question_number ??
    null;

  const base = {
    answer_id: answer.id,
    question_id: question.id ?? answer.question_id ?? null,
    question_number: questionNumber != null ? Number(questionNumber) : null,
    question_type: questionType,
    question_code: question.code ?? null,
    question_text: question.text ?? null,
    display: answer.display ?? null,
    raw: {
      text: answer.text ?? null,
      number: answer.number ?? null,
      boolean: answer.boolean ?? null,
      option_id: answer.option_id ?? null,
      scale_option_id: answer.scale_option_id ?? null,
    },
  };

  if (questionType === 'scale') {
    const selected = normalizeSingleChoice(answer);

    return {
      ...base,
      value: selected?.value != null ? toNumberOrNull(selected.value) ?? selected.value : null,
      selected_option: null,
      scale_option: selected,
      values: null,
      ranking: null,
      text: answer.text ?? null,
      number: toNumberOrNull(answer.number),
      boolean: answer.boolean ?? null,
    };
  }

  if (questionType === 'single_choice') {
    const selected = normalizeSingleChoice(answer);

    return {
      ...base,
      value: selected?.value != null ? toNumberOrNull(selected.value) ?? selected.value : null,
      selected_option: selected,
      scale_option: null,
      values: null,
      ranking: null,
      text: answer.text ?? null,
      number: toNumberOrNull(answer.number),
      boolean: answer.boolean ?? null,
    };
  }

  if (questionType === 'multiple_choice') {
    return {
      ...base,
      value: null,
      selected_option: null,
      scale_option: null,
      values: normalizeMultipleChoice(answer),
      ranking: null,
      text: answer.text ?? null,
      number: toNumberOrNull(answer.number),
      boolean: answer.boolean ?? null,
    };
  }

  if (questionType === 'ranking' || questionType === 'rank') {
    return {
      ...base,
      value: null,
      selected_option: null,
      scale_option: null,
      values: null,
      ranking: normalizeRanking(answer),
      text: answer.text ?? null,
      number: toNumberOrNull(answer.number),
      boolean: answer.boolean ?? null,
    };
  }

  if (questionType === 'text') {
    return {
      ...base,
      value: answer.text ?? null,
      selected_option: null,
      scale_option: null,
      values: null,
      ranking: null,
      text: answer.text ?? null,
      number: null,
      boolean: null,
    };
  }

  if (questionType === 'number') {
    return {
      ...base,
      value: toNumberOrNull(answer.number),
      selected_option: null,
      scale_option: null,
      values: null,
      ranking: null,
      text: null,
      number: toNumberOrNull(answer.number),
      boolean: null,
    };
  }

  if (questionType === 'yes_no') {
    return {
      ...base,
      value: answer.boolean,
      selected_option: null,
      scale_option: null,
      values: null,
      ranking: null,
      text: null,
      number: null,
      boolean: answer.boolean ?? null,
    };
  }

  return {
    ...base,
    value:
      toNumberOrNull(answer.scale_option?.value) ??
      toNumberOrNull(answer.option?.value) ??
      toNumberOrNull(answer.number) ??
      answer.text ??
      answer.boolean ??
      null,
    selected_option: normalizeSingleChoice(answer),
    scale_option: answer.scale_option
      ? {
          option_id: answer.scale_option.id,
          label: answer.scale_option.label ?? null,
          value: answer.scale_option.value ?? null,
          score: answer.scale_option.score ?? null,
          source: 'scale_option',
        }
      : null,
    values: normalizeMultipleChoice(answer),
    ranking: normalizeRanking(answer),
    text: answer.text ?? null,
    number: toNumberOrNull(answer.number),
    boolean: answer.boolean ?? null,
  };
}

// ====== ОСНОВНАЯ ЧАСТЬ ======

if (!attempt) {
  throw new Error('Не найдена попытка');
}

const person = attempt.person;

if (!person) {
  throw new Error('Не найдены данные person');
}

const directAge = toNumberOrNull(person.age);
const birthDate = person.birth_date || person.date_of_birth || null;

const age = directAge != null
  ? directAge
  : getAgeFromBirthDate(birthDate);

const answers = Array.isArray(attempt.answers)
  ? attempt.answers.map(normalizeAnswer)
  : [];

return {
  attempt_id: attempt.id,
  test_id: attempt.test?.id ?? null,
  test_code: attempt.test?.code || null,
  test_title: attempt.test?.title || null,
  submitted_at: attempt.submitted_at || null,
  student: {
    id: person.id,
    name: person.full_name || person.name || null,
    birth_date: birthDate,
    age: age ?? null,
    gender: person.gender || null,
    gender_value: normalizeGenderValue(person.gender),
  },
  answers,
};