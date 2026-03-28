from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .config import settings
from .db_models import (
    AchievementDef,
    ChatMessage,
    CommunityPost,
    Course,
    Lesson,
    LessonAttempt,
    LessonType,
    Module,
    ModuleCompletionReward,
    ParentChildLink,
    ParentLinkRequest,
    QuizOption,
    QuizQuestion,
    RequestStatus,
    SessionToken,
    User,
    UserAchievement,
    UserProgress,
    UserRole,
)
from .security import hash_password

XP_PER_LEVEL = [0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200]

ACHIEVEMENT_SEED = [
    {"code": "first_login", "name": "Первый старт", "description": "Зарегистрировался в Programmer", "icon": "🌟", "rule_json": {"type": "always"}, "xp_reward": 0},
    {"code": "first_lesson", "name": "Первый урок", "description": "Прошёл первый урок", "icon": "📖", "rule_json": {"type": "lessons_completed", "min": 1}, "xp_reward": 0},
    {"code": "quiz_master", "name": "Знаток", "description": "Правильно ответил на 5 вопросов", "icon": "🧠", "rule_json": {"type": "correct_answers", "min": 5}, "xp_reward": 0},
    {"code": "level5", "name": "Пятый уровень", "description": "Достиг 5 уровня", "icon": "🚀", "rule_json": {"type": "level", "min": 5}, "xp_reward": 0},
    {"code": "module_done", "name": "Мастер модуля", "description": "Прошёл целый модуль", "icon": "🏆", "rule_json": {"type": "module_complete", "min": 1}, "xp_reward": 0},
    {"code": "xp100", "name": "100 очков", "description": "Набрал 100 XP", "icon": "⚡", "rule_json": {"type": "xp", "min": 100}, "xp_reward": 0},
]

SEED_COURSE_VERSION = "seed-v4-2026-03-28-expanded-curriculum"

TRACKS = [
    {"track": "python", "emoji": "🐍", "color": "#06d6a0"},
    {"track": "javascript", "emoji": "🟨", "color": "#f7df1e"},
    {"track": "csharp", "emoji": "🟣", "color": "#7b2ff7"},
]


def default_practice_starter(language: str | None) -> str:
    if language == "javascript":
        return "const name = 'Programmer';\nconsole.log(`Привет, ${name}!`);\n"
    if language == "csharp":
        return 'using System;\n\nstring name = "Programmer";\nConsole.WriteLine($"Привет, {name}!");\n'
    return 'name = "Programmer"\nprint(f"Привет, {name}!")\n'


def default_practice_hint(language: str | None) -> str:
    if language == "javascript":
        return "Используй переменные, console.log и базовые конструкции из теории."
    if language == "csharp":
        return "Используй переменные, Console.WriteLine и if/else из теории."
    return "Используй переменные, print и условия из теории."

COURSE_BLUEPRINTS: dict[str, dict[str, Any]] = {
    "python": {
        "title": "Python: от первых строк до мини-проектов",
        "description": "Трек для школьников 8-15 лет: основы, логика, функции и полезные задачи.",
        "modules": [
            {
                "title": "Старт в Python",
                "age_range": "8-10",
                "difficulty": "easy",
                "unlock_xp": 0,
                "xp_reward": 35,
                "description": "Знакомимся с print, переменными и простыми строками.",
                "theory_html": """
<h3>Python для новичков</h3>
<p>Python читается почти как обычный текст. Команда <code>print()</code> выводит сообщения на экран.</p>
<p>Переменная помогает хранить данные: имя, возраст, любимую игру.</p>
<pre>name = "Аня"
age = 9
print(f"Привет, {name}! Тебе {age} лет.")</pre>
""",
                "practice_task": "Сделай приветствие: выведи имя и любимую игру в одном сообщении.",
                "practice_starter": (
                    'name = "Лена"\n'
                    'favorite_game = "Minecraft"\n'
                    'print(f"Привет, {name}! Моя любимая игра — {favorite_game}.")\n'
                ),
                "practice_hint": "Используй переменные и f-строку.",
                "practice_check_mode": "contains_all",
                "practice_check_value": "print,favorite_game",
                "quiz": [
                    {
                        "text": "Что делает команда print()?",
                        "options": [
                            {"text": "Выводит текст на экран", "is_correct": True},
                            {"text": "Удаляет переменную", "is_correct": False},
                            {"text": "Выключает программу", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Как хранить возраст в программе?",
                        "options": [
                            {"text": "В переменной age", "is_correct": True},
                            {"text": "Только в комментарии", "is_correct": False},
                            {"text": "Никак, Python не умеет", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Условия и циклы",
                "age_range": "11-12",
                "difficulty": "medium",
                "unlock_xp": 30,
                "xp_reward": 50,
                "description": "Учимся проверять условия и повторять действия.",
                "theory_html": """
<h3>Логика в Python</h3>
<p>Условие <code>if</code> помогает принимать решения, а цикл <code>for</code> — обрабатывать много значений.</p>
<pre>scores = [4, 6, 8]
total = 0
for score in scores:
    total += score

if total >= 15:
    print("Квест пройден!")</pre>
""",
                "practice_task": "Посчитай сумму очков из списка и выведи: пройден уровень или нет.",
                "practice_starter": (
                    "scores = [5, 7, 8]\n"
                    "total = 0\n\n"
                    "for score in scores:\n"
                    "    total += score\n\n"
                    "if total >= 18:\n"
                    '    print("Уровень пройден!")\n'
                    "else:\n"
                    '    print("Попробуй еще раз")\n'
                ),
                "practice_hint": "Нужны цикл for, переменная total и условие if.",
                "practice_check_mode": "contains_all",
                "practice_check_value": "for,if,print",
                "quiz": [
                    {
                        "text": "Зачем нужен цикл for?",
                        "options": [
                            {"text": "Чтобы повторять действия для каждого элемента", "is_correct": True},
                            {"text": "Чтобы менять язык программы", "is_correct": False},
                            {"text": "Чтобы очищать память вручную", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Когда срабатывает ветка if?",
                        "options": [
                            {"text": "Когда условие истинно", "is_correct": True},
                            {"text": "Всегда после else", "is_correct": False},
                            {"text": "Только в начале файла", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Функции и мини-проект",
                "age_range": "13-15",
                "difficulty": "hard",
                "unlock_xp": 80,
                "xp_reward": 70,
                "description": "Собираем мини-проект с функцией и оценкой результата.",
                "theory_html": """
<h3>Функции и разбиение задачи</h3>
<p>Функция — это блок кода, который можно вызывать много раз. Это делает код короче и понятнее.</p>
<pre>def average(values):
    return sum(values) / len(values)

marks = [5, 4, 5, 3]
avg = average(marks)
print(avg)</pre>
""",
                "practice_task": "Сделай функцию average(values), посчитай средний балл и выведи уровень: Отлично/Хорошо/Нужно подтянуть.",
                "practice_starter": (
                    "def average(values):\n"
                    "    return sum(values) / len(values)\n\n"
                    "marks = [5, 4, 5, 3]\n"
                    "avg = average(marks)\n\n"
                    "if avg >= 4.5:\n"
                    '    print("Отлично")\n'
                    "elif avg >= 3.5:\n"
                    '    print("Хорошо")\n'
                    "else:\n"
                    '    print("Нужно подтянуть")\n'
                ),
                "practice_hint": "Используй def, return и условную развилку if/elif/else.",
                "practice_check_mode": "contains_all",
                "practice_check_value": "def,return,average",
                "quiz": [
                    {
                        "text": "Что возвращает оператор return?",
                        "options": [
                            {"text": "Результат работы функции", "is_correct": True},
                            {"text": "Случайный текст", "is_correct": False},
                            {"text": "Только ноль", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Зачем делить код на функции?",
                        "options": [
                            {"text": "Чтобы код было проще читать и переиспользовать", "is_correct": True},
                            {"text": "Чтобы Python работал офлайн", "is_correct": False},
                            {"text": "Чтобы не писать переменные", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Списки и словари в задачах",
                "age_range": "12-14",
                "difficulty": "medium",
                "unlock_xp": 140,
                "xp_reward": 80,
                "description": "Учимся хранить структуру данных и строить отчёт по ним.",
                "theory_html": """
<h3>Списки + словари = основа маленьких проектов</h3>
<p>Список хранит набор элементов, словарь — именованные поля. Вместе они позволяют описать состояние игры или учебного плана.</p>
<pre>player = {"name": "Nika", "level": 3, "xp": 145}
missions = [
    {"title": "Синтаксис", "done": True},
    {"title": "Циклы", "done": False},
]

done_count = 0
for m in missions:
    if m["done"]:
        done_count += 1

print(f"{player['name']}: выполнено {done_count}/{len(missions)}")</pre>
""",
                "practice_task": "Создай словарь player и список missions, посчитай выполненные задачи и выведи отчёт.",
                "practice_starter": (
                    "player = {\n"
                    '    "name": "Nika",\n'
                    '    "grade": 6,\n'
                    '    "favorite_language": "python",\n'
                    "}\n\n"
                    "missions = [\n"
                    '    {"title": "print и переменные", "done": True},\n'
                    '    {"title": "условия if", "done": True},\n'
                    '    {"title": "циклы for", "done": False},\n'
                    "]\n\n"
                    "done_count = 0\n"
                    "for mission in missions:\n"
                    '    if mission["done"]:\n'
                    "        done_count += 1\n\n"
                    'print(f\"{player[\'name\']}: выполнено {done_count}/{len(missions)}\")\n'
                ),
                "practice_hint": "Тебе нужны list, dict, цикл for и проверка done.",
                "practice_check_mode": "contains_all",
                "practice_check_value": "missions,player,for,print",
                "quiz": [
                    {
                        "text": "Что лучше хранить в словаре?",
                        "options": [
                            {"text": "Поля одного объекта: имя, уровень, XP", "is_correct": True},
                            {"text": "Только одну букву", "is_correct": False},
                            {"text": "Лишь комментарии", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Как посчитать выполненные задания в списке?",
                        "options": [
                            {"text": "Пройтись циклом и проверять поле done", "is_correct": True},
                            {"text": "Удалить все элементы списка", "is_correct": False},
                            {"text": "Всегда ставить done_count = 100", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Финальный мини-проект: планировщик",
                "age_range": "14-15",
                "difficulty": "hard",
                "unlock_xp": 220,
                "xp_reward": 100,
                "description": "Собираем простой планировщик задач с функциями и списком словарей.",
                "theory_html": """
<h3>Финальный шаг: собрать маленький продукт</h3>
<p>Хороший проект состоит из простых функций: добавить задачу, отметить выполнение, вывести текущий план.</p>
<pre>tasks = []

def add_task(tasks, title, priority):
    tasks.append({"title": title, "priority": priority, "done": False})

def print_plan(tasks):
    for t in tasks:
        mark = "✅" if t["done"] else "⬜"
        print(f"{mark} {t['title']} ({t['priority']})")

add_task(tasks, "Сделать ДЗ", "high")
print_plan(tasks)</pre>
""",
                "practice_task": "Реализуй add_task(...) и print_plan(...), добавь 3 задачи и выведи их список.",
                "practice_starter": (
                    "tasks = []\n\n"
                    "def add_task(tasks, title, priority):\n"
                    "    # TODO: добавь словарь задачи в список\n"
                    "    return tasks\n\n"
                    "def print_plan(tasks):\n"
                    "    # TODO: выведи все задачи в формате: [приоритет] название\n"
                    "    pass\n\n"
                    "add_task(tasks, 'Повторить циклы', 'high')\n"
                    "add_task(tasks, 'Сделать 5 задач', 'medium')\n"
                    "add_task(tasks, 'Подготовить проект', 'high')\n"
                    "print_plan(tasks)\n"
                ),
                "practice_hint": "Используй append, функции с параметрами и цикл for для вывода.",
                "practice_check_mode": "contains_all",
                "practice_check_value": "def,add_task,print_plan,return",
                "quiz": [
                    {
                        "text": "Почему удобно делить проект на функции?",
                        "options": [
                            {"text": "Код проще тестировать и расширять", "is_correct": True},
                            {"text": "Чтобы убрать все переменные", "is_correct": False},
                            {"text": "Иначе Python не запустится", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Как хранить список задач с несколькими полями?",
                        "options": [
                            {"text": "Список словарей", "is_correct": True},
                            {"text": "Только одну строку", "is_correct": False},
                            {"text": "Набор комментариев", "is_correct": False},
                        ],
                    },
                ],
            },
        ],
    },
    "javascript": {
        "title": "JavaScript: логика и интерактив",
        "description": "Трек 8-15: основы JS, условия, массивы и объекты.",
        "modules": [
            {
                "title": "Первые шаги в JavaScript",
                "age_range": "8-10",
                "difficulty": "easy",
                "unlock_xp": 0,
                "xp_reward": 35,
                "description": "Вывод сообщений, переменные и простые вычисления.",
                "theory_html": """
<h3>JavaScript для старта</h3>
<p>Команда <code>console.log()</code> показывает результат в консоли.</p>
<pre>const name = "Илья";
const age = 10;
console.log(`Привет, ${name}! Мне ${age}.`);</pre>
""",
                "practice_task": "Сохрани имя и любимый предмет в переменные и выведи сообщение в console.log.",
                "practice_starter": (
                    'const name = "Илья";\n'
                    'const favoriteSubject = "математика";\n'
                    'console.log(`Привет! Я ${name}, мой любимый предмет — ${favoriteSubject}.`);\n'
                ),
                "practice_hint": "Используй шаблонную строку с ${...}.",
                "practice_check_mode": "contains_all",
                "practice_check_value": "console.log,favoriteSubject",
                "quiz": [
                    {
                        "text": "Как вывести текст в JavaScript?",
                        "options": [
                            {"text": "console.log(...)", "is_correct": True},
                            {"text": "print(...)", "is_correct": False},
                            {"text": "echo(...)", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Как объявить неизменяемую переменную?",
                        "options": [
                            {"text": "const", "is_correct": True},
                            {"text": "loop", "is_correct": False},
                            {"text": "function", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Условия и массивы",
                "age_range": "11-12",
                "difficulty": "medium",
                "unlock_xp": 30,
                "xp_reward": 50,
                "description": "Работаем с if, for и списками значений.",
                "theory_html": """
<h3>Логика в JavaScript</h3>
<p>Условие <code>if</code> проверяет правило, цикл <code>for</code> проходит по массиву.</p>
<pre>const scores = [6, 7, 9];
let sum = 0;
for (const s of scores) {
  sum += s;
}
if (sum >= 20) {
  console.log("Победа!");
}</pre>
""",
                "practice_task": "Посчитай сумму массива scores и выведи \"Победа\", если сумма не меньше 20.",
                "practice_starter": (
                    "const scores = [6, 7, 9];\n"
                    "let sum = 0;\n\n"
                    "for (const s of scores) {\n"
                    "  sum += s;\n"
                    "}\n\n"
                    "if (sum >= 20) {\n"
                    '  console.log("Победа!");\n'
                    "} else {\n"
                    '  console.log("Еще тренировка");\n'
                    "}\n"
                ),
                "practice_hint": "Нужны for...of, sum и if.",
                "practice_check_mode": "contains_all",
                "practice_check_value": "for,if,console.log",
                "quiz": [
                    {
                        "text": "Что такое массив?",
                        "options": [
                            {"text": "Список значений", "is_correct": True},
                            {"text": "Только одно число", "is_correct": False},
                            {"text": "Кнопка на сайте", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Как увеличить sum в цикле?",
                        "options": [
                            {"text": "sum += s", "is_correct": True},
                            {"text": "sum == s", "is_correct": False},
                            {"text": "sum => s", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Функции и объекты",
                "age_range": "13-15",
                "difficulty": "hard",
                "unlock_xp": 80,
                "xp_reward": 70,
                "description": "Создаем функции и объект мини-профиля игрока.",
                "theory_html": """
<h3>Функции и объекты</h3>
<p>Функции позволяют переиспользовать код, объекты хранят свойства и данные сущности.</p>
<pre>function levelTitle(xp) {
  if (xp >= 100) return "Профи";
  return "Новичок";
}

const player = { name: "Mira", xp: 120 };
console.log(`${player.name}: ${levelTitle(player.xp)}`);</pre>
""",
                "practice_task": "Создай функцию rank(xp) и объект player, затем выведи ранг игрока.",
                "practice_starter": (
                    "function rank(xp) {\n"
                    "  if (xp >= 150) return 'Мастер';\n"
                    "  if (xp >= 100) return 'Профи';\n"
                    "  return 'Новичок';\n"
                    "}\n\n"
                    "const player = { name: 'Mira', xp: 120 };\n"
                    "console.log(`${player.name}: ${rank(player.xp)}`);\n"
                ),
                "practice_hint": "Используй function, return и объект с полями name/xp.",
                "practice_check_mode": "contains_all",
                "practice_check_value": "function,return,player",
                "quiz": [
                    {
                        "text": "Что хранит объект в JS?",
                        "options": [
                            {"text": "Пары ключ-значение", "is_correct": True},
                            {"text": "Только один символ", "is_correct": False},
                            {"text": "Только массивы", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Зачем нужен return в функции?",
                        "options": [
                            {"text": "Вернуть результат наружу", "is_correct": True},
                            {"text": "Создать новый цикл", "is_correct": False},
                            {"text": "Остановить интернет", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Массивы объектов и аналитика",
                "age_range": "12-14",
                "difficulty": "medium",
                "unlock_xp": 140,
                "xp_reward": 80,
                "description": "Фильтруем данные, считаем статистику и выводим результат.",
                "theory_html": """
<h3>Работа с данными как в реальном проекте</h3>
<p>Когда у нас массив объектов, мы можем фильтровать, считать сумму и делать отчёт.</p>
<pre>const lessons = [
  { title: "Переменные", done: true, xp: 20 },
  { title: "Циклы", done: false, xp: 30 },
];

const doneLessons = lessons.filter(l => l.done);
const xpEarned = doneLessons.reduce((acc, l) => acc + l.xp, 0);
console.log(`Выполнено: ${doneLessons.length}, XP: ${xpEarned}`);</pre>
""",
                "practice_task": "Создай массив lessons, отфильтруй выполненные и посчитай общий XP через reduce.",
                "practice_starter": (
                    "const lessons = [\n"
                    "  { title: 'Переменные', done: true, xp: 20 },\n"
                    "  { title: 'Условия', done: true, xp: 25 },\n"
                    "  { title: 'Функции', done: false, xp: 30 },\n"
                    "];\n\n"
                    "// TODO: оставь только выполненные уроки\n"
                    "const doneLessons = lessons.filter((lesson) => lesson.done);\n\n"
                    "// TODO: посчитай сумму XP выполненных уроков\n"
                    "const totalXp = doneLessons.reduce((acc, lesson) => acc + lesson.xp, 0);\n\n"
                    "console.log(`Выполнено: ${doneLessons.length}`);\n"
                    "console.log(`XP: ${totalXp}`);\n"
                ),
                "practice_hint": "Используй filter для отбора и reduce для суммы.",
                "practice_check_mode": "contains_all",
                "practice_check_value": "filter,reduce,console.log",
                "quiz": [
                    {
                        "text": "Для чего нужен filter?",
                        "options": [
                            {"text": "Оставить элементы, подходящие по условию", "is_correct": True},
                            {"text": "Поменять язык файла", "is_correct": False},
                            {"text": "Удалить весь массив", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что делает reduce?",
                        "options": [
                            {"text": "Собирает массив в одно значение", "is_correct": True},
                            {"text": "Создаёт новый класс", "is_correct": False},
                            {"text": "Открывает сайт", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Финальный мини-проект: трекер привычек",
                "age_range": "14-15",
                "difficulty": "hard",
                "unlock_xp": 220,
                "xp_reward": 100,
                "description": "Собираем маленькое приложение с функциями и объектами.",
                "theory_html": """
<h3>Мини-приложение на JavaScript</h3>
<p>Финальный уровень: создаём структуру данных и функции, которые её изменяют и печатают отчёт.</p>
<pre>const habits = [];

function addHabit(list, name, target) {
  list.push({ name, target, done: 0 });
}

function markDone(list, name) {
  const habit = list.find(h => h.name === name);
  if (habit) habit.done += 1;
}

addHabit(habits, "Чтение", 5);
markDone(habits, "Чтение");
console.log(habits);</pre>
""",
                "practice_task": "Реализуй addHabit, markDone и printStats для массива habits.",
                "practice_starter": (
                    "const habits = [];\n\n"
                    "function addHabit(list, name, target) {\n"
                    "  // TODO: добавь новую привычку в список\n"
                    "}\n\n"
                    "function markDone(list, name) {\n"
                    "  // TODO: найди привычку по имени и увеличь done\n"
                    "}\n\n"
                    "function printStats(list) {\n"
                    "  // TODO: выведи каждую привычку в формате: name: done/target\n"
                    "}\n\n"
                    "addHabit(habits, 'Чтение', 5);\n"
                    "addHabit(habits, 'Спорт', 4);\n"
                    "markDone(habits, 'Чтение');\n"
                    "markDone(habits, 'Чтение');\n"
                    "markDone(habits, 'Спорт');\n"
                    "printStats(habits);\n"
                ),
                "practice_hint": "Тебе помогут push, find, if и console.log.",
                "practice_check_mode": "contains_all",
                "practice_check_value": "function,habits,console.log,return",
                "quiz": [
                    {
                        "text": "Зачем хранить проектные данные в массиве объектов?",
                        "options": [
                            {"text": "Так удобнее обновлять и выводить состояние", "is_correct": True},
                            {"text": "Чтобы не писать функции", "is_correct": False},
                            {"text": "Это обязательно только для сайтов", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Как найти объект в массиве по условию?",
                        "options": [
                            {"text": "Через find(...)", "is_correct": True},
                            {"text": "Через import(...)", "is_correct": False},
                            {"text": "Через static(...)", "is_correct": False},
                        ],
                    },
                ],
            },
        ],
    },
    "csharp": {
        "title": "C#: от консоли до классов",
        "description": "Трек 8-15: синтаксис C#, условия, методы и основы ООП.",
        "modules": [
            {
                "title": "Старт в C#",
                "age_range": "10-12",
                "difficulty": "easy",
                "unlock_xp": 0,
                "xp_reward": 35,
                "description": "Вывод текста и базовые переменные в C#.",
                "theory_html": """
<h3>Первые шаги в C#</h3>
<p>Для вывода используем <code>Console.WriteLine()</code>.</p>
<pre>using System;

string name = "Олег";
int age = 11;
Console.WriteLine($"Привет, {name}! Тебе {age} лет.");</pre>
""",
                "practice_task": "Создай переменные name и hobby, выведи сообщение о себе.",
                "practice_starter": (
                    "using System;\n\n"
                    'string name = "Олег";\n'
                    'string hobby = "робототехника";\n'
                    'Console.WriteLine($"Меня зовут {name}, мое хобби — {hobby}.");\n'
                ),
                "practice_hint": "Используй строковые переменные и Console.WriteLine.",
                "practice_check_mode": "contains_all",
                "practice_check_value": "WriteLine,string",
                "quiz": [
                    {
                        "text": "Какая команда печатает текст в C#?",
                        "options": [
                            {"text": "Console.WriteLine()", "is_correct": True},
                            {"text": "console.log()", "is_correct": False},
                            {"text": "print()", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Какой тип подходит для возраста?",
                        "options": [
                            {"text": "int", "is_correct": True},
                            {"text": "bool", "is_correct": False},
                            {"text": "char", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Условия и методы",
                "age_range": "12-13",
                "difficulty": "medium",
                "unlock_xp": 30,
                "xp_reward": 50,
                "description": "Пишем метод и используем if для решения задачи.",
                "theory_html": """
<h3>Решаем задачи через методы</h3>
<p>Метод объединяет действия в отдельный блок кода.</p>
<pre>using System;

int Sum(int a, int b) {
    return a + b;
}

int result = Sum(7, 5);
if (result >= 10) {
    Console.WriteLine("Отлично");
}</pre>
""",
                "practice_task": "Сделай метод Total(points) и выведи \"Победа\", если сумма >= 20.",
                "practice_starter": (
                    "using System;\n\n"
                    "int Total(int[] points) {\n"
                    "    int sum = 0;\n"
                    "    foreach (int p in points) {\n"
                    "        sum += p;\n"
                    "    }\n"
                    "    return sum;\n"
                    "}\n\n"
                    "int[] points = {6, 7, 8};\n"
                    "int total = Total(points);\n"
                    "if (total >= 20) {\n"
                    "    Console.WriteLine(\"Победа\");\n"
                    "} else {\n"
                    "    Console.WriteLine(\"Еще попытка\");\n"
                    "}\n"
                ),
                "practice_hint": "Нужны метод, return и if.",
                "practice_check_mode": "contains_all",
                "practice_check_value": "return,if,WriteLine",
                "quiz": [
                    {
                        "text": "Зачем нужен метод в C#?",
                        "options": [
                            {"text": "Чтобы переиспользовать код", "is_correct": True},
                            {"text": "Чтобы удалить проект", "is_correct": False},
                            {"text": "Чтобы менять операционную систему", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что делает if?",
                        "options": [
                            {"text": "Проверяет условие", "is_correct": True},
                            {"text": "Создает массив", "is_correct": False},
                            {"text": "Сохраняет файл", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Классы и мини-проект",
                "age_range": "13-15",
                "difficulty": "hard",
                "unlock_xp": 80,
                "xp_reward": 70,
                "description": "Создаем класс и используем объект в мини-проекте.",
                "theory_html": """
<h3>Основы ООП в C#</h3>
<p>Класс описывает модель объекта, а экземпляр класса хранит конкретные данные.</p>
<pre>using System;

var bot = new Robot("Codey");
Console.WriteLine(bot.Hello());

class Robot {
    public string Name { get; }
    public Robot(string name) { Name = name; }
    public string Hello() => $"Я робот {Name}";
}</pre>
""",
                "practice_task": "Создай класс Hero с полем Name и методом Intro(), затем выведи приветствие героя.",
                "practice_starter": (
                    "using System;\n\n"
                    "var hero = new Hero(\"Nova\");\n"
                    "Console.WriteLine(hero.Intro());\n\n"
                    "class Hero {\n"
                    "    public string Name { get; }\n\n"
                    "    public Hero(string name) {\n"
                    "        Name = name;\n"
                    "    }\n\n"
                    "    public string Intro() {\n"
                    "        return $\"Я герой {Name}\";\n"
                    "    }\n"
                    "}\n"
                ),
                "practice_hint": "Нужны class, конструктор и метод с return.",
                "practice_check_mode": "contains_all",
                "practice_check_value": "class,return,WriteLine",
                "quiz": [
                    {
                        "text": "Что описывает класс?",
                        "options": [
                            {"text": "Шаблон объекта", "is_correct": True},
                            {"text": "Только одно число", "is_correct": False},
                            {"text": "Список библиотек", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что такое объект hero?",
                        "options": [
                            {"text": "Экземпляр класса Hero", "is_correct": True},
                            {"text": "Имя файла", "is_correct": False},
                            {"text": "Тип данных bool", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Коллекции и аналитика",
                "age_range": "12-14",
                "difficulty": "medium",
                "unlock_xp": 140,
                "xp_reward": 80,
                "description": "Учимся работать со списками и считать базовую статистику.",
                "theory_html": """
<h3>Списки в C#</h3>
<p>Коллекция <code>List&lt;T&gt;</code> помогает хранить набор значений и проходить по ним циклом.</p>
<pre>using System;
using System.Collections.Generic;

var points = new List<int> { 7, 8, 10, 9 };
int total = 0;
foreach (int p in points) {
    total += p;
}

double avg = (double)total / points.Count;
Console.WriteLine($"Средний балл: {avg:F1}");</pre>
""",
                "practice_task": "Создай List<int> points, посчитай сумму и средний балл, затем выведи оценку результата.",
                "practice_starter": (
                    "using System;\n"
                    "using System.Collections.Generic;\n\n"
                    "var points = new List<int> { 7, 8, 10, 9, 6 };\n"
                    "int total = 0;\n\n"
                    "foreach (int p in points) {\n"
                    "    total += p;\n"
                    "}\n\n"
                    "double avg = (double)total / points.Count;\n"
                    "Console.WriteLine($\"Средний балл: {avg:F1}\");\n\n"
                    "if (avg >= 8) {\n"
                    "    Console.WriteLine(\"Отличный прогресс\");\n"
                    "} else if (avg >= 6.5) {\n"
                    "    Console.WriteLine(\"Хороший результат\");\n"
                    "} else {\n"
                    "    Console.WriteLine(\"Нужно потренироваться\");\n"
                    "}\n"
                ),
                "practice_hint": "Тебе нужны List<int>, foreach, вычисление average и Console.WriteLine.",
                "practice_check_mode": "contains_all",
                "practice_check_value": "List,foreach,Console.WriteLine",
                "quiz": [
                    {
                        "text": "Что хранит List<int>?",
                        "options": [
                            {"text": "Список целых чисел", "is_correct": True},
                            {"text": "Только один символ", "is_correct": False},
                            {"text": "Только строки", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Зачем приводить total к double перед делением?",
                        "options": [
                            {"text": "Чтобы получить дробный средний балл", "is_correct": True},
                            {"text": "Чтобы удалить остаток", "is_correct": False},
                            {"text": "Это нужно только в JavaScript", "is_correct": False},
                        ],
                    },
                ],
            },
            {
                "title": "Финальный мини-проект: менеджер задач",
                "age_range": "14-15",
                "difficulty": "hard",
                "unlock_xp": 220,
                "xp_reward": 100,
                "description": "Собираем консольный менеджер задач на классах и списках.",
                "theory_html": """
<h3>Структура проекта на C#</h3>
<p>Финальный проект строится из модели данных (class), списка элементов и функций работы с ними.</p>
<pre>using System;
using System.Collections.Generic;

class TaskItem {
    public string Title { get; }
    public bool Done { get; set; }
    public TaskItem(string title) { Title = title; Done = false; }
}

var tasks = new List<TaskItem>();
tasks.Add(new TaskItem("Подготовить презентацию"));
Console.WriteLine(tasks[0].Title);</pre>
""",
                "practice_task": "Создай class TaskItem и функции AddTask/PrintTasks, добавь 3 задачи и выведи их.",
                "practice_starter": (
                    "using System;\n"
                    "using System.Collections.Generic;\n\n"
                    "class TaskItem {\n"
                    "    public string Title { get; }\n"
                    "    public bool Done { get; set; }\n\n"
                    "    public TaskItem(string title) {\n"
                    "        Title = title;\n"
                    "        Done = false;\n"
                    "    }\n"
                    "}\n\n"
                    "void AddTask(List<TaskItem> tasks, string title) {\n"
                    "    tasks.Add(new TaskItem(title));\n"
                    "}\n\n"
                    "void PrintTasks(List<TaskItem> tasks) {\n"
                    "    foreach (var task in tasks) {\n"
                    "        string mark = task.Done ? \"✅\" : \"⬜\";\n"
                    "        Console.WriteLine($\"{mark} {task.Title}\");\n"
                    "    }\n"
                    "}\n\n"
                    "var tasks = new List<TaskItem>();\n"
                    "AddTask(tasks, \"Сделать домашку\");\n"
                    "AddTask(tasks, \"Повторить циклы\");\n"
                    "AddTask(tasks, \"Подготовить проект\");\n"
                    "tasks[1].Done = true;\n"
                    "PrintTasks(tasks);\n"
                ),
                "practice_hint": "Используй class, List<TaskItem>, методы AddTask и PrintTasks.",
                "practice_check_mode": "contains_all",
                "practice_check_value": "class,List,Console.WriteLine,AddTask",
                "quiz": [
                    {
                        "text": "Зачем нужен класс TaskItem?",
                        "options": [
                            {"text": "Чтобы описать одну задачу с полями", "is_correct": True},
                            {"text": "Чтобы хранить только числа", "is_correct": False},
                            {"text": "Чтобы заменить цикл foreach", "is_correct": False},
                        ],
                    },
                    {
                        "text": "Что даёт List<TaskItem> в проекте?",
                        "options": [
                            {"text": "Хранение и обработку множества задач", "is_correct": True},
                            {"text": "Только запуск программы", "is_correct": False},
                            {"text": "Автоматический UI", "is_correct": False},
                        ],
                    },
                ],
            },
        ],
    },
}


def compute_level(xp: int) -> int:
    level = 1
    for idx in range(1, len(XP_PER_LEVEL)):
        if xp >= XP_PER_LEVEL[idx]:
            level = idx + 1
        else:
            break
    return level


def _rule_satisfied(db: Session, user: User, rule: dict[str, Any]) -> bool:
    rtype = rule.get("type")
    minimum = int(rule.get("min", 0))
    if rtype == "always":
        return True
    if rtype == "lessons_completed":
        return user.lessons_completed >= minimum
    if rtype == "correct_answers":
        return user.correct_answers >= minimum
    if rtype == "level":
        return user.level >= minimum
    if rtype == "xp":
        return user.xp >= minimum
    if rtype == "module_complete":
        completed = db.scalar(select(func.count(ModuleCompletionReward.id)).where(ModuleCompletionReward.user_id == user.id))
        return int(completed or 0) >= minimum
    return False


def evaluate_achievements(db: Session, user: User) -> list[dict[str, Any]]:
    already = {row.achievement_id for row in db.scalars(select(UserAchievement).where(UserAchievement.user_id == user.id)).all()}
    new_items: list[dict[str, Any]] = []
    for ach in db.scalars(select(AchievementDef)).all():
        if ach.id in already:
            continue
        if not _rule_satisfied(db, user, ach.rule_json or {}):
            continue
        db.add(UserAchievement(user_id=user.id, achievement_id=ach.id))
        if ach.xp_reward:
            user.xp += ach.xp_reward
            user.level = compute_level(user.xp)
        new_items.append({"id": ach.id, "code": ach.code, "name": ach.name, "description": ach.description, "icon": ach.icon, "xp_reward": ach.xp_reward})
    if new_items:
        db.commit()
        db.refresh(user)
    return new_items


def seed_admin_user(db: Session) -> None:
    if db.scalar(select(User).where(User.username == settings.admin_username)):
        return
    db.add(User(username=settings.admin_username, password_hash=hash_password(settings.admin_password), role=UserRole.ADMIN, age=None, xp=0, level=1, stars=0, streak=1, lessons_completed=0, correct_answers=0))
    db.commit()


def seed_achievements(db: Session) -> None:
    for item in ACHIEVEMENT_SEED:
        if db.scalar(select(AchievementDef).where(AchievementDef.code == item["code"])):
            continue
        db.add(AchievementDef(**item))
    db.commit()


def _seed_quiz_questions(
    db: Session, lesson_id: int, questions: list[dict[str, Any]]
) -> None:
    for q_idx, q_data in enumerate(questions, 1):
        question = QuizQuestion(
            lesson_id=lesson_id, text=q_data["text"], order_index=q_idx
        )
        db.add(question)
        db.flush()
        for o_idx, opt in enumerate(q_data["options"], 1):
            db.add(
                QuizOption(
                    question_id=question.id,
                    text=opt["text"],
                    is_correct=bool(opt.get("is_correct")),
                    order_index=o_idx,
                )
            )


def _seed_course_track(db: Session, track_meta: dict[str, str]) -> None:
    track_name = track_meta["track"]
    blueprint = COURSE_BLUEPRINTS[track_name]
    course = Course(
        track=track_name,
        title=blueprint["title"],
        description=f"{blueprint['description']} [{SEED_COURSE_VERSION}]",
        is_published=True,
        created_by=None,
    )
    db.add(course)
    db.flush()

    for m_idx, m_data in enumerate(blueprint["modules"], 1):
        module = Module(
            course_id=course.id,
            title=f"{track_meta['emoji']} {m_data['title']} ({m_data['age_range']})",
            description=f"Возраст: {m_data['age_range']}. {m_data['description']}",
            difficulty=m_data["difficulty"],
            color=track_meta["color"],
            emoji=track_meta["emoji"],
            unlock_xp=m_data["unlock_xp"],
            xp_reward=m_data["xp_reward"],
            order_index=m_idx,
        )
        db.add(module)
        db.flush()

        theory_lesson = Lesson(
            module_id=module.id,
            title=f"Теория ({m_data['age_range']})",
            lesson_type=LessonType.THEORY,
            emoji="📖",
            xp_reward=12 + (m_idx - 1) * 3,
            order_index=1,
            theory_html=m_data["theory_html"],
        )
        db.add(theory_lesson)
        db.flush()

        practice_lesson = Lesson(
            module_id=module.id,
            title=f"Практика ({m_data['age_range']})",
            lesson_type=LessonType.PRACTICE,
            emoji="🎮",
            xp_reward=12 + (m_idx - 1) * 3,
            order_index=2,
            practice_task=m_data["practice_task"],
            practice_starter=m_data["practice_starter"],
            practice_hint=m_data["practice_hint"],
            practice_language=track_name,
            practice_check_mode=m_data["practice_check_mode"],
            practice_check_value=m_data["practice_check_value"],
        )
        db.add(practice_lesson)
        db.flush()

        quiz_lesson = Lesson(
            module_id=module.id,
            title=f"Тест ({m_data['age_range']})",
            lesson_type=LessonType.QUIZ,
            emoji="🧪",
            xp_reward=12 + (m_idx - 1) * 3,
            order_index=3,
        )
        db.add(quiz_lesson)
        db.flush()

        _seed_quiz_questions(db, quiz_lesson.id, m_data["quiz"])


def _needs_course_reseed(db: Session) -> bool:
    tracks = [t["track"] for t in TRACKS]
    seed_courses = db.scalars(
        select(Course).where(Course.created_by.is_(None), Course.track.in_(tracks))
    ).all()
    if len(seed_courses) != len(tracks):
        return True
    return any(
        SEED_COURSE_VERSION not in (course.description or "") for course in seed_courses
    )


def _reseed_courses(db: Session) -> None:
    tracks = [t["track"] for t in TRACKS]
    old_seed_courses = db.scalars(
        select(Course).where(Course.created_by.is_(None), Course.track.in_(tracks))
    ).all()
    for course in old_seed_courses:
        db.delete(course)
    db.flush()
    for track in TRACKS:
        _seed_course_track(db, track)
    db.commit()


def bootstrap_data(db: Session) -> None:
    seed_admin_user(db)
    seed_achievements(db)
    if _needs_course_reseed(db):
        _reseed_courses(db)


def ensure_first_login_achievement(db: Session, user: User) -> None:
    ach = db.scalar(select(AchievementDef).where(AchievementDef.code == "first_login"))
    if not ach:
        return
    exists = db.scalar(select(UserAchievement).where(UserAchievement.user_id == user.id, UserAchievement.achievement_id == ach.id))
    if exists:
        return
    db.add(UserAchievement(user_id=user.id, achievement_id=ach.id))
    db.commit()


def complete_lesson(db: Session, user: User, lesson: Lesson) -> dict[str, Any]:
    existing = db.scalar(select(UserProgress).where(UserProgress.user_id == user.id, UserProgress.lesson_id == lesson.id))
    if existing:
        return {"already_completed": True, "lesson_xp": 0, "module_bonus_xp": 0, "level_up": False}

    prev_level = user.level
    lesson_xp = int(lesson.xp_reward or 0)
    db.add(UserProgress(user_id=user.id, module_id=lesson.module_id, lesson_id=lesson.id, xp_earned=lesson_xp))
    user.lessons_completed += 1
    user.stars += 1
    user.xp += lesson_xp

    module_bonus_xp = 0
    module = db.get(Module, lesson.module_id)
    total_lessons = db.scalar(select(func.count(Lesson.id)).where(Lesson.module_id == lesson.module_id)) or 0
    done_lessons = db.scalar(select(func.count(UserProgress.id)).where(UserProgress.user_id == user.id, UserProgress.module_id == lesson.module_id)) or 0

    if total_lessons > 0 and done_lessons == total_lessons:
        already_bonus = db.scalar(select(ModuleCompletionReward).where(ModuleCompletionReward.user_id == user.id, ModuleCompletionReward.module_id == lesson.module_id))
        if already_bonus is None and module and module.xp_reward > 0:
            module_bonus_xp = int(module.xp_reward)
            user.xp += module_bonus_xp
            db.add(ModuleCompletionReward(user_id=user.id, module_id=lesson.module_id, bonus_xp=module_bonus_xp))

    user.level = compute_level(user.xp)
    db.add(LessonAttempt(user_id=user.id, lesson_id=lesson.id, kind="lesson_complete", score=1, max_score=1, passed=True, details_json={"module_bonus_xp": module_bonus_xp}))
    db.commit()
    db.refresh(user)

    return {"already_completed": False, "lesson_xp": lesson_xp, "module_bonus_xp": module_bonus_xp, "level_up": user.level > prev_level}


def submit_quiz(db: Session, user: User, lesson: Lesson, answers: dict[int, int]) -> dict[str, Any]:
    questions = db.scalars(select(QuizQuestion).where(QuizQuestion.lesson_id == lesson.id).order_by(QuizQuestion.order_index)).all()
    details = []
    correct = 0

    for q in questions:
        options = db.scalars(select(QuizOption).where(QuizOption.question_id == q.id).order_by(QuizOption.order_index)).all()
        correct_opt = next((o for o in options if o.is_correct), None)
        picked = answers.get(q.id)
        ok = bool(correct_opt and picked == correct_opt.id)
        if ok:
            correct += 1
        details.append(
            {
                "question_id": q.id,
                "question": q.text,
                "picked_option_id": picked,
                "correct_option_id": correct_opt.id if correct_opt else None,
                "is_correct": ok,
                "options": [{"id": o.id, "text": o.text, "is_correct": o.is_correct} for o in options],
            }
        )

    max_score = len(questions)
    user.correct_answers += correct
    db.add(LessonAttempt(user_id=user.id, lesson_id=lesson.id, kind="quiz", score=correct, max_score=max_score, passed=(correct == max_score if max_score else False), details_json={"questions": details}))
    db.commit()

    completion = complete_lesson(db, user, lesson)
    unlocked = evaluate_achievements(db, user)
    return {"score": correct, "max_score": max_score, "questions": details, "completion": completion, "new_achievements": unlocked}


def serialize_lesson(db: Session, lesson: Lesson, include_answers: bool = False) -> dict[str, Any]:
    practice_language = lesson.practice_language
    practice_starter = lesson.practice_starter
    practice_hint = lesson.practice_hint
    if lesson.lesson_type == LessonType.PRACTICE:
        if not practice_language:
            practice_language = "python"
        if not (practice_starter or "").strip():
            practice_starter = default_practice_starter(practice_language)
        if not (practice_hint or "").strip():
            practice_hint = default_practice_hint(practice_language)

    payload = {
        "id": lesson.id,
        "module_id": lesson.module_id,
        "title": lesson.title,
        "lesson_type": lesson.lesson_type.value,
        "emoji": lesson.emoji,
        "xp_reward": lesson.xp_reward,
        "order_index": lesson.order_index,
        "theory_html": lesson.theory_html,
        "practice_task": lesson.practice_task,
        "practice_starter": practice_starter,
        "practice_hint": practice_hint,
        "practice_language": practice_language,
        "practice_check_mode": lesson.practice_check_mode,
        "practice_check_value": lesson.practice_check_value if include_answers else None,
    }
    if lesson.lesson_type == LessonType.QUIZ:
        questions = db.scalars(select(QuizQuestion).where(QuizQuestion.lesson_id == lesson.id).order_by(QuizQuestion.order_index)).all()
        payload["questions"] = []
        for q in questions:
            options = db.scalars(select(QuizOption).where(QuizOption.question_id == q.id).order_by(QuizOption.order_index)).all()
            payload["questions"].append({"id": q.id, "text": q.text, "order_index": q.order_index, "options": [{"id": o.id, "text": o.text, "order_index": o.order_index, "is_correct": o.is_correct if include_answers else None} for o in options]})
    return payload


def serialize_course(db: Session, course: Course, include_answers: bool = False) -> dict[str, Any]:
    modules = db.scalars(select(Module).where(Module.course_id == course.id).order_by(Module.order_index)).all()
    return {
        "id": course.id,
        "track": course.track,
        "title": course.title,
        "description": course.description,
        "is_published": course.is_published,
        "modules": [
            {
                "id": m.id,
                "course_id": m.course_id,
                "title": m.title,
                "description": m.description,
                "difficulty": m.difficulty,
                "color": m.color,
                "emoji": m.emoji,
                "unlock_xp": m.unlock_xp,
                "xp_reward": m.xp_reward,
                "order_index": m.order_index,
                "lessons": [serialize_lesson(db, l, include_answers=include_answers) for l in db.scalars(select(Lesson).where(Lesson.module_id == m.id).order_by(Lesson.order_index)).all()],
            }
            for m in modules
        ],
    }


def user_progress_snapshot(db: Session, user: User) -> dict[str, Any]:
    progress_rows = db.scalars(select(UserProgress).where(UserProgress.user_id == user.id)).all()
    achievements = db.scalars(select(UserAchievement).where(UserAchievement.user_id == user.id)).all()
    ach_ids = [a.achievement_id for a in achievements]
    ach_defs = db.scalars(select(AchievementDef).where(AchievementDef.id.in_(ach_ids))).all() if ach_ids else []

    modules = db.scalars(select(Module).order_by(Module.id)).all()
    module_progress = []
    for mod in modules:
        total = db.scalar(select(func.count(Lesson.id)).where(Lesson.module_id == mod.id)) or 0
        done = db.scalar(select(func.count(UserProgress.id)).where(UserProgress.user_id == user.id, UserProgress.module_id == mod.id)) or 0
        module_progress.append({"module_id": mod.id, "module_title": mod.title, "completed_lessons": int(done), "total_lessons": int(total), "percent": int((done / total) * 100) if total else 0})

    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role.value,
            "age": user.age,
            "xp": user.xp,
            "level": user.level,
            "stars": user.stars,
            "streak": user.streak,
            "lessons_completed": user.lessons_completed,
            "correct_answers": user.correct_answers,
            "created_at": user.created_at.isoformat(),
        },
        "completed_lesson_ids": [row.lesson_id for row in progress_rows],
        "module_progress": module_progress,
        "achievements": [{"code": a.code, "name": a.name, "description": a.description, "icon": a.icon} for a in ach_defs],
    }


def cleanup_expired_sessions(db: Session) -> None:
    db.execute(delete(SessionToken).where(SessionToken.expires_at <= datetime.utcnow()))
    db.commit()


def parent_child_progress(db: Session, child: User) -> dict[str, Any]:
    snapshot = user_progress_snapshot(db, child)
    attempts = db.scalars(select(LessonAttempt).where(LessonAttempt.user_id == child.id).order_by(LessonAttempt.created_at.desc()).limit(15)).all()
    snapshot["recent_activity"] = [{"kind": a.kind, "lesson_id": a.lesson_id, "score": a.score, "max_score": a.max_score, "passed": a.passed, "created_at": a.created_at.isoformat()} for a in attempts]
    return snapshot


def simple_practice_check(lesson: Lesson, code: str) -> bool:
    mode = (lesson.practice_check_mode or "").strip().lower()
    if not mode:
        return True
    pieces = [x.strip() for x in (lesson.practice_check_value or "").split(",") if x.strip()]
    if mode == "contains_all":
        return all(p in code for p in pieces)
    if mode == "contains_any":
        return any(p in code for p in pieces)
    return True


def leaderboard_rows(db: Session) -> list[dict[str, Any]]:
    users = db.scalars(select(User).where(User.role == UserRole.STUDENT).order_by(User.xp.desc(), User.level.desc(), User.id.asc()).limit(100)).all()
    return [{"rank": idx, "user_id": u.id, "username": u.username, "xp": u.xp, "level": u.level, "stars": u.stars} for idx, u in enumerate(users, 1)]


def list_feed(db: Session, limit: int = 50) -> list[dict[str, Any]]:
    posts = db.scalars(select(CommunityPost).order_by(CommunityPost.created_at.desc()).limit(limit)).all()
    user_map = {u.id: u.username for u in db.scalars(select(User).where(User.id.in_([p.user_id for p in posts]))).all()} if posts else {}
    return [{"id": p.id, "user_id": p.user_id, "username": user_map.get(p.user_id, "unknown"), "content": p.content, "created_at": p.created_at.isoformat()} for p in posts]


def list_chat(db: Session, since_id: int | None = None, limit: int = 100) -> list[dict[str, Any]]:
    query = select(ChatMessage)
    if since_id:
        query = query.where(ChatMessage.id > since_id)
    rows = list(reversed(db.scalars(query.order_by(ChatMessage.id.desc()).limit(limit)).all()))
    user_map = {u.id: u.username for u in db.scalars(select(User).where(User.id.in_([r.user_id for r in rows]))).all()} if rows else {}
    return [{"id": r.id, "user_id": r.user_id, "username": user_map.get(r.user_id, "unknown"), "content": r.content, "created_at": r.created_at.isoformat()} for r in rows]


def pending_requests_for_child(db: Session, child_id: int) -> list[ParentLinkRequest]:
    return db.scalars(select(ParentLinkRequest).where(ParentLinkRequest.child_id == child_id, ParentLinkRequest.status == RequestStatus.PENDING)).all()


def parent_has_link(db: Session, parent_id: int, child_id: int) -> bool:
    return db.scalar(select(ParentChildLink).where(ParentChildLink.parent_id == parent_id, ParentChildLink.child_id == child_id)) is not None

