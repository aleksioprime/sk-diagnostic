"""Скрипты расчёта на JavaScript. Выполняются в отдельном движке V8: без файлов, сети и окружения приложения."""

import json
import re
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from py_mini_racer import JSEvalException, JSOOMException, JSTimeoutException, MiniRacer

from app.scoring.common import ScoringError

TIMEOUT_SECONDS = 2
MAX_MEMORY_BYTES = 128 * 1024 * 1024
MAX_OUTPUT_BYTES = 1024 * 1024
MAX_LOG_LINES = 200
MAX_LOG_LINE = 2000
# Столько строк обёртки стоит перед скриптом: номера строк в ошибках считаем от начала скрипта
WRAPPER_LINES = 2

PRELUDE = """
const __logs = [];
const __print = (value) => {
  if (typeof value === 'string') return value;
  try { return JSON.stringify(value) ?? String(value); } catch { return String(value); }
};
const __console = Object.fromEntries(['log', 'info', 'warn', 'error', 'debug'].map((level) => [level, (...args) => {
  if (__logs.length < MAX_LOG_LINES) __logs.push(args.map(__print).join(' ').slice(0, MAX_LOG_LINE));
}]));
""".replace('MAX_LOG_LINES', str(MAX_LOG_LINES)).replace('MAX_LOG_LINE', str(MAX_LOG_LINE))

RUN = """
(() => {
  const data = JSON.parse(INPUT);
  let result;
  try {
    result = __script(data, __console);
  } catch (error) {
    const place = /<anonymous>:(\\d+):(\\d+)/.exec(error?.stack || '');
    return JSON.stringify({
      error: error instanceof Error ? `${error.name}: ${error.message}` : __print(error),
      line: place ? Number(place[1]) - __offset : null,
      logs: __logs,
    });
  }
  return JSON.stringify({ result: result === undefined ? null : result, logs: __logs });
})()
"""


@dataclass
class ScriptRun:
    """Итог запуска. Ошибка скрипта — обычный итог: её показывают автору, а не прячут."""

    output: dict | None = None
    error: str | None = None
    line: int | None = None
    logs: list[str] = field(default_factory=list)
    duration_ms: int = 0


def _parse_error(exc: Exception) -> tuple[str, int | None]:
    """Из сообщения V8 — суть и номер строки в скрипте."""
    text = str(exc)
    place = re.search(r'<anonymous>:(\d+)', text)
    line = int(place.group(1)) - WRAPPER_LINES if place else None
    summary = next((row.strip() for row in text.splitlines() if 'Error' in row), text.strip())
    summary = re.sub(r'^<anonymous>:\d+:?\s*', '', summary)
    return summary[:500], line


def _unwrap(result: Any) -> tuple[dict | None, str | None]:
    """Результат — объект. Формат скриптов NocoBase {status, json} принимается как есть."""
    if isinstance(result, dict) and 'json' in result and 'status' in result:
        if result['status'] == 'error':
            return None, str(result.get('error') or result.get('json') or 'Скрипт вернул ошибку')
        result = result['json']
    if isinstance(result, dict) and not result:
        return None, 'Скрипт вернул пустой объект (async-функции не поддерживаются)'
    if not isinstance(result, dict):
        return None, 'Скрипт должен вернуть объект: return { ... }'
    return result, None


def run_script(script: str, data: dict) -> ScriptRun:
    """Запустить скрипт: на входе переменная data, на выходе то, что он вернул через return."""
    started = perf_counter()
    run = ScriptRun()
    with MiniRacer() as engine:
        try:
            engine.eval(PRELUDE)
            limits = {'timeout_sec': TIMEOUT_SECONDS, 'max_memory': MAX_MEMORY_BYTES}
            head = f'const __offset = {WRAPPER_LINES};\nconst __script = (function (data, console) {{'
            wrapped = f'{head}\n{script}\n}});'
            engine.eval(wrapped, **limits)
            raw = engine.eval(RUN.replace('INPUT', json.dumps(json.dumps(data))), **limits)
        except JSTimeoutException:
            run.error = f'Скрипт выполнялся дольше {TIMEOUT_SECONDS} с и был остановлен'
        except JSOOMException:
            run.error = 'Скрипту не хватило памяти'
        except JSEvalException as exc:
            run.error, run.line = _parse_error(exc)
        else:
            if len(raw) > MAX_OUTPUT_BYTES:
                run.error = 'Результат скрипта слишком большой (больше 1 МБ)'
            else:
                payload = json.loads(raw)
                run.logs = payload.get('logs') or []
                if payload.get('error'):
                    run.error, run.line = payload['error'][:500], payload.get('line')
                else:
                    run.output, run.error = _unwrap(payload.get('result'))
    run.duration_ms = round((perf_counter() - started) * 1000)
    return run


def calculate(script: str, data: dict) -> dict:
    """Расчёт отправленной попытки: ошибка скрипта становится ошибкой результата."""
    run = run_script(script, data)
    if run.error:
        place = f' (строка {run.line})' if run.line else ''
        raise ScoringError(f'Ошибка скрипта расчёта{place}: {run.error}')
    return run.output
