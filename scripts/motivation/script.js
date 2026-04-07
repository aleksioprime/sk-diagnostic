/**
 * Методика диагностики мотивации учения школьников 10-16 лет
 */

/**
 * Пол ученика в человекочитаемом виде
 */
function getGenderLabel(gender) {
  if (gender === "male") return "Мужской";
  if (gender === "female") return "Женский";
  return "Не указан";
}

/**
 * Каждая шкала содержит список номеров вопросов
 */
const SCALES = {
  cognitive_activity: [2, 6, 10, 14, 18, 22, 26, 30, 34, 38], // Познавательная активность
  achievement_motivation: [4, 8, 12, 16, 20, 24, 28, 32, 36, 40], // Мотивация достижения
  anxiety: [1, 5, 9, 13, 17, 21, 25, 29, 33, 37], // Тревожность
  anger: [3, 7, 11, 15, 19, 23, 27, 31, 35, 39] // Гнев
};

// ПРИМЕЧАНИЕ: Применение обратной шкалы (реверса) требует уточнения у психологов.
// Нормы в Таблице 3 PDF методики эмпирически совпадают с Excel-расчётами при подсчёте
// RAW-сумм (без реверса). Закомментированный блок REVERSED оставлен для восстановления.
//
// const REVERSED = {
//   cognitive_activity:     [14, 30, 38],          // Вопросы 14, 30, 38 по шкале познавательной активности
//   achievement_motivation: [4, 12, 20, 28, 32],   // Вопросы 4, 12, 20, 28, 32 по шкале мотивации достижения
//   anxiety:                [1, 9, 25, 33],        // Вопросы 1, 9, 25, 33 по шкале тревожности
//   anger:                  [],                    // Нет обратных вопросов по шкале гнева
// };

/*
 * Нормы для каждой шкалы в зависимости от возрастной группы и пола
*/
const NORMS = {
  "10-11": {
    female: {
      cognitive_activity: {
        high: [31, 40],
        medium: [21, 30],
        low: [10, 20]
      },
      achievement_motivation: {
        high: [32, 40],
        medium: [22, 31],
        low: [10, 21]
      },
      anxiety: {
        high: [27, 40],
        medium: [20, 26],
        low: [10, 19]
      },
      anger: {
        high: [21, 40],
        medium: [14, 20],
        low: [10, 13]
      }
    },
    male: {
      cognitive_activity: {
        high: [28, 40],
        medium: [22, 27],
        low: [10, 21]
      },
      achievement_motivation: {
        high: [29, 40],
        medium: [21, 28],
        low: [10, 20]
      },
      anxiety: {
        high: [24, 40],
        medium: [17, 23],
        low: [10, 16]
      },
      anger: {
        high: [20, 40],
        medium: [13, 19],
        low: [10, 12]
      }
    }
  },

  "12-14": {
    female: {
      cognitive_activity: {
        high: [28, 40],
        medium: [21, 27],
        low: [10, 20]
      },
      achievement_motivation: {
        high: [31, 40],
        medium: [23, 30],
        low: [10, 22]
      },
      anxiety: {
        high: [25, 40],
        medium: [19, 24],
        low: [10, 18]
      },
      anger: {
        high: [19, 40],
        medium: [14, 19],
        low: [10, 13]
      }
    },
    male: {
      cognitive_activity: {
        high: [27, 40],
        medium: [19, 26],
        low: [10, 18]
      },
      achievement_motivation: {
        high: [25, 40],
        medium: [18, 24],
        low: [10, 17]
      },
      anxiety: {
        high: [26, 40],
        medium: [19, 25],
        low: [10, 18]
      },
      anger: {
        high: [23, 40],
        medium: [15, 22],
        low: [10, 14]
      }
    }
  },

  "15-16": {
    female: {
      cognitive_activity: {
        high: [29, 40],
        medium: [18, 28],
        low: [10, 17]
      },
      achievement_motivation: {
        high: [31, 40],
        medium: [22, 30],
        low: [10, 21]
      },
      anxiety: {
        high: [25, 40],
        medium: [17, 24],
        low: [10, 16]
      },
      anger: {
        high: [21, 40],
        medium: [14, 20],
        low: [10, 13]
      }
    },
    male: {
      cognitive_activity: {
        high: [31, 40],
        medium: [21, 29],
        low: [10, 20]
      },
      achievement_motivation: {
        high: [26, 40],
        medium: [18, 25],
        low: [10, 17]
      },
      anxiety: {
        high: [23, 40],
        medium: [16, 22],
        low: [10, 15]
      },
      anger: {
        high: [18, 40],
        medium: [12, 18],
        low: [10, 11]
      }
    }
  }
};

/**
 * Преобразует массив ответов в словарь вида:
 * { 1: 3, 2: 4, ... }
 */
function buildAnswersMap(answers = []) {
  const answersMap = {};

  for (const item of answers) {
    const questionNumber = item.question_number;

    if (questionNumber == null) {
      continue;
    }

    let value = null;

    if (typeof item.value === "number" && !Number.isNaN(item.value)) {
      value = item.value;
    } else if (
      item.selected_option &&
      item.selected_option.value != null &&
      !Number.isNaN(Number(item.selected_option.value))
    ) {
      value = Number(item.selected_option.value);
    }

    if (value != null) {
      answersMap[questionNumber] = value;
    }
  }

  return answersMap;
}

/**
 * Получить значение ответа для вопроса (без реверса)
 */
function getAnswerValue(questionNumber, answersMap) {
  const rawValue = answersMap[questionNumber];

  if (![1, 2, 3, 4].includes(rawValue)) {
    throw new Error(`Некорректный или отсутствующий ответ для вопроса ${questionNumber}`);
  }

  return rawValue;
}

// Вариант с обратной шкалой (реверсом) — раскомментировать при подтверждении психологами:
// function getAnswerValue(questionNumber, scaleName, answersMap) {
//   const rawValue = answersMap[questionNumber];
//   if (![1, 2, 3, 4].includes(rawValue)) {
//     throw new Error(`Некорректный или отсутствующий ответ для вопроса ${questionNumber}`);
//   }
//   const isReversed = REVERSED[scaleName].includes(questionNumber);
//   return isReversed ? 5 - rawValue : rawValue;
// }

/**
 * Подсчёт суммы по одной шкале
 */
function calcScale(scaleName, answersMap, scales = SCALES) {
  return scales[scaleName].reduce((sum, questionNumber) => {
    return sum + getAnswerValue(questionNumber, answersMap);
  }, 0);
}

// Вариант с реверсом:
// function calcScale(scaleName, answersMap, scales = SCALES) {
//   return scales[scaleName].reduce((sum, questionNumber) => {
//     return sum + getAnswerValue(questionNumber, scaleName, answersMap);
//   }, 0);
// }

/**
 * Определение уровня мотивации и текстовой интерпретации
 */
function getInterpretation(total) {
  if (total >= 45 && total <= 60) {
    return {
      level: "I",
      interpretation:
        "Продуктивная мотивация с выраженным преобладанием познавательной мотивации и положительным отношением к учению"
    };
  }

  if (total >= 29 && total <= 44) {
    return {
      level: "II",
      interpretation:
        "Продуктивная мотивация, позитивное отношение к учению, соответствие социальному нормативу"
    };
  }

  if (total >= 13 && total <= 28) {
    return {
      level: "III",
      interpretation:
        "Средний уровень с несколько сниженной познавательной мотивацией"
    };
  }

  if (total >= -2 && total <= 12) {
    return {
      level: "IV",
      interpretation:
        "Сниженная мотивация, переживание школьной скуки, отрицательное эмоциональное отношение к учению"
    };
  }

  return {
    level: "V",
    interpretation: "Резко отрицательное отношение к учению"
  };
}

/*
  * Нормы для каждой шкалы в зависимости от возрастной группы и пола
 */
function getLevelByNorm(value, norm) {
  if (value >= norm.high[0] && value <= norm.high[1]) return "high";
  if (value >= norm.medium[0] && value <= norm.medium[1]) return "medium";
  if (value >= norm.low[0] && value <= norm.low[1]) return "low";

  throw new Error(`Значение ${value} вне диапазонов`);
}

const LEVEL_LABELS = {
  high: "высокий",
  medium: "средний",
  low: "низкий"
};

/*
  * Возвращает возрастную группу по возрасту
  * 10-11, 12-14, 15-16
 */
function getAgeGroup(age) {
  if (age >= 10 && age <= 11) return "10-11";
  if (age >= 12 && age <= 14) return "12-14";
  if (age >= 15 && age <= 16) return "15-16";

  throw new Error("Возраст вне диапазона методики");
}

/*
  * Рассчитывает уровни по нормам для каждой шкалы на основе возраста и пола
 */
function calculateNormLevels(scales, age, gender) {
  const ageGroup = getAgeGroup(age);
  const normsByAge = NORMS[ageGroup];

  if (!normsByAge) {
    throw new Error(`Не найдены нормы для возрастной группы ${ageGroup}`);
  }

  const norms = normsByAge[gender];

  if (!norms) {
    throw new Error(`Не найдены нормы для пола "${gender}" и возрастной группы ${ageGroup}`);
  }

  return {
    cognitive_activity: getLevelByNorm(
      scales.cognitive_activity,
      norms.cognitive_activity
    ),
    achievement_motivation: getLevelByNorm(
      scales.achievement_motivation,
      norms.achievement_motivation
    ),
    anxiety: getLevelByNorm(
      scales.anxiety,
      norms.anxiety
    ),
    anger: getLevelByNorm(
      scales.anger,
      norms.anger
    )
  };
}

/**
 * Основная функция расчёта результата диагностики
 */
function calculateMotivationResult(data) {
  if (!data || typeof data !== "object") {
    throw new Error("Не переданы данные для расчёта");
  }

  if (!data.student) {
    throw new Error("Отсутствуют данные student");
  }

  if (data.student.age == null) {
    throw new Error("Отсутствует возраст student.age");
  }

  if (!data.student.gender) {
    throw new Error("Отсутствует пол student.gender");
  }

  // Преобразуем массив ответов в словарь для удобного доступа
  const answersMap = buildAnswersMap(data.answers || []);

  // Подсчитываем баллы по каждой шкале с учётом обратной шкалы
  const pa = calcScale("cognitive_activity", answersMap);
  const md = calcScale("achievement_motivation", answersMap);
  const t = calcScale("anxiety", answersMap);
  const g = calcScale("anger", answersMap);

  // Общая формула: ПА + МД + (–Т) + (–Г)
  const total = pa + md - t - g;

  // Получаем уровень мотивации и интерпретацию на основе общей суммы
  const { level, interpretation } = getInterpretation(total);

  const normLevels = calculateNormLevels(
    {
      cognitive_activity: pa,
      achievement_motivation: md,
      anxiety: t,
      anger: g
    },
    data.student.age,
    data.student.gender // "male" / "female"
  );

  // Формируем итоговый результат в нужном формате
  return {
    attempt: {
      id: data.attempt_id,
      submitted_at: data.submitted_at
    },
    test: {
      code: data.test_code,
      title: data.test_title || null
    },
    student: {
      id: data.student.id,
      name: data.student.name || null,
      birth_date: data.student.birth_date || null,
      age: data.student.age,
      gender: data.student.gender,
      gender_value: data.student.gender_value || null,
      gender_label: getGenderLabel(data.student.gender)
    },
    result: {
      level,
      total_score: total,
      interpretation,
      calculated_at: new Date().toISOString()
    },
    scales: [
      {
        code: "cognitive_activity",
        title: "Познавательная активность",
        value: pa,
        level: normLevels.cognitive_activity,
        level_label: LEVEL_LABELS[normLevels.cognitive_activity]
      },
      {
        code: "achievement_motivation",
        title: "Мотивация достижения",
        value: md,
        level: normLevels.achievement_motivation,
        level_label: LEVEL_LABELS[normLevels.achievement_motivation]
      },
      {
        code: "anxiety",
        title: "Тревожность",
        value: t,
        level: normLevels.anxiety,
        level_label: LEVEL_LABELS[normLevels.anxiety]
      },
      {
        code: "anger",
        title: "Гнев",
        value: g,
        level: normLevels.anger,
        level_label: LEVEL_LABELS[normLevels.anger]
      }
    ]
  };
}

// Экспортируем функцию для использования в других модулях
const result = calculateMotivationResult(data);

// Выводим результат в консоль (можно заменить на return для использования в API)
return {
  status: 'calculated',
  json: result
};