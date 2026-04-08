/**
 * Проективная методика «Домики»
 */

/**
 * Справочник цветов методики
 */
const COLORS = {
  blue: {
    code: "blue",
    number: 1,
    title: "Синий",
    type: "base_positive"
  },
  green: {
    code: "green",
    number: 2,
    title: "Зеленый",
    type: "base_positive"
  },
  red: {
    code: "red",
    number: 3,
    title: "Красный",
    type: "base_positive"
  },
  yellow: {
    code: "yellow",
    number: 4,
    title: "Желтый",
    type: "base_positive"
  },
  violet: {
    code: "violet",
    number: 5,
    title: "Фиолетовый",
    type: "ambivalent"
  },
  brown: {
    code: "brown",
    number: 6,
    title: "Коричневый",
    type: "negative"
  },
  gray: {
    code: "gray",
    number: 7,
    title: "Серый",
    type: "neutral"
  },
  black: {
    code: "black",
    number: 8,
    title: "Черный",
    type: "negative"
  }
};

/**
 * Аутогенная норма:
 * 34251607 в тексте методики дана как:
 * 3 – красный
 * 4 – желтый
 * 2 – зеленый
 * 5 – фиолетовый
 * 1 – синий
 * 6 – коричневый
 * 0 – серый
 * 7 – черный
 *
 * В нашем коде используем строковые ключи цветов в нормативном порядке
 */
const AUTOGENIC_NORM = [
  "red",
  "yellow",
  "green",
  "violet",
  "blue",
  "brown",
  "gray",
  "black"
];

/**
 * Блоки социальных эмоций
 */
const EMOTION_BLOCKS = [
  {
    title: "Блок базового комфорта",
    positive: "happiness",
    negative: "grief"
  },
  {
    title: "Блок личностного роста",
    positive: "justice",
    negative: "offense"
  },
  {
    title: "Блок межличностного взаимодействия",
    positive: "friendship",
    negative: "quarrel"
  },
  {
    title: "Блок потенциальной агрессии",
    positive: "kindness",
    negative: "malice"
  },
  {
    title: "Блок познания",
    positive: "admiration",
    negative: "boredom"
  }
];

/**
 * Человекочитаемые названия эмоций
 */
const EMOTION_TITLES = {
  happiness: "Счастье",
  grief: "Горе",
  justice: "Справедливость",
  offense: "Обида",
  friendship: "Дружба",
  quarrel: "Ссора",
  kindness: "Доброта",
  malice: "Злоба",
  boredom: "Скука",
  admiration: "Восхищение"
};

/**
 * Человекочитаемые названия домиков
 */
const HOUSE_TITLES = {
  soul: "Твоя душа",
  school_way: "Когда ты идешь в школу",
  reading_lesson: "На уроке литературы",
  writing_lesson: "На уроке письма",
  math_lesson: "На уроке математики",
  teacher_talk: "Когда разговариваешь с учителем",
  classmates: "Когда общаешься с одноклассниками",
  home: "Когда находишься дома",
  homework: "Когда делаешь уроки",
  custom_house: "Собственный домик"
};

const BASE_POSITIVE_COLORS = ["blue", "green", "red", "yellow"];
const NEGATIVE_COLORS = ["brown", "black"];
const SCHOOL_RELATED_CODES = [
  "school_way",
  "reading_lesson",
  "writing_lesson",
  "math_lesson",
  "teacher_talk",
  "classmates",
  "homework"
];

/**
 * Получить объект ответа по коду вопроса
 */
function findAnswerByCode(answers = [], code) {
  return answers.find((item) => item.question_code === code) || null;
}

/**
 * Получить строковое значение цвета из ответа
 */
function getColorValueFromAnswer(answer) {
  if (!answer) {
    throw new Error("Ответ не найден");
  }

  const candidates = [
    answer.value,
    answer.scale_option?.value,
    answer.selected_option?.value
  ];

  for (const candidate of candidates) {
    if (typeof candidate === "string" && COLORS[candidate]) {
      return candidate;
    }
  }

  throw new Error(`Не удалось определить цвет для question_code=${answer.question_code}`);
}

/**
 * Получить текстовое значение из ответа
 */
function getTextValueFromAnswer(answer) {
  if (!answer) {
    return null;
  }

  if (typeof answer.text === "string" && answer.text.trim()) {
    return answer.text.trim();
  }

  if (typeof answer.value === "string" && answer.value.trim()) {
    return answer.value.trim();
  }

  return null;
}

/**
 * Получить ranking в виде массива цветов по порядку предпочтения
 */
function getPreferenceOrder(answer) {
  if (!answer) {
    throw new Error("Не найден ответ задания №1");
  }

  if (!Array.isArray(answer.ranking) || !answer.ranking.length) {
    throw new Error("В ответе задания №1 отсутствует ranking");
  }

  const sorted = [...answer.ranking]
    .sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999));

  const result = sorted.map((item) => {
    const colorCode = item.option_value;

    if (!COLORS[colorCode]) {
      throw new Error(`Некорректный цвет в ranking: ${colorCode}`);
    }

    return colorCode;
  });

  if (new Set(result).size !== 8) {
    throw new Error("В задании №1 должно быть 8 уникальных цветов");
  }

  return result;
}

/**
 * Возвращает места цветов в порядке предпочтения:
 * { red: 1, yellow: 2, ... }
 */
function buildColorPositions(preferenceOrder) {
  const positions = {};

  preferenceOrder.forEach((colorCode, index) => {
    positions[colorCode] = index + 1;
  });

  return positions;
}

/**
 * ВК = (18 – место красного – место синего) / (18 – место синего – место зеленого)
 */
function calculateVegetativeCoefficient(positions) {
  const redPos = positions.red;
  const bluePos = positions.blue;
  const greenPos = positions.green;

  const denominator = 18 - bluePos - greenPos;

  if (denominator === 0) {
    throw new Error("Невозможно вычислить ВК: знаменатель равен нулю");
  }

  return Number(((18 - redPos - bluePos) / denominator).toFixed(2));
}

/**
 * Интерпретация ВК
 */
function interpretVegetativeCoefficient(vk) {
  if (vk >= 0 && vk <= 0.5) {
    return {
      level: "critical_fatigue",
      title: "Хроническое переутомление",
      interpretation: "Истощение, низкая работоспособность. Нагрузки непосильны для ребенка."
    };
  }

  if (vk >= 0.51 && vk <= 0.91) {
    return {
      level: "compensated_fatigue",
      title: "Компенсируемое состояние усталости",
      interpretation: "Самовосстановление оптимальной работоспособности происходит за счет периодического снижения активности. Необходима оптимизация рабочего ритма, режима труда и отдыха."
    };
  }

  if (vk >= 0.92 && vk < 2) {
    return {
      level: "optimal",
      title: "Оптимальная работоспособность",
      interpretation: "Ребенок отличается бодростью, здоровой активностью, готовностью к энергозатратам. Нагрузки соответствуют возможностям. Образ жизни позволяет ребенку восстанавливать затраченную энергию."
    };
  }

  return {
    level: "overexcitation",
    title: "Перевозбуждение",
    interpretation: "Чаще является результатом работы ребенка на пределе своих возможностей, что приводит к быстрому истощению. Требуется нормализация темпа деятельности, режима труда и отдыха, а иногда и снижение нагрузки."
  };
}

/**
 * Рассчитывает суммарное отклонение от аутогенной нормы
 */
function calculateTotalDeviation(preferenceOrder) {
  let total = 0;

  AUTOGENIC_NORM.forEach((colorCode, index) => {
    const actualPosition = preferenceOrder.indexOf(colorCode) + 1;
    const normPosition = index + 1;
    total += Math.abs(actualPosition - normPosition);
  });

  return total;
}

/**
 * Интерпретация суммарного отклонения
 */
function interpretTotalDeviation(totalDeviation) {
  if (totalDeviation > 20) {
    return {
      level: "negative_background",
      title: "Преобладание отрицательных эмоций",
      interpretation: "У ребенка доминируют плохое настроение и неприятные переживания. Имеются проблемы, которые ребенок не может решить самостоятельно."
    };
  }

  if (totalDeviation >= 10 && totalDeviation <= 18) {
    return {
      level: "normal_background",
      title: "Эмоциональное состояние в норме",
      interpretation: "Ребенок может радоваться и печалиться, поводов для беспокойства нет."
    };
  }

  if (totalDeviation >= 19 && totalDeviation <= 20) {
    return {
      level: "borderline_background",
      title: "Пограничный эмоциональный фон",
      interpretation:
        "Показатель находится между нормативным диапазоном и зоной преобладания отрицательных эмоций; по описанию методики требует дополнительной качественной интерпретации."
    };
  }

  return {
    level: "positive_background",
    title: "Преобладание положительных эмоций",
    interpretation: "Ребенок весел, счастлив, настроен оптимистично."
  };
}

/**
 * Анализ задания №2
 */
function analyzeEmotions(answers, positions) {
  const emotions = {};
  const blocks = [];

  Object.keys(EMOTION_TITLES).forEach((code) => {
    const answer = findAnswerByCode(answers, code);
    const colorCode = getColorValueFromAnswer(answer);

    emotions[code] = {
      code,
      title: EMOTION_TITLES[code],
      color_code: colorCode,
      color_title: COLORS[colorCode].title,
      color_type: COLORS[colorCode].type,
      preference_position: positions[colorCode] || null
    };
  });

  for (const block of EMOTION_BLOCKS) {
    const positiveEmotion = emotions[block.positive];
    const negativeEmotion = emotions[block.negative];

    blocks.push({
      title: block.title,
      positive_emotion: positiveEmotion.title,
      negative_emotion: negativeEmotion.title,
      positive_color: positiveEmotion.color_title,
      negative_color: negativeEmotion.color_title,
      same_color: positiveEmotion.color_code === negativeEmotion.color_code,
      distance_in_preference:
        Math.abs(
          (positiveEmotion.preference_position || 0) -
          (negativeEmotion.preference_position || 0)
        )
    });
  }

  const positiveEmotionCodes = ["happiness", "justice", "friendship", "kindness", "admiration"];
  const negativeEmotionCodes = ["grief", "offense", "quarrel", "malice", "boredom"];

  const positiveMainCount = positiveEmotionCodes.filter((code) =>
    emotions[code].color_type === "base_positive"
  ).length;

  const negativeDarkCount = negativeEmotionCodes.filter((code) =>
    ["negative"].includes(emotions[code].color_type)
  ).length;

  const repeatedPairs = blocks
    .filter((block) => block.same_color)
    .map((block) => block.title);

  const basePositivePositions = BASE_POSITIVE_COLORS
    .map((code) => positions[code])
    .filter((value) => value != null);
  const basePositiveLateCount = basePositivePositions
    .filter((value) => value >= 5)
    .length;
  const hasInvertedGradient = basePositiveLateCount >= 3;

  let summary = null;

  if (repeatedPairs.length > 0) {
    summary =
      "Есть признаки недостаточной дифференциации социальных эмоций: некоторые парные категории окрашены одинаково.";
  } else if (hasInvertedGradient) {
    summary =
      "Есть признаки инверсии цветового градусника: основные цвета занимают поздние позиции, поэтому интерпретация социальных эмоций требует осторожности.";
  } else if (positiveMainCount >= 4 && negativeDarkCount >= 3) {
    summary =
      "Дифференциация социальных эмоций выглядит сохранной: позитивные чувства чаще окрашены основными цветами, негативные — темными.";
  } else {
    summary =
      "Дифференциация социальных эмоций частично сохранна, но есть неоднозначные ассоциации, требующие качественной интерпретации.";
  }

  return {
    emotions: Object.values(emotions),
    blocks,
    differentiation: {
      positive_main_color_count: positiveMainCount,
      negative_dark_color_count: negativeDarkCount,
      base_positive_late_count: basePositiveLateCount,
      has_inverted_gradient: hasInvertedGradient,
      repeated_pairs: repeatedPairs,
      summary
    }
  };
}

/**
 * Классификация отношения по цвету
 */
function getRelationByColor(colorCode) {
  const color = COLORS[colorCode];

  if (!color) {
    throw new Error(`Неизвестный цвет: ${colorCode}`);
  }

  if (color.type === "base_positive") return "positive";
  if (color.type === "negative") return "negative";
  return "ambivalent";
}

/**
 * Человекочитаемая подпись отношения
 */
function getRelationLabel(relation) {
  if (relation === "positive") return "положительное";
  if (relation === "negative") return "негативное";
  return "амбивалентное";
}

function getAttentionStatusByColor(colorCode) {
  if (["gray", "brown", "black"].includes(colorCode)) {
    return {
      value: "attention",
      label: "Обратить внимание"
    };
  }

  return {
    value: "ok",
    label: "Отклонений нет"
  };
}

function getEmotionalBackgroundLabel(totalDeviation) {
  if (totalDeviation > 20) return "отрицательный";
  if (totalDeviation >= 10 && totalDeviation <= 18) return "нормальный";
  if (totalDeviation >= 19 && totalDeviation <= 20) return "пограничный";
  return "положительный";
}

function calculateSelfEsteem(preferenceOrder) {
  const firstColor = preferenceOrder[0];

  if (BASE_POSITIVE_COLORS.includes(firstColor)) {
    return {
      value: "positive",
      label: "Положительная"
    };
  }

  if (firstColor === "violet") {
    return {
      value: "infantile",
      label: "Инфантильная"
    };
  }

  if (NEGATIVE_COLORS.includes(firstColor) || firstColor === "gray") {
    return {
      value: "negative",
      label: "Отрицательная"
    };
  }

  return {
    value: "unknown",
    label: "Не определена"
  };
}

function summarizeRelations(items) {
  const positiveCount = items.filter((item) => item.relation === "positive").length;
  const negativeCount = items.filter((item) => item.relation === "negative").length;
  const ambivalentCount = items.filter((item) => item.relation === "ambivalent").length;

  let value = "ambivalent";

  if (items.length === 1) {
    value = items[0].relation;
  } else if (negativeCount > 0 && positiveCount === 0 && ambivalentCount === 0) {
    value = "negative";
  } else if (positiveCount > 0 && negativeCount === 0 && ambivalentCount === 0) {
    value = "positive";
  } else if (negativeCount >= Math.ceil(items.length / 2) && positiveCount === 0) {
    value = "negative";
  } else if (
    positiveCount >= Math.ceil(items.length / 2) &&
    negativeCount === 0 &&
    ambivalentCount <= 1
  ) {
    value = "positive";
  }

  return {
    value,
    label: getRelationLabel(value),
    counts: {
      positive: positiveCount,
      negative: negativeCount,
      ambivalent: ambivalentCount
    }
  };
}

function getDomainInterpretation(domainCode, relation) {
  const domainTitles = {
    self: "к себе",
    learning: "к учебной деятельности",
    teacher: "к учителю",
    classmates: "к одноклассникам",
    school: "к школьной жизни"
  };

  const target = domainTitles[domainCode] || "к рассматриваемой сфере";

  if (relation === "positive") {
    return `Эмоциональное отношение ${target} выглядит положительным.`;
  }

  if (relation === "negative") {
    return `Есть признаки негативного эмоционального отношения ${target}.`;
  }

  return `Эмоциональное отношение ${target} выглядит смешанным и требует дополнительного анализа.`;
}

function buildCompactDomainStatuses(houses, customHouseDescription) {
  const houseByCode = Object.fromEntries(houses.map((item) => [item.code, item]));
  const definitions = [
    { code: "soul", title: "Душа" },
    { code: "school_way", title: "Идти в школу" },
    { code: "reading_lesson", title: "Урок литературы" },
    { code: "writing_lesson", title: "Урок письма" },
    { code: "math_lesson", title: "Урок математики" },
    { code: "teacher_talk", title: "Отношения с учителями" },
    { code: "classmates", title: "Отношения с одноклассниками" },
    { code: "home", title: "Отношение дома" },
    { code: "homework", title: "Делать уроки" },
    { code: "custom_house", title: "Придумай сам" }
  ];

  const items = definitions
    .map(({ code, title }) => {
      const house = houseByCode[code];

      if (!house) {
        return null;
      }

      const status = getAttentionStatusByColor(house.color_code);

      const item = {
        code,
        title,
        status: status.value,
        status_label: status.label,
        color_code: house.color_code,
        color_title: house.color_title
      };

      if (code === "custom_house") {
        item.description = customHouseDescription;
      }

      return item;
    })
    .filter(Boolean);

  return { items };
}

/**
 * Анализ задания №3
 */
function analyzeHouses(answers) {
  const houseCodes = [
    "soul",
    "school_way",
    "reading_lesson",
    "writing_lesson",
    "math_lesson",
    "teacher_talk",
    "classmates",
    "home",
    "homework",
    "custom_house"
  ];

  const houses = houseCodes.map((code) => {
    const answer = findAnswerByCode(answers, code);
    const colorCode = getColorValueFromAnswer(answer);
    const relation = getRelationByColor(colorCode);

    return {
      code,
      title: HOUSE_TITLES[code],
      color_code: colorCode,
      color_title: COLORS[colorCode].title,
      relation,
      relation_label: getRelationLabel(relation)
    };
  });

  const schoolRelations = houses
    .filter((item) => SCHOOL_RELATED_CODES.includes(item.code));
  const schoolRelation = summarizeRelations(schoolRelations);

  return {
    houses,
    school_relation: {
      ...schoolRelation,
      interpretation: getDomainInterpretation("school", schoolRelation.value)
    },
    counts: schoolRelation.counts
  };
}

/**
 * Основная функция расчёта результата диагностики
 */
function calculateDomikiResult(data) {
  if (!data || typeof data !== "object") {
    throw new Error("Не переданы данные для расчёта");
  }

  if (!data.student) {
    throw new Error("Отсутствуют данные student");
  }

  if (!Array.isArray(data.answers) || !data.answers.length) {
    throw new Error("Отсутствуют ответы");
  }

  const rankingAnswer = findAnswerByCode(data.answers, "color_preference");
  const preferenceOrder = getPreferenceOrder(rankingAnswer);
  const positions = buildColorPositions(preferenceOrder);

  const vk = calculateVegetativeCoefficient(positions);
  const totalDeviation = calculateTotalDeviation(preferenceOrder);
  const selfEsteem = calculateSelfEsteem(preferenceOrder);

  const vkInterpretation = interpretVegetativeCoefficient(vk);
  const totalDeviationInterpretation = interpretTotalDeviation(totalDeviation);

  const houses = analyzeHouses(data.answers);
  const customHouseDescription = getTextValueFromAnswer(
    findAnswerByCode(data.answers, "custom_house_description")
  );
  const domainStatuses = buildCompactDomainStatuses(houses.houses, customHouseDescription);

  return {
    attempt: {
      id: data.attempt_id,
      submitted_at: data.submitted_at || null
    },
    test: {
      id: data.test_id || null,
      code: data.test_code || null,
      title: data.test_title || null
    },
    student: {
      id: data.student.id || null,
      name: data.student.name || null,
      birth_date: data.student.birth_date || null,
      age: data.student.age || null,
      gender: data.student.gender || null,
      gender_value: data.student.gender_value || null
    },
    result: {
      calculated_at: new Date().toISOString(),
      vegetative_coefficient: {
        value: vk,
        level: vkInterpretation.level,
        label: vkInterpretation.title,
        interpretation: vkInterpretation.interpretation
      },
      emotional_background: {
        value: totalDeviation,
        level: totalDeviationInterpretation.level,
        label: getEmotionalBackgroundLabel(totalDeviation),
        title: totalDeviationInterpretation.title,
        interpretation: totalDeviationInterpretation.interpretation
      },
      self_esteem: selfEsteem,
      school_relation: {
        value: houses.school_relation.value,
        label: houses.school_relation.label,
        interpretation: houses.school_relation.interpretation
      }
    },
    domains: domainStatuses.items
  };
}

// Экспортируем функцию для использования в других модулях
const result = calculateDomikiResult(data);

// Выводим результат в консоль (можно заменить на return для использования в API)
return {
  status: "calculated",
  json: result
};
