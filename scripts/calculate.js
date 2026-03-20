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
			`Не указана папка со скриптом. Использование: node scripts/calculate.js <script-name>\nДоступные скрипты: ${availableScripts.join(", ")}`
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
const scriptDirectory = resolveScriptDirectory(__dirname, scriptName);
const dataPath = path.join(scriptDirectory, "data.json");
const scriptPath = path.join(scriptDirectory, "script.js");

if (!fs.existsSync(dataPath)) {
	throw new Error(`В папке "${scriptName}" не найден файл data.json`);
}

const inputData = loadInputData(dataPath);

// Выполнение расчёта
const result = runScript(scriptPath, inputData);

// Вывод результата
console.log("=== Результат диагностики ===");
console.log(JSON.stringify(result, null, 2));
