/**
 * Цветовой тест отношений (ЦТО) — 7 класс
 * Код теста: domiki_emotion_middle
 *
 * Логика идентична методике «Домики» (domiki_emotion_primary),
 * адаптирована для 7-го класса: расширен перечень домиков (задание №3).
 */

/**
 * Справочник цветов методики
 */
const COLORS = {
  blue:   { code: "blue",   number: 1, title: "Синий",       type: "base_positive" },
  green:  { code: "green",  number: 2, title: "Зеленый",     type: "base_positive" },
  red:    { code: "red",    number: 3, title: "Красный",     type: "base_positive" },
  yellow: { code: "yellow", number: 4, title: "Желтый",      type: "base_positive" },
  violet: { code: "violet", number: 5, title: "Фиолетовый",  type: "ambivalent"    },
  brown:  { code: "brown",  number: 6, title: "Коричневый",  type: "negative"      },
  gray:   { code: "gray",   number: 7, title: "Серый",       type: "neutral"       },
  black:  { code: "black",  number: 8, title: "Черный",      type: "negative"      },
};

/**
 * Аутогенная норма (34251607):
 * 3-красный, 4-желтый, 2-зеленый, 5-фиолетовый,
 * 1-синий, 6-коричневый, 0-серый, 7-черный
 */
const AUTOGENIC_NORM = ["red", "yellow", "green", "violet", "blue", "brown", "gray", "black"];

/**
 * Блоки социальных эмоций (задание №2 — одинаково для всех возрастов)
 */
const EMOTION_BLOCKS = [
  { title: "Блок базового комфорта",              positive: "happiness",  negative: "grief"     },
  { title: "Блок личностного роста",              positive: "justice",    negative: "offense"   },
  { title: "Блок межличностного взаимодействия",  positive: "friendship", negative: "quarrel"   },
  { title: "Блок потенциальной агрессии",         positive: "kindness",   negative: "malice"    },
  { title: "Блок познания",                       positive: "admiration", negative: "boredom"   },
];

const EMOTION_TITLES = {
  happiness: "Счастье",
  grief:     "Горе",
  justice:   "Справедливость",
  offense:   "Обида",
  friendship:"Дружба",
  quarrel:   "Ссора",
  kindness:  "Доброта",
  malice:    "Злоба",
  boredom:   "Скука",
  admiration:"Восхищение",
};

/**
 * Домики для 7 класса (задание №3)
 */
const HOUSE_TITLES = {
  soul:             "Твоя душа",
  school:           "Настроение в школе",
  home:             "Настроение дома",
  literature:       "Урок русского языка и литературы",
  english:          "Урок английского языка",
  mathematics:      "Урок математики",
  history:          "Урок истории",
  technology:       "Урок технологии",
  physical_culture: "Урок физкультуры",
  biology:          "Урок биологии",
  physics:          "Урок физики",
  arts:             "Урок ИЗО",
  test:             "Контрольные и проверочные работы",
  board:            "Ответ у доски",
  mentor:           "Общение с наставником",
  classmates:       "Общение с одноклассниками",
  homework:         "Выполнение домашних заданий",
};

/**
 * Коды демо-вопросов, которые не учитываются в расчётах
 * (но отображаются в тесте и передаются в ответах)
 */
const DEMO_QUESTION_CODES = [
  "color_ranking_demo",
];

/**
 * Домики, учитываемые при расчёте «отношения к школе»
 */
const SCHOOL_RELATED_CODES = [
  "school",
  "literature",
  "english",
  "mathematics",
  "history",
  "technology",
  "physical_culture",
  "biology",
  "physics",
  "arts",
  "test",
  "board",
  "mentor",
  "classmates",
  "homework",
];

const BASE_POSITIVE_COLORS = ["blue", "green", "red", "yellow"];
const NEGATIVE_COLORS      = ["brown", "black"];

// ---------------------------------------------------------------------------
// Вспомогательные функции
// ---------------------------------------------------------------------------

function findAnswerByCode(answers = [], code) {
  return answers.find((item) => item.question_code === code) || null;
}

function getColorValueFromAnswer(answer) {
  if (!answer) throw new Error("Ответ не найден");

  const candidates = [
    answer.value,
    answer.scale_option?.value,
    answer.selected_option?.value,
  ];

  for (const candidate of candidates) {
    if (typeof candidate === "string" && COLORS[candidate]) {
      return candidate;
    }
  }

  throw new Error(`Не удалось определить цвет для question_code=${answer.question_code}`);
}

function getPreferenceOrder(answer) {
  if (!answer) throw new Error("Не найден ответ задания №1");
  if (!Array.isArray(answer.ranking) || !answer.ranking.length) {
    throw new Error("В ответе задания №1 отсутствует ranking");
  }

  const sorted = [...answer.ranking].sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999));
  const result = sorted.map((item) => {
    if (!COLORS[item.option_value]) throw new Error(`Некорректный цвет в ranking: ${item.option_value}`);
    return item.option_value;
  });

  if (new Set(result).size !== 8) throw new Error("В задании №1 должно быть 8 уникальных цветов");
  return result;
}

function buildColorPositions(preferenceOrder) {
  const positions = {};
  preferenceOrder.forEach((colorCode, index) => { positions[colorCode] = index + 1; });
  return positions;
}

// ---------------------------------------------------------------------------
// Вегетативный коэффициент
// ---------------------------------------------------------------------------

function calculateVegetativeCoefficient(positions) {
  const denominator = 18 - positions.blue - positions.green;
  if (denominator === 0) throw new Error("Невозможно вычислить ВК: знаменатель равен нулю");
  return Number(((18 - positions.red - positions.blue) / denominator).toFixed(2));
}

function interpretVegetativeCoefficient(vk) {
  if (vk >= 0 && vk <= 0.5)    return { level: "critical_fatigue",    title: "Хроническое переутомление",              interpretation: "Истощение, низкая работоспособность. Нагрузки непосильны для ребенка." };
  if (vk >= 0.51 && vk <= 0.91) return { level: "compensated_fatigue", title: "Компенсируемое состояние усталости",     interpretation: "Самовосстановление оптимальной работоспособности происходит за счет периодического снижения активности. Необходима оптимизация рабочего ритма, режима труда и отдыха." };
  if (vk >= 0.92 && vk < 2)     return { level: "optimal",             title: "Оптимальная работоспособность",          interpretation: "Ребенок отличается бодростью, здоровой активностью, готовностью к энергозатратам. Нагрузки соответствуют возможностям. Образ жизни позволяет ребенку восстанавливать затраченную энергию." };
  return                                { level: "overexcitation",      title: "Перевозбуждение",                        interpretation: "Чаще является результатом работы ребенка на пределе своих возможностей, что приводит к быстрому истощению. Требуется нормализация темпа деятельности, режима труда и отдыха, а иногда и снижение нагрузки." };
}

// ---------------------------------------------------------------------------
// Суммарное отклонение от аутогенной нормы
// ---------------------------------------------------------------------------

function calculateTotalDeviation(preferenceOrder) {
  return AUTOGENIC_NORM.reduce((total, colorCode, index) => {
    return total + Math.abs(preferenceOrder.indexOf(colorCode) + 1 - (index + 1));
  }, 0);
}

function interpretTotalDeviation(totalDeviation) {
  if (totalDeviation > 20)                          return { level: "negative_background",  title: "Преобладание отрицательных эмоций",  interpretation: "У ребенка доминируют плохое настроение и неприятные переживания. Имеются проблемы, которые ребенок не может решить самостоятельно." };
  if (totalDeviation >= 19 && totalDeviation <= 20) return { level: "borderline_background", title: "Пограничный эмоциональный фон",       interpretation: "Показатель находится между нормативным диапазоном и зоной преобладания отрицательных эмоций; требует дополнительной качественной интерпретации." };
  if (totalDeviation >= 10 && totalDeviation <= 18) return { level: "normal_background",     title: "Эмоциональное состояние в норме",     interpretation: "Ребенок может радоваться и печалиться, поводов для беспокойства нет." };
  return                                            { level: "positive_background",  title: "Преобладание положительных эмоций",  interpretation: "Ребенок весел, счастлив, настроен оптимистично." };
}

function getEmotionalBackgroundLabel(d) {
  if (d > 20)                       return "отрицательный";
  if (d >= 19 && d <= 20)           return "пограничный";
  if (d >= 10 && d <= 18)           return "нормальный";
  return                                   "положительный";
}

// ---------------------------------------------------------------------------
// Самооценка
// ---------------------------------------------------------------------------

function calculateSelfEsteem(preferenceOrder) {
  const first = preferenceOrder[0];
  if (BASE_POSITIVE_COLORS.includes(first))                  return { value: "positive",   label: "Положительная" };
  if (first === "violet")                                     return { value: "infantile",  label: "Инфантильная"  };
  if (NEGATIVE_COLORS.includes(first) || first === "gray")   return { value: "negative",   label: "Отрицательная" };
  return                                                             { value: "unknown",    label: "Не определена" };
}

// ---------------------------------------------------------------------------
// Анализ задания №2 — социальные эмоции
// ---------------------------------------------------------------------------

function analyzeEmotions(answers, positions) {
  const emotions = {};
  Object.keys(EMOTION_TITLES).forEach((code) => {
    const answer    = findAnswerByCode(answers, code);
    const colorCode = getColorValueFromAnswer(answer);
    emotions[code]  = {
      code,
      title:               EMOTION_TITLES[code],
      color_code:          colorCode,
      color_title:         COLORS[colorCode].title,
      color_type:          COLORS[colorCode].type,
      preference_position: positions[colorCode] || null,
    };
  });

  const blocks = EMOTION_BLOCKS.map((block) => {
    const pos = emotions[block.positive];
    const neg = emotions[block.negative];
    return {
      title:                   block.title,
      positive_emotion:        pos.title,
      negative_emotion:        neg.title,
      positive_color:          pos.color_title,
      negative_color:          neg.color_title,
      same_color:              pos.color_code === neg.color_code,
      distance_in_preference:  Math.abs((pos.preference_position || 0) - (neg.preference_position || 0)),
    };
  });

  const positiveEmotionCodes = ["happiness", "justice", "friendship", "kindness", "admiration"];
  const negativeEmotionCodes = ["grief",     "offense", "quarrel",   "malice",   "boredom"   ];

  const positiveMainCount  = positiveEmotionCodes.filter((c) => emotions[c].color_type === "base_positive").length;
  const negativeDarkCount  = negativeEmotionCodes.filter((c) => emotions[c].color_type === "negative").length;
  const repeatedPairs      = blocks.filter((b) => b.same_color).map((b) => b.title);

  const basePositiveLateCount = BASE_POSITIVE_COLORS.map((c) => positions[c]).filter((p) => p >= 5).length;
  const hasInvertedGradient   = basePositiveLateCount >= 3;

  let summary;
  if (repeatedPairs.length > 0) {
    summary = "Есть признаки недостаточной дифференциации социальных эмоций: некоторые парные категории окрашены одинаково.";
  } else if (hasInvertedGradient) {
    summary = "Есть признаки инверсии цветового градусника: основные цвета занимают поздние позиции, поэтому интерпретация социальных эмоций требует осторожности.";
  } else if (positiveMainCount >= 4 && negativeDarkCount >= 3) {
    summary = "Дифференциация социальных эмоций выглядит сохранной: позитивные чувства чаще окрашены основными цветами, негативные — тёмными.";
  } else {
    summary = "Дифференциация социальных эмоций частично сохранна, но есть неоднозначные ассоциации, требующие качественной интерпретации.";
  }

  return {
    emotions: Object.values(emotions),
    blocks,
    differentiation: {
      positive_main_color_count: positiveMainCount,
      negative_dark_color_count: negativeDarkCount,
      base_positive_late_count:  basePositiveLateCount,
      has_inverted_gradient:     hasInvertedGradient,
      repeated_pairs:            repeatedPairs,
      summary,
    },
  };
}

// ---------------------------------------------------------------------------
// Анализ задания №3 — домики
// ---------------------------------------------------------------------------

function getRelationByColor(colorCode) {
  const color = COLORS[colorCode];
  if (!color) throw new Error(`Неизвестный цвет: ${colorCode}`);
  if (color.type === "base_positive") return "positive";
  if (color.type === "negative")      return "negative";
  return "ambivalent";
}

function getRelationLabel(relation) {
  if (relation === "positive") return "положительное";
  if (relation === "negative") return "негативное";
  return "амбивалентное";
}

function getAttentionStatusByColor(colorCode) {
  if (["gray", "brown", "black"].includes(colorCode)) return { value: "attention", label: "Обратить внимание" };
  return { value: "ok", label: "Отклонений нет" };
}

function summarizeRelations(items) {
  const positiveCount  = items.filter((i) => i.relation === "positive").length;
  const negativeCount  = items.filter((i) => i.relation === "negative").length;
  const ambivalentCount = items.filter((i) => i.relation === "ambivalent").length;

  let value = "ambivalent";
  if (items.length === 1) {
    value = items[0].relation;
  } else if (negativeCount > 0 && positiveCount === 0 && ambivalentCount === 0) {
    value = "negative";
  } else if (positiveCount > 0 && negativeCount === 0 && ambivalentCount === 0) {
    value = "positive";
  } else if (negativeCount >= Math.ceil(items.length / 2) && positiveCount === 0) {
    value = "negative";
  } else if (positiveCount >= Math.ceil(items.length / 2) && negativeCount === 0 && ambivalentCount <= 1) {
    value = "positive";
  }

  return { value, label: getRelationLabel(value), counts: { positive: positiveCount, negative: negativeCount, ambivalent: ambivalentCount } };
}

function analyzeHouses(answers) {
  const houseCodes = Object.keys(HOUSE_TITLES).filter(
    (code) => !DEMO_QUESTION_CODES.includes(code)
  );

  const houses = houseCodes.map((code) => {
    const answer    = findAnswerByCode(answers, code);
    const colorCode = getColorValueFromAnswer(answer);
    const relation  = getRelationByColor(colorCode);
    return {
      code,
      title:          HOUSE_TITLES[code],
      color_code:     colorCode,
      color_title:    COLORS[colorCode].title,
      relation,
      relation_label: getRelationLabel(relation),
    };
  });

  const schoolItems   = houses.filter((h) => SCHOOL_RELATED_CODES.includes(h.code));
  const schoolRelation = summarizeRelations(schoolItems);

  const schoolInterpretation =
    schoolRelation.value === "positive" ? "Эмоциональное отношение к школьной жизни выглядит положительным."  :
    schoolRelation.value === "negative" ? "Есть признаки негативного эмоционального отношения к школьной жизни." :
    "Эмоциональное отношение к школьной жизни выглядит смешанным и требует дополнительного анализа.";

  return {
    houses,
    school_relation: { ...schoolRelation, interpretation: schoolInterpretation },
    counts: schoolRelation.counts,
  };
}

function buildDomainStatuses(houses) {
  return houses.map((house) => {
    const status = getAttentionStatusByColor(house.color_code);
    return {
      code:         house.code,
      title:        house.title,
      status:       status.value,
      status_label: status.label,
      color_code:   house.color_code,
      color_title:  house.color_title,
    };
  });
}

// ---------------------------------------------------------------------------
// Основная функция расчёта
// ---------------------------------------------------------------------------

function calculateResult(data) {
  if (!data || typeof data !== "object") throw new Error("Не переданы данные для расчёта");
  if (!data.student)                     throw new Error("Отсутствуют данные student");
  if (!Array.isArray(data.answers) || !data.answers.length) throw new Error("Отсутствуют ответы");

  const rankingAnswer  = findAnswerByCode(data.answers, "color_preference");
  const preferenceOrder = getPreferenceOrder(rankingAnswer);
  const positions      = buildColorPositions(preferenceOrder);

  const vk             = calculateVegetativeCoefficient(positions);
  const totalDeviation = calculateTotalDeviation(preferenceOrder);
  const selfEsteem     = calculateSelfEsteem(preferenceOrder);
  const vkInterp       = interpretVegetativeCoefficient(vk);
  const tdInterp       = interpretTotalDeviation(totalDeviation);

  const housesResult   = analyzeHouses(data.answers);
  const domainStatuses = buildDomainStatuses(housesResult.houses);

  return {
    attempt: {
      id:           data.attempt_id,
      submitted_at: data.submitted_at || null,
    },
    test: {
      id:    data.test_id    || null,
      code:  data.test_code  || null,
      title: data.test_title || null,
    },
    student: {
      id:           data.student.id           || null,
      name:         data.student.name         || null,
      birth_date:   data.student.birth_date   || null,
      age:          data.student.age          || null,
      gender:       data.student.gender       || null,
      gender_value: data.student.gender_value || null,
    },
    result: {
      calculated_at: new Date().toISOString(),
      vegetative_coefficient: {
        value:          vk,
        level:          vkInterp.level,
        label:          vkInterp.title,
        interpretation: vkInterp.interpretation,
      },
      emotional_background: {
        value:          totalDeviation,
        level:          tdInterp.level,
        label:          getEmotionalBackgroundLabel(totalDeviation),
        title:          tdInterp.title,
        interpretation: tdInterp.interpretation,
      },
      self_esteem:    selfEsteem,
      school_relation: {
        value:          housesResult.school_relation.value,
        label:          housesResult.school_relation.label,
        interpretation: housesResult.school_relation.interpretation,
      },
    },
    domains: domainStatuses,
  };
}

const result = calculateResult(data);

return {
  status: "calculated",
  json: result,
};
