import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

function getAvailableScriptNames(scriptsRoot) {
	return fs
		.readdirSync(scriptsRoot, { withFileTypes: true })
		.filter((entry) => entry.isDirectory())
		.map((entry) => entry.name)
		.filter((name) => fs.existsSync(path.join(scriptsRoot, name, "script.js")))
		.sort();
}

function resolveScriptDirectory(scriptsRoot, scriptName) {
	const availableScripts = getAvailableScriptNames(scriptsRoot);

	if (!scriptName) {
		throw new Error(
			`Не указана папка со скриптом. Использование: node scripts/calculate.js <script-name> [data-file]\nДоступные скрипты: ${availableScripts.join(", ")}`
		);
	}

	if (scriptName.includes("/") || scriptName.includes("\\")) {
		throw new Error("Нужно передать только имя папки внутри scripts, без вложенных путей");
	}

	if (!availableScripts.includes(scriptName)) {
		throw new Error(
			`Скрипт "${scriptName}" не найден. Доступные скрипты: ${availableScripts.join(", ")}`
		);
	}

	return path.join(scriptsRoot, scriptName);
}

function resolveDataPath(scriptDirectory, dataFile) {
	// Если указан конкретный файл — ищем в подпапке data/
	if (dataFile) {
		const dataPath = path.join(scriptDirectory, "data", dataFile);
		if (!fs.existsSync(dataPath)) {
			const available = getAvailableDataFiles(scriptDirectory);
			throw new Error(
				`Файл данных "${dataFile}" не найден в папке data/.\nДоступные файлы:\n${available.map((f) => `  ${f}`).join("\n")}`
			);
		}
		return dataPath;
	}

	// Иначе пробуем data.json рядом со скриптом (обратная совместимость)
	const legacyPath = path.join(scriptDirectory, "data.json");
	if (fs.existsSync(legacyPath)) {
		return legacyPath;
	}

	// Если есть папка data/ — подсказываем список файлов
	const available = getAvailableDataFiles(scriptDirectory);
	if (available.length > 0) {
		throw new Error(
			`Файл data.json не найден. Укажите файл из папки data/:\n${available.map((f) => `  node scripts/calculate.js ${path.basename(scriptDirectory)} ${f}`).join("\n")}`
		);
	}

	throw new Error(`В папке "${path.basename(scriptDirectory)}" не найден файл данных`);
}

function getAvailableDataFiles(scriptDirectory) {
	const dataDir = path.join(scriptDirectory, "data");
	if (!fs.existsSync(dataDir)) return [];
	return fs
		.readdirSync(dataDir)
		.filter((f) => f.endsWith(".json"))
		.sort();
}

function loadInputData(dataPath) {
	const raw = fs.readFileSync(dataPath, "utf-8");
	const apiData = JSON.parse(raw);

	return {
		...apiData,
		student: {
			...apiData.student,
			name: apiData.student?.name ?? apiData.student?.full_name ?? null
		}
	};
}

function runScript(scriptPath, data) {
	const source = fs.readFileSync(scriptPath, "utf-8");
	const executeScript = new Function("data", source);

	return executeScript(data);
}

// Чтение данных из файлов
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const scriptName = process.argv[2];
const dataFile = process.argv[3] || null;
const scriptDirectory = resolveScriptDirectory(__dirname, scriptName);
const dataPath = resolveDataPath(scriptDirectory, dataFile);
const scriptPath = path.join(scriptDirectory, "script.js");

const inputData = loadInputData(dataPath);

// Вывод информации о запуске
console.log(`=== Файл данных: ${path.relative(__dirname, dataPath)} ===`);

// Выполнение расчёта
const result = runScript(scriptPath, inputData);

// Вывод результата
console.log("=== Результат диагностики ===");
console.log(JSON.stringify(result, null, 2));
