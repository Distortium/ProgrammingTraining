const DEFAULT_API_BASE = `http://${window.location.hostname || '127.0.0.1'}:8000`;
const API_BASE = (localStorage.getItem('programmer_api_base') || DEFAULT_API_BASE).replace(/\/$/, '');

const XP_PER_LEVEL = [0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200];

const state = {
  user: null,
  progress: null,
  courses: [],
  adminCourses: [],
  parentSelectedChildId: null,
  track: 'python',
  currentCourse: null,
  currentModule: null,
  currentLessonIdx: 0,
  quizAnswers: {},
  quizSubmitted: false,
  soundOn: true,
  particlesOn: true,
  chatPollTimer: null,
  audioCtx: null,
};

function qs(id) { return document.getElementById(id); }

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function showAuthError(msg) {
  const el = qs('auth-error');
  el.textContent = msg;
  el.style.display = 'block';
}

function clearAuthError() {
  const el = qs('auth-error');
  el.textContent = '';
  el.style.display = 'none';
}

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (res.status === 401) {
    throw new Error('AUTH_REQUIRED');
  }
  const isJson = (res.headers.get('content-type') || '').includes('application/json');
  const body = isJson ? await res.json() : await res.text();
  if (!res.ok) {
    const detail = typeof body === 'object' && body?.detail ? body.detail : body;
    throw new Error(String(detail || `HTTP ${res.status}`));
  }
  return body;
}

function playTone(freq = 520, duration = 0.05, type = 'sine') {
  if (!state.soundOn) return;
  try {
    if (!state.audioCtx) {
      state.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    const ctx = state.audioCtx;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    gain.gain.value = 0.03;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + duration);
  } catch (_) {}
}

function burstParticles(x, y, count = 10) {
  if (!state.particlesOn) return;
  const layer = qs('particles-layer');
  for (let i = 0; i < count; i++) {
    const p = document.createElement('span');
    p.className = 'particle';
    const tx = Math.round((Math.random() - 0.5) * 90) + 'px';
    const ty = Math.round((Math.random() - 0.5) * 90) + 'px';
    p.style.left = `${x}px`;
    p.style.top = `${y}px`;
    p.style.setProperty('--tx', tx);
    p.style.setProperty('--ty', ty);
    layer.appendChild(p);
    setTimeout(() => p.remove(), 650);
  }
}

function showToast(type, text, icon) {
  const icons = { success: '✅', xp: '⚡', achievement: icon || '🏆', error: '❌' };
  const container = qs('toast-container');
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.innerHTML = `<span class="t-icon">${icons[type] || '🔔'}</span><span>${text}</span>`;
  container.appendChild(t);
  setTimeout(() => {
    t.style.opacity = '0';
    t.style.transform = 'translateX(60px)';
    t.style.transition = 'all 0.3s';
    setTimeout(() => t.remove(), 300);
  }, 2600);
}

function switchAuthTab(tab) {
  document.querySelectorAll('.auth-tab').forEach((node) => {
    node.classList.toggle('active', node.dataset.tab === tab);
  });
  qs('form-login').style.display = tab === 'login' ? 'block' : 'none';
  qs('form-register').style.display = tab === 'register' ? 'block' : 'none';
  clearAuthError();
}

async function login() {
  const username = qs('login-user').value.trim();
  const password = qs('login-pass').value;
  if (!username || !password) {
    showAuthError('Заполни логин и пароль');
    return;
  }
  try {
    await api('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    playTone(660, 0.06);
    await enterApp();
  } catch (err) {
    showAuthError(err.message);
  }
}

async function register() {
  const role = qs('reg-role').value;
  const username = qs('reg-user').value.trim();
  const password = qs('reg-pass').value;
  const age = Number(qs('reg-age').value || 0);

  if (!username || !password) {
    showAuthError('Заполни обязательные поля');
    return;
  }

  const path = role === 'parent' ? '/api/v1/auth/register/parent' : '/api/v1/auth/register/student';
  const payload = role === 'parent' ? { username, password } : { username, password, age };

  try {
    await api(path, { method: 'POST', body: JSON.stringify(payload) });
    await api('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    playTone(740, 0.08);
    await enterApp();
  } catch (err) {
    showAuthError(err.message);
  }
}

async function logout() {
  try {
    await api('/api/v1/auth/logout', { method: 'POST' });
  } catch (_) {}
  state.user = null;
  state.progress = null;
  qs('app').style.display = 'none';
  qs('page-auth').classList.add('active');
  stopChatPolling();
}

function closeModal(id) { qs(id).classList.remove('open'); }

function updateHeader() {
  if (!state.progress) return;
  const u = state.progress.user;
  qs('hdr-role').textContent = u.role;
  qs('hdr-xp').textContent = u.xp;
  qs('hdr-level').textContent = u.level;
}

async function enterApp() {
  state.progress = await api('/api/v1/progress/me');
  state.user = state.progress.user;
  const coursesRes = await api('/api/v1/courses');
  state.courses = coursesRes.items || [];

  qs('page-auth').classList.remove('active');
  qs('app').style.display = 'flex';

  updateHeader();
  renderNavBars();
  renderTrackTabs();
  showPage('home');
}

function showPage(name) {
  document.querySelectorAll('#app .page').forEach((p) => p.classList.remove('active'));
  const page = qs(`page-${name}`);
  if (page) page.classList.add('active');

  document.querySelectorAll('.bottom-nav .nav-tab').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.page === name);
  });

  if (name === 'home') renderHome();
  if (name === 'profile') renderProfile();
  if (name === 'community') renderCommunity();
  if (name === 'parent') renderParentPage();
  if (name === 'admin') renderAdminPage();

  if (name === 'community') startChatPolling();
  else stopChatPolling();
}

function navButton(label, icon, page) {
  return `<button class="nav-tab" data-page="${page}"><span class="nav-icon">${icon}</span>${label}</button>`;
}

function renderNavBars() {
  const base = [navButton('Главная', '🏠', 'home'), navButton('Рейтинг', '🏆', 'community'), navButton('Профиль', '👤', 'profile')];

  const role = state.user?.role;
  if (role === 'student' || role === 'parent') {
    base.push(navButton('Семья', '👪', 'parent'));
  }
  if (role === 'admin') {
    base.push(navButton('Admin', '🛠️', 'admin'));
  }

  ['bottom-nav-home', 'bottom-nav-lesson', 'bottom-nav-profile', 'bottom-nav-community', 'bottom-nav-parent', 'bottom-nav-admin'].forEach((id) => {
    const el = qs(id);
    if (el) {
      el.innerHTML = base.join('');
      el.querySelectorAll('.nav-tab').forEach((btn) => btn.addEventListener('click', () => showPage(btn.dataset.page)));
    }
  });
}

function renderTrackTabs() {
  const tabWrap = qs('track-tabs');
  const tracks = [...new Set(state.courses.map((c) => c.track))];
  tabWrap.innerHTML = tracks
    .map((t) => `<button data-track="${t}" class="${state.track === t ? 'active' : ''}">${t.toUpperCase()}</button>`)
    .join('');
  tabWrap.querySelectorAll('button').forEach((btn) => {
    btn.addEventListener('click', () => {
      state.track = btn.dataset.track;
      renderTrackTabs();
      renderHome();
    });
  });
}

function xpToNext(level) {
  const next = XP_PER_LEVEL[Math.min(level, XP_PER_LEVEL.length - 1)];
  const prev = XP_PER_LEVEL[Math.max(0, Math.min(level - 1, XP_PER_LEVEL.length - 1))];
  return { prev, next };
}

function renderAchievements(containerId) {
  const el = qs(containerId);
  if (!el) return;
  el.innerHTML = '';
  const list = state.progress?.achievements || [];
  if (!list.length) {
    el.innerHTML = '<div style="color:var(--text2)">Пока нет достижений</div>';
    return;
  }
  list.forEach((a) => {
    const div = document.createElement('div');
    div.className = 'achievement';
    div.innerHTML = `<span class="achievement-icon">${a.icon}</span><div class="achievement-info"><div class="achievement-name">${a.name}</div><div class="achievement-desc">${a.description}</div></div>`;
    el.appendChild(div);
  });
}

function renderHome() {
  const u = state.progress.user;
  qs('home-username').textContent = u.username;
  qs('home-level').textContent = u.level;
  qs('home-xp').textContent = u.xp;
  const { prev, next } = xpToNext(u.level);
  qs('home-xp-next').textContent = next;
  const pct = Math.min(100, Math.max(0, ((u.xp - prev) / Math.max(1, (next - prev))) * 100));
  qs('home-xp-bar').style.width = `${pct}%`;

  qs('stat-lessons').textContent = u.lessons_completed;
  qs('stat-achievements').textContent = (state.progress.achievements || []).length;
  qs('stat-stars').textContent = u.stars;
  qs('stat-correct').textContent = u.correct_answers;

  const trackCourses = state.courses.filter((c) => c.track === state.track);
  const fallbackTrack = state.courses[0]?.track;
  const selectedCourses = trackCourses.length ? trackCourses : state.courses.filter((c) => c.track === fallbackTrack);
  const mergedModules = selectedCourses
    .flatMap((course) => (course.modules || []).map((mod) => ({
      ...mod,
      _course_id: course.id,
      _course_title: course.title,
    })))
    .sort((a, b) => {
      const byUnlock = Number(a.unlock_xp || 0) - Number(b.unlock_xp || 0);
      if (byUnlock !== 0) return byUnlock;
      const byCourse = Number(a._course_id || 0) - Number(b._course_id || 0);
      if (byCourse !== 0) return byCourse;
      return Number(a.order_index || 0) - Number(b.order_index || 0);
    });
  const course = selectedCourses[0] || state.courses[0];
  state.currentCourse = course ? { ...course, modules: mergedModules } : null;
  const grid = qs('modules-grid');
  grid.innerHTML = '';

  if (!course || !mergedModules.length) {
    grid.innerHTML = '<div style="color:var(--text2)">Курсы не найдены</div>';
    return;
  }

  const doneIds = new Set(state.progress.completed_lesson_ids || []);

  mergedModules.forEach((mod) => {
    const doneCnt = mod.lessons.filter((l) => doneIds.has(l.id)).length;
    const pctMod = Math.round((doneCnt / Math.max(1, mod.lessons.length)) * 100);
    const locked = u.xp < mod.unlock_xp;
    const card = document.createElement('div');
    card.className = 'module-card' + (locked ? ' locked' : '');
    card.innerHTML = locked
      ? `<div class="lock-icon">🔒</div><div class="module-emoji">${mod.emoji}</div><div class="module-title">${mod.title}</div><div class="module-desc">${mod.description}</div><div class="module-meta"><span class="tag tag-${mod.difficulty}">${mod.difficulty}</span><span style="color:var(--accent2)">🔓 ${mod.unlock_xp} XP</span></div>`
      : `<div class="module-emoji">${mod.emoji}</div><div class="module-title">${mod.title}</div><div class="module-desc">${mod.description}</div><div class="module-progress"><div class="module-progress-bar"><div class="module-progress-fill" style="width:${pctMod}%"></div></div></div><div class="module-meta"><span class="tag tag-${mod.difficulty}">${mod.difficulty}</span><span style="color:var(--text2)">${doneCnt}/${mod.lessons.length} уроков · +${mod.xp_reward} XP</span></div>`;
    if (!locked) {
      card.addEventListener('click', () => openModule(mod.id));
    }
    grid.appendChild(card);
  });

  renderAchievements('achievements-row');
}

function openModule(moduleId) {
  if (!state.currentCourse) return;
  state.currentModule = state.currentCourse.modules.find((m) => m.id === moduleId) || null;
  if (!state.currentModule) return;
  const doneIds = new Set(state.progress.completed_lesson_ids || []);
  const idx = state.currentModule.lessons.findIndex((l) => !doneIds.has(l.id));
  state.currentLessonIdx = idx >= 0 ? idx : 0;
  renderLesson();
  showPage('lesson');
}

function renderLesson() {
  const mod = state.currentModule;
  if (!mod) return;
  const lesson = mod.lessons[state.currentLessonIdx];
  if (!lesson) return;
  state.quizAnswers = {};
  state.quizSubmitted = false;

  qs('bc-module').textContent = mod.title;
  qs('lesson-emoji').textContent = lesson.emoji;
  qs('lesson-title').textContent = lesson.title;
  qs('lesson-prog-fill').style.width = `${Math.round((state.currentLessonIdx / Math.max(1, mod.lessons.length)) * 100)}%`;
  qs('lesson-prog-txt').textContent = `${state.currentLessonIdx + 1} / ${mod.lessons.length}`;

  const doneIds = new Set(state.progress.completed_lesson_ids || []);
  const sidebar = qs('lesson-sidebar-items');
  sidebar.innerHTML = '';
  mod.lessons.forEach((l, i) => {
    const item = document.createElement('div');
    const isDone = doneIds.has(l.id);
    const isActive = i === state.currentLessonIdx;
    item.className = 'lesson-item' + (isDone ? ' done' : '') + (isActive ? ' active' : '');
    item.innerHTML = `<div class="li-num">${isDone ? '✓' : i + 1}</div><span>${l.title}</span>`;
    item.addEventListener('click', () => { state.currentLessonIdx = i; renderLesson(); });
    sidebar.appendChild(item);
  });

  const body = qs('lesson-body');
  body.innerHTML = '';

  if (lesson.lesson_type === 'theory') {
    body.innerHTML = `<div class="lesson-section">${lesson.theory_html || '<p>Теория отсутствует</p>'}</div>`;
  } else if (lesson.lesson_type === 'quiz') {
    renderQuiz(lesson, body);
  } else if (lesson.lesson_type === 'practice') {
    renderPractice(lesson, body);
  }

  qs('btn-next-lesson').textContent = state.currentLessonIdx === mod.lessons.length - 1 ? 'Завершить модуль 🎉' : 'Дальше >';
}

function renderQuiz(lesson, container) {
  (lesson.questions || []).forEach((q, qi) => {
    const card = document.createElement('div');
    card.className = 'quiz-card';
    const letters = ['А', 'Б', 'В', 'Г'];
    card.innerHTML = `<div class="quiz-q">${qi + 1}. ${q.text}</div><div class="quiz-options" id="qopts-${q.id}">${(q.options || []).map((o, oi) => `<div class="quiz-option" data-question="${q.id}" data-option="${o.id}"><div class="opt-letter">${letters[oi] || ''}</div><span>${o.text}</span></div>`).join('')}</div><div class="quiz-feedback" id="qfb-${q.id}"></div>`;
    container.appendChild(card);
  });

  container.querySelectorAll('.quiz-option').forEach((el) => {
    el.addEventListener('click', () => {
      if (state.quizSubmitted) return;
      const qid = Number(el.dataset.question);
      const oid = Number(el.dataset.option);
      state.quizAnswers[qid] = oid;
      container.querySelectorAll(`#qopts-${qid} .quiz-option`).forEach((n) => n.classList.toggle('selected', n === el));
    });
  });

  const btn = document.createElement('button');
  btn.className = 'btn-primary';
  btn.textContent = 'Проверить ответы ✅';
  btn.style.cssText = 'max-width:280px;margin:0 0 20px';
  btn.addEventListener('click', () => submitQuiz(lesson));
  container.appendChild(btn);
}

async function submitQuiz(lesson) {
  if (state.quizSubmitted) return;
  state.quizSubmitted = true;
  try {
    const res = await api(`/api/v1/progress/quizzes/${lesson.id}/submit`, {
      method: 'POST',
      body: JSON.stringify({ answers: state.quizAnswers }),
    });

    (res.questions || []).forEach((q) => {
      const fb = qs(`qfb-${q.question_id}`);
      const opts = document.querySelectorAll(`#qopts-${q.question_id} .quiz-option`);
      opts.forEach((el) => {
        const optionId = Number(el.dataset.option);
        if (optionId === q.correct_option_id) el.classList.add('correct');
        else if (optionId === q.picked_option_id && !q.is_correct) el.classList.add('wrong');
      });
      fb.style.display = 'block';
      fb.className = q.is_correct ? 'quiz-feedback correct' : 'quiz-feedback wrong';
      fb.textContent = q.is_correct ? '✅ Правильно!' : '❌ Неверно';
    });

    await reloadProgress();
    handleCompletionEffects(res.completion, res.new_achievements || []);
    showToast('xp', `📊 Результат: ${res.score}/${res.max_score}`);
  } catch (err) {
    showToast('error', err.message);
  }
}

function defaultStarterForLanguage(language) {
  if (language === 'python') {
    return (
      'name = "Programmer"\n' +
      'xp = 10\n' +
      'print(f"Привет, {name}! XP: {xp}")\n'
    );
  }
  if (language === 'javascript') {
    return (
      "const name = 'Programmer';\n" +
      'const xp = 10;\n' +
      "console.log(`Привет, ${name}! XP: ${xp}`);\n"
    );
  }
  return (
    "using System;\n\n" +
    'string name = "Programmer";\n' +
    "int xp = 10;\n" +
    'Console.WriteLine($"Привет, {name}! XP: {xp}");\n'
  );
}

function renderPractice(lesson, container) {
  const practiceLang = lesson.practice_language || state.track || 'python';
  const starterCode = (lesson.practice_starter || '').trim() || defaultStarterForLanguage(practiceLang);
  const taskText = lesson.practice_task || 'Выполни задание в редакторе';
  const hintText = lesson.practice_hint || 'Используй знания из теории';
  const csharpNote = practiceLang === 'csharp'
    ? '<div class="info-box"><span class="ib-icon">ℹ️</span><p><strong>C#:</strong> можно писать короткий фрагмент, полный шаблон файла не обязателен.</p></div>'
    : '';

  container.innerHTML = `
    <div class="lesson-section"><h3>🎯 Задание</h3><p>${escapeHtml(taskText)}</p></div>
    <div class="code-editor-wrap">
      <div class="editor-header"><span>🧪 ${practiceLang} редактор</span><button class="btn-run" id="run-practice">▶ Запустить</button></div>
      <textarea class="code-textarea" id="practice-editor" rows="8"></textarea>
      <div class="editor-output" id="practice-output">> Нажми "Запустить" чтобы увидеть результат</div>
    </div>
    ${csharpNote}
    <div class="info-box"><span class="ib-icon">💡</span><p><strong>Подсказка:</strong> ${escapeHtml(hintText)}</p></div>
  `;
  qs('practice-editor').value = starterCode;

  qs('run-practice').addEventListener('click', async () => {
    const code = qs('practice-editor').value;
    const out = qs('practice-output');
    out.textContent = '⏳ Выполнение...';
    out.className = 'editor-output';
    try {
      const res = await api('/api/v1/practice/run', {
        method: 'POST',
        body: JSON.stringify({ language: lesson.practice_language || state.track, code, lesson_id: lesson.id }),
      });
      out.textContent = (res.stdout || '') + (res.stderr ? `\n${res.stderr}` : '');
      if (!out.textContent.trim()) out.textContent = '(нет вывода)';
      if (res.status !== 'ok') out.className = 'editor-output error';

      if (res.lesson_check_passed) {
        showToast('success', '✅ Практика засчитана');
        await reloadProgress();
        handleCompletionEffects(res.completion, res.new_achievements || []);
      }
    } catch (err) {
      out.textContent = `❌ ${err.message}`;
      out.className = 'editor-output error';
    }
  });
}

async function handleCompletionEffects(completion, newAchievements) {
  if (completion && !completion.already_completed) {
    playTone(840, 0.07, 'triangle');
    showToast('xp', `⚡ +${(completion.lesson_xp || 0) + (completion.module_bonus_xp || 0)} XP`);
    qs('modal-ld-title').textContent = 'Урок пройден!';
    qs('modal-ld-text').textContent = 'Отличная работа!';
    qs('modal-ld-xp').textContent = (completion.lesson_xp || 0) + (completion.module_bonus_xp || 0);
    qs('modal-lesson-done').classList.add('open');
    if (completion.level_up) {
      qs('modal-new-level').textContent = state.progress.user.level;
      setTimeout(() => qs('modal-levelup').classList.add('open'), 450);
      playTone(980, 0.09, 'square');
    }
  }
  (newAchievements || []).forEach((a) => {
    showToast('achievement', `🏆 ${a.name}`, a.icon);
    playTone(750, 0.05);
  });
}

async function nextLesson() {
  const mod = state.currentModule;
  if (!mod) return;
  const lesson = mod.lessons[state.currentLessonIdx];
  if (!lesson) return;

  try {
    const res = await api(`/api/v1/progress/lessons/${lesson.id}/complete`, { method: 'POST' });
    await reloadProgress();
    await handleCompletionEffects(res.completion, res.new_achievements || []);
  } catch (_) {}

  if (state.currentLessonIdx < mod.lessons.length - 1) {
    state.currentLessonIdx += 1;
    renderLesson();
  } else {
    showPage('home');
  }
}

function renderProfile() {
  const u = state.progress.user;
  qs('profile-name').textContent = u.username;
  qs('profile-joined').textContent = `Дата регистрации: ${new Date(u.created_at).toLocaleDateString('ru-RU')}`;
  qs('profile-xp').textContent = u.xp;
  qs('profile-level').textContent = u.level;
  qs('profile-stars').textContent = u.stars;
  renderAchievements('profile-achievements');

  const box = qs('profile-modules');
  box.innerHTML = '';
  const moduleToTrack = new Map();
  state.courses.forEach((course) => {
    (course.modules || []).forEach((mod) => {
      moduleToTrack.set(mod.id, (course.track || '').toUpperCase());
    });
  });
  state.progress.module_progress.forEach((m) => {
    const trackLabel = moduleToTrack.get(m.module_id) || 'TRACK';
    const div = document.createElement('div');
    div.style.cssText = 'background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:12px;';
    div.innerHTML = `<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px"><span style="font-weight:700">${m.module_title}</span><span style="font-size:10px;font-weight:800;color:var(--accent2);border:1px solid rgba(255,204,2,0.35);border-radius:999px;padding:2px 8px">${trackLabel}</span></div><div style="height:8px;background:var(--bg2);border-radius:8px;overflow:hidden"><div style="height:100%;width:${m.percent}%;background:linear-gradient(90deg,var(--accent),var(--accent2));"></div></div><div style="font-size:12px;color:var(--text2);margin-top:4px">${m.completed_lessons}/${m.total_lessons}</div>`;
    box.appendChild(div);
  });
}

async function renderCommunity() {
  const lb = await api('/api/v1/community/leaderboard');
  const table = qs('leaderboard-table');
  table.innerHTML = '';
  (lb.items || []).forEach((u) => {
    const row = document.createElement('div');
    row.className = 'lb-row' + (u.user_id === state.user.id ? ' me' : '');
    row.innerHTML = `<div class="lb-rank">${u.rank <= 3 ? (u.rank === 1 ? '🥇' : u.rank === 2 ? '🥈' : '🥉') : u.rank}</div><div class="lb-avatar">👤</div><div class="lb-name">${u.username}</div><div class="lb-level">Ур. ${u.level}</div><div class="lb-xp">${u.xp} XP</div>`;
    table.appendChild(row);
  });

  const feed = await api('/api/v1/community/feed');
  qs('feed-list').innerHTML = (feed.items || []).map((p) => `<div class="feed-item"><div class="feed-meta">${p.username} · ${new Date(p.created_at).toLocaleString('ru-RU')}</div><div>${p.content}</div></div>`).join('') || '<div style="color:var(--text2)">Пока пусто</div>';

  const chat = await api('/api/v1/community/chat');
  renderChatItems(chat.items || []);
}

function renderChatItems(items) {
  const box = qs('chat-list');
  box.innerHTML = items.map((m) => `<div class="chat-item"><div class="chat-meta">${m.username} · ${new Date(m.created_at).toLocaleTimeString('ru-RU')}</div><div>${m.content}</div></div>`).join('') || '<div style="color:var(--text2)">Нет сообщений</div>';
}

function startChatPolling() {
  if (state.chatPollTimer) return;
  state.chatPollTimer = setInterval(async () => {
    try {
      const chat = await api('/api/v1/community/chat');
      renderChatItems(chat.items || []);
    } catch (_) {}
  }, 5000);
}

function stopChatPolling() {
  if (state.chatPollTimer) {
    clearInterval(state.chatPollTimer);
    state.chatPollTimer = null;
  }
}

async function renderParentPage() {
  const isParent = state.user.role === 'parent';
  const isStudent = state.user.role === 'student';
  const parentGrid = qs('parent-panel-grid');
  const parentProgressCard = qs('parent-progress-card');
  const studentNote = qs('student-family-note');
  const progressBox = qs('parent-child-progress');
  qs('student-incoming-wrap').style.display = isStudent ? 'block' : 'none';

  if (parentGrid) parentGrid.style.display = isParent ? 'grid' : 'none';
  if (parentProgressCard) parentProgressCard.style.display = isParent ? 'block' : 'none';
  if (studentNote) studentNote.style.display = isStudent ? 'block' : 'none';

  if (isParent) {
    const list = await api('/api/v1/parent/children');
    const children = list.items || [];
    const el = qs('parent-children');
    el.innerHTML = '';
    children.forEach((c) => {
      const btn = document.createElement('button');
      btn.className = 'parent-child-btn';
      btn.dataset.childId = String(c.id);
      btn.innerHTML = `<div>${escapeHtml(c.username)}</div><div style="color:var(--text2);font-size:11px;margin-top:2px">ур. ${c.level} · ${c.xp} XP</div>`;
      btn.addEventListener('click', async () => {
        await loadParentChildProgress(c.id);
      });
      el.appendChild(btn);
    });
    if (!children.length) {
      el.innerHTML = '<span style="color:var(--text2)">Нет привязанных детей</span>';
      progressBox.className = 'child-progress-empty';
      progressBox.textContent = 'Добавьте ребёнка и выберите его, чтобы увидеть прогресс.';
    } else {
      const selected = children.some((c) => c.id === state.parentSelectedChildId)
        ? state.parentSelectedChildId
        : children[0].id;
      await loadParentChildProgress(selected);
    }
  }

  if (isStudent) {
    const incoming = await api('/api/v1/parent/requests/incoming');
    const listEl = qs('incoming-requests');
    listEl.innerHTML = '';
    (incoming.items || []).forEach((r) => {
      const row = document.createElement('div');
      row.className = 'request-item';
      row.innerHTML = `<span>${r.parent_username}</span><div><button class="btn-mini" data-action="accept">Принять</button> <button class="btn-mini" data-action="reject">Отклонить</button></div>`;
      row.querySelector('[data-action="accept"]').addEventListener('click', async () => { await api(`/api/v1/parent/requests/${r.id}/accept`, { method: 'POST' }); renderParentPage(); });
      row.querySelector('[data-action="reject"]').addEventListener('click', async () => { await api(`/api/v1/parent/requests/${r.id}/reject`, { method: 'POST' }); renderParentPage(); });
      listEl.appendChild(row);
    });
    if (!(incoming.items || []).length) listEl.innerHTML = '<span style="color:var(--text2)">Нет входящих запросов</span>';
  }

  if (!isParent && !isStudent) {
    qs('student-incoming-wrap').style.display = 'none';
    if (studentNote) studentNote.style.display = 'none';
  }
}

function activityLabel(kind) {
  if (kind === 'quiz') return '🧠 Тест';
  if (kind === 'lesson_complete') return '📘 Урок';
  return '🛠️ Практика';
}

function updateParentChildButtonsActive() {
  const current = String(state.parentSelectedChildId || '');
  document.querySelectorAll('.parent-child-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.childId === current);
  });
}

function renderParentChildProgress(progress) {
  const user = progress.user || {};
  const achievements = progress.achievements || [];
  const modules = progress.module_progress || [];
  const recent = progress.recent_activity || [];
  const moduleHtml = modules.map((m) => `
    <div class="child-module-row">
      <div class="child-module-head">
        <span class="child-module-title">${escapeHtml(m.module_title)}</span>
        <span class="child-module-meta">${m.completed_lessons}/${m.total_lessons}</span>
      </div>
      <div class="child-module-bar"><span style="width:${Math.max(0, Math.min(100, Number(m.percent) || 0))}%"></span></div>
    </div>
  `).join('');

  const recentHtml = recent.length
    ? recent.map((item) => {
      const scoreText = item.max_score ? `${item.score}/${item.max_score}` : `${item.score}`;
      return `
        <div class="child-activity-item">
          <div class="child-activity-left">${activityLabel(item.kind)} · урок #${item.lesson_id || '-'}</div>
          <div class="child-activity-right">${escapeHtml(scoreText)} · ${new Date(item.created_at).toLocaleString('ru-RU')}</div>
        </div>
      `;
    }).join('')
    : '<div class="child-progress-empty">Активности пока нет</div>';

  return `
    <div class="child-progress-wrap">
      <div class="child-progress-head">
        <div>
          <div class="child-progress-title">${escapeHtml(user.username || 'Ученик')}</div>
          <div class="child-progress-sub">Последнее обновление: ${new Date().toLocaleString('ru-RU')}</div>
        </div>
        <div class="child-progress-badges">
          <span class="child-badge">Возраст: ${user.age ?? '—'}</span>
          <span class="child-badge">Достижения: ${achievements.length}</span>
        </div>
      </div>
      <div class="child-progress-stats">
        <div class="child-stat"><div class="val">${user.xp || 0}</div><div class="lbl">XP</div></div>
        <div class="child-stat"><div class="val">${user.level || 1}</div><div class="lbl">Уровень</div></div>
        <div class="child-stat"><div class="val">${user.lessons_completed || 0}</div><div class="lbl">Уроков</div></div>
        <div class="child-stat"><div class="val">${user.correct_answers || 0}</div><div class="lbl">Верных ответов</div></div>
      </div>
      <div>
        <div class="section-title" style="font-size:14px;margin-bottom:8px"><span class="dot"></span> Прогресс по модулям</div>
        <div class="child-modules-grid">${moduleHtml || '<div class="child-progress-empty">Нет модулей</div>'}</div>
      </div>
      <div>
        <div class="section-title" style="font-size:14px;margin-bottom:8px"><span class="dot"></span> Последняя активность</div>
        <div class="child-activity-list">${recentHtml}</div>
      </div>
    </div>
  `;
}

async function loadParentChildProgress(childId) {
  state.parentSelectedChildId = Number(childId);
  updateParentChildButtonsActive();
  const box = qs('parent-child-progress');
  box.className = 'child-progress-empty';
  box.textContent = 'Загрузка активности...';
  try {
    const progress = await api(`/api/v1/parent/children/${childId}/progress`);
    box.className = '';
    box.innerHTML = renderParentChildProgress(progress);
    updateParentChildButtonsActive();
  } catch (err) {
    box.className = 'child-progress-empty';
    box.textContent = `Не удалось загрузить активность: ${err.message}`;
  }
}

function flattenAdminModules(courses) {
  const items = [];
  (courses || []).forEach((course) => {
    (course.modules || []).forEach((module) => {
      items.push({ ...module, course_id: course.id, course_title: course.title, course_track: course.track });
    });
  });
  return items;
}

function flattenAdminQuizLessons(courses) {
  const rows = [];
  flattenAdminModules(courses).forEach((module) => {
    (module.lessons || []).forEach((lesson) => {
      if (lesson.lesson_type === 'quiz') {
        rows.push({
          id: lesson.id,
          title: lesson.title,
          module_id: module.id,
          module_title: module.title,
          course_title: module.course_title,
          questions: lesson.questions || [],
        });
      }
    });
  });
  return rows;
}

function findAdminCourseById(courseId) {
  return (state.adminCourses || []).find((c) => c.id === Number(courseId)) || null;
}

function findAdminModuleById(moduleId) {
  for (const course of state.adminCourses || []) {
    for (const module of course.modules || []) {
      if (module.id === Number(moduleId)) return { course, module };
    }
  }
  return null;
}

function nextModuleOrder(course) {
  const maxOrder = Math.max(0, ...((course?.modules || []).map((m) => Number(m.order_index) || 0)));
  return maxOrder + 1;
}

function nextLessonOrder(module) {
  const maxOrder = Math.max(0, ...((module?.lessons || []).map((l) => Number(l.order_index) || 0)));
  return maxOrder + 1;
}

function refreshAdminSummary(courses) {
  const modulesCount = (courses || []).reduce((acc, c) => acc + (c.modules || []).length, 0);
  const lessonsCount = (courses || []).reduce(
    (acc, c) => acc + (c.modules || []).reduce((s, m) => s + (m.lessons || []).length, 0),
    0,
  );
  qs('admin-summary').innerHTML = `
    <span class="admin-chip">Курсов: ${courses.length}</span>
    <span class="admin-chip">Модулей: ${modulesCount}</span>
    <span class="admin-chip">Уроков: ${lessonsCount}</span>
  `;
}

function refreshAdminSelectors(courses) {
  const courseSelect = qs('admin-module-course-id');
  courseSelect.innerHTML = (courses || []).map((c) => `<option value="${c.id}">#${c.id} · ${escapeHtml(c.title)} (${c.track})</option>`).join('');

  const modules = flattenAdminModules(courses);
  const moduleSelect = qs('admin-lesson-module-id');
  moduleSelect.innerHTML = modules.map((m) => `<option value="${m.id}">#${m.id} · ${escapeHtml(m.course_title)} / ${escapeHtml(m.title)}</option>`).join('');

  const quizLessons = flattenAdminQuizLessons(courses);
  const questionLessonSelect = qs('admin-question-lesson-id');
  questionLessonSelect.innerHTML = quizLessons.map((l) => `<option value="${l.id}">#${l.id} · ${escapeHtml(l.course_title)} / ${escapeHtml(l.module_title)} / ${escapeHtml(l.title)}</option>`).join('');

  if (!courses.length) {
    courseSelect.innerHTML = '<option value="">Сначала создайте курс</option>';
  }
  if (!modules.length) {
    moduleSelect.innerHTML = '<option value="">Сначала создайте модуль</option>';
  }
  if (!quizLessons.length) {
    questionLessonSelect.innerHTML = '<option value="">Сначала создайте quiz-урок</option>';
  }
}

function renderAdminCourseTree(courses) {
  if (!(courses || []).length) {
    qs('admin-courses-list').innerHTML = '<div style="color:var(--text2)">Нет курсов</div>';
    return;
  }
  qs('admin-courses-list').innerHTML = `
    <div class="admin-tree">
      ${(courses || []).map((course) => `
        <div class="admin-course-item">
          <div class="admin-course-head">
            <div class="admin-course-title">#${course.id} · ${escapeHtml(course.title)}</div>
            <span class="admin-track-badge">${course.track}</span>
          </div>
          <div class="admin-meta">${escapeHtml(course.description || '')}</div>
          <div class="admin-modules" style="margin-top:8px">
            ${(course.modules || []).map((module) => `
              <div class="admin-module-item">
                <div class="admin-module-head">
                  <div class="admin-module-title">#${module.id} ${escapeHtml(module.emoji || '📦')} ${escapeHtml(module.title)}</div>
                  <div class="admin-meta">order ${module.order_index}</div>
                </div>
                <div class="admin-meta">unlock ${module.unlock_xp} XP · reward ${module.xp_reward} XP · ${module.difficulty}</div>
                <div class="admin-lessons" style="margin-top:6px">
                  ${(module.lessons || []).map((lesson) => `
                    <div class="admin-lesson-item">
                      #${lesson.id} · ${escapeHtml(lesson.title)} · ${lesson.lesson_type} · order ${lesson.order_index}
                    </div>
                  `).join('') || '<div class="admin-lesson-item">Уроков пока нет</div>'}
                </div>
              </div>
            `).join('') || '<div class="admin-module-item">Модулей пока нет</div>'}
          </div>
        </div>
      `).join('')}
    </div>
  `;
}

function syncLessonLanguageToModule() {
  const moduleId = Number(qs('admin-lesson-module-id').value);
  if (!moduleId) return;
  const found = findAdminModuleById(moduleId);
  if (!found) return;
  qs('admin-lesson-language').value = found.course.track;
}

function syncLessonFormState() {
  const type = qs('admin-lesson-type').value;
  const starter = qs('admin-lesson-starter');
  const hint = qs('admin-lesson-hint');
  const lang = qs('admin-lesson-language');
  const body = qs('admin-lesson-body');
  const isPractice = type === 'practice';
  starter.disabled = !isPractice;
  hint.disabled = !isPractice;
  lang.disabled = !isPractice;
  body.placeholder = type === 'theory'
    ? 'HTML/текст теории'
    : type === 'practice'
      ? 'Текст задания для практики'
      : 'Краткое описание quiz-урока';
}

async function renderAdminPage() {
  if (state.user.role !== 'admin') return;
  const res = await api('/api/v1/admin/courses');
  state.adminCourses = res.items || [];
  refreshAdminSummary(state.adminCourses);
  refreshAdminSelectors(state.adminCourses);
  renderAdminCourseTree(state.adminCourses);
  syncLessonLanguageToModule();
  syncLessonFormState();
}

async function reloadProgress() {
  state.progress = await api('/api/v1/progress/me');
  state.user = state.progress.user;
  updateHeader();
}

async function initApp() {
  qs('reg-role').addEventListener('change', () => {
    qs('reg-age-wrap').style.display = qs('reg-role').value === 'student' ? 'block' : 'none';
  });
  qs('btn-login').addEventListener('click', login);
  qs('btn-register').addEventListener('click', register);
  qs('btn-logout').addEventListener('click', logout);
  qs('logo-home').addEventListener('click', () => showPage('home'));
  qs('btn-open-profile').addEventListener('click', () => showPage('profile'));
  qs('bc-back-home').addEventListener('click', () => showPage('home'));
  qs('btn-back-home').addEventListener('click', () => showPage('home'));
  qs('btn-next-lesson').addEventListener('click', nextLesson);
  qs('btn-close-levelup').addEventListener('click', () => closeModal('modal-levelup'));
  qs('btn-close-lesson-done').addEventListener('click', () => closeModal('modal-lesson-done'));

  document.querySelectorAll('.auth-tab').forEach((btn) => btn.addEventListener('click', () => switchAuthTab(btn.dataset.tab)));

  qs('feed-send').addEventListener('click', async () => {
    const content = qs('feed-input').value.trim();
    if (!content) return;
    await api('/api/v1/community/feed', { method: 'POST', body: JSON.stringify({ content }) });
    qs('feed-input').value = '';
    renderCommunity();
  });
  qs('chat-send').addEventListener('click', async () => {
    const content = qs('chat-input').value.trim();
    if (!content) return;
    await api('/api/v1/community/chat', { method: 'POST', body: JSON.stringify({ content }) });
    qs('chat-input').value = '';
    renderCommunity();
  });

  qs('parent-send-request').addEventListener('click', async () => {
    const username = qs('parent-child-username').value.trim();
    if (!username) return;
    try {
      await api('/api/v1/parent/requests', { method: 'POST', body: JSON.stringify({ child_username: username }) });
      qs('parent-child-username').value = '';
      showToast('success', 'Запрос отправлен');
      renderParentPage();
    } catch (err) { showToast('error', err.message); }
  });

  qs('admin-lesson-type').addEventListener('change', syncLessonFormState);
  qs('admin-lesson-module-id').addEventListener('change', syncLessonLanguageToModule);

  qs('admin-create-course').addEventListener('click', async () => {
    const payload = {
      track: qs('admin-course-track').value,
      title: qs('admin-course-title').value.trim(),
      description: qs('admin-course-desc').value.trim(),
      is_published: true,
    };
    if (!payload.title || !payload.description) {
      showToast('error', 'Заполни название и описание курса');
      return;
    }
    try {
      await api('/api/v1/admin/courses', { method: 'POST', body: JSON.stringify(payload) });
      qs('admin-course-title').value = '';
      qs('admin-course-desc').value = '';
      showToast('success', 'Курс создан');
      await renderAdminPage();
    } catch (err) {
      showToast('error', err.message);
    }
  });

  qs('admin-create-module').addEventListener('click', async () => {
    const courseId = Number(qs('admin-module-course-id').value);
    const course = findAdminCourseById(courseId);
    const payload = {
      course_id: courseId,
      title: qs('admin-module-title').value.trim(),
      description: qs('admin-module-desc').value.trim(),
      difficulty: qs('admin-module-difficulty').value,
      color: qs('admin-module-color').value || '#06d6a0',
      emoji: qs('admin-module-emoji').value.trim() || '📦',
      unlock_xp: Number(qs('admin-module-unlock-xp').value || 0),
      xp_reward: Number(qs('admin-module-xp-reward').value || 20),
      order_index: nextModuleOrder(course),
    };
    if (!courseId || !payload.title || !payload.description) {
      showToast('error', 'Заполни курс, название и описание модуля');
      return;
    }
    try {
      await api('/api/v1/admin/modules', { method: 'POST', body: JSON.stringify(payload) });
      qs('admin-module-title').value = '';
      qs('admin-module-desc').value = '';
      showToast('success', 'Модуль создан');
      await renderAdminPage();
    } catch (err) {
      showToast('error', err.message);
    }
  });

  qs('admin-create-lesson').addEventListener('click', async () => {
    const t = qs('admin-lesson-type').value;
    const moduleId = Number(qs('admin-lesson-module-id').value);
    const found = findAdminModuleById(moduleId);
    const title = qs('admin-lesson-title').value.trim();
    const body = qs('admin-lesson-body').value.trim();
    const starter = qs('admin-lesson-starter').value;
    const hint = qs('admin-lesson-hint').value.trim();
    const lessonLanguage = qs('admin-lesson-language').value;
    if (!moduleId || !title) {
      showToast('error', 'Выбери модуль и укажи название урока');
      return;
    }

    const payload = {
      module_id: moduleId,
      title,
      lesson_type: t,
      emoji: t === 'theory' ? '📖' : t === 'quiz' ? '❓' : '🧪',
      xp_reward: Number(qs('admin-lesson-xp-reward').value || 10),
      order_index: nextLessonOrder(found?.module),
      theory_html: t === 'theory' ? body : (t === 'quiz' ? body : null),
      practice_task: t === 'practice' ? body : null,
      practice_starter: t === 'practice' ? starter : null,
      practice_hint: t === 'practice' ? hint : null,
      practice_language: t === 'practice' ? (lessonLanguage || found?.course.track || 'python') : null,
    };

    if (t === 'theory' && !body) {
      showToast('error', 'Для theory нужен текст теории');
      return;
    }
    if (t === 'practice' && !body) {
      showToast('error', 'Для practice нужен текст задания');
      return;
    }

    try {
      await api('/api/v1/admin/lessons', { method: 'POST', body: JSON.stringify(payload) });
      qs('admin-lesson-title').value = '';
      qs('admin-lesson-body').value = '';
      qs('admin-lesson-starter').value = '';
      qs('admin-lesson-hint').value = '';
      showToast('success', t === 'quiz' ? 'Quiz-урок создан, добавь вопросы' : 'Урок создан');
      await renderAdminPage();
    } catch (err) {
      showToast('error', err.message);
    }
  });

  qs('admin-create-question').addEventListener('click', async () => {
    const lessonId = Number(qs('admin-question-lesson-id').value);
    const text = qs('admin-question-text').value.trim();
    const optionsRaw = [
      qs('admin-question-opt1').value.trim(),
      qs('admin-question-opt2').value.trim(),
      qs('admin-question-opt3').value.trim(),
      qs('admin-question-opt4').value.trim(),
    ];
    const options = optionsRaw
      .map((o, idx) => ({ text: o, idx: idx + 1 }))
      .filter((o) => o.text.length > 0);
    const correct = Number(qs('admin-question-correct').value || 1);
    if (!lessonId || !text) {
      showToast('error', 'Выбери quiz-урок и введи вопрос');
      return;
    }
    if (options.length < 2) {
      showToast('error', 'Нужно минимум 2 непустых варианта');
      return;
    }
    const correctOption = options.find((o) => o.idx === correct);
    if (!correctOption) {
      showToast('error', 'Укажи правильный вариант среди заполненных');
      return;
    }

    const quizLessons = flattenAdminQuizLessons(state.adminCourses);
    const lesson = quizLessons.find((x) => x.id === lessonId);
    const payload = {
      lesson_id: lessonId,
      text,
      order_index: (lesson?.questions?.length || 0) + 1,
      options: options.map((o, idx) => ({
        text: o.text,
        is_correct: o.idx === correct,
        order_index: idx + 1,
      })),
    };
    try {
      await api('/api/v1/admin/questions', { method: 'POST', body: JSON.stringify(payload) });
      qs('admin-question-text').value = '';
      qs('admin-question-opt1').value = '';
      qs('admin-question-opt2').value = '';
      qs('admin-question-opt3').value = '';
      qs('admin-question-opt4').value = '';
      qs('admin-question-correct').value = '1';
      showToast('success', 'Вопрос добавлен');
      await renderAdminPage();
    } catch (err) {
      showToast('error', err.message);
    }
  });

  qs('toggle-sound').addEventListener('change', (e) => { state.soundOn = e.target.checked; });
  qs('toggle-particles').addEventListener('change', (e) => { state.particlesOn = e.target.checked; });

  document.addEventListener('click', (e) => {
    const target = e.target.closest('button');
    if (!target) return;
    playTone(560, 0.03);
    burstParticles(e.clientX, e.clientY, 8);
  });

  try {
    await enterApp();
  } catch (_) {
    qs('page-auth').classList.add('active');
  }
}

initApp();


