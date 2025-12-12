import "./App.css";

export default function ArchitecturePage() {
  return (
    <div className="container center-content">
      <header className="hero">
        <div className="title">
          <h1>07.03.01 — Архитектура (профиль «Архитектура»)</h1>
          <p className="subtitle">
            Бакалавриат — очная форма, срок 5 лет. Обучение на русском языке. Бюджетные и контрактные места.
          </p>

          <div className="chips">
            <span className="chip">🎓 Бакалавриат</span>
            <span className="chip">🕒 5 лет</span>
            <span className="chip">🗣 Русский</span>
            <span className="chip">🏛 Аккредитация — бессрочно</span>
          </div>

          <div className="cards top-gap">
            <div className="card">
              <h3>Руководитель программы</h3>
              <p>Канд. архитектуры, доцент — Капустин Петр Владимирович</p>
            </div>
            <div className="card">
              <h3>Контакты</h3>
              <p>г. Воронеж, ул. 20-летия Октября, д.84, ауд.1523<br/>тел. +7 (473) 271-54-21</p>
            </div>
          </div>
        </div>

        <div className="video">
          <div className="placeholder">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none">
              <rect x="2" y="2" width="20" height="20" rx="4" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
              <path d="M10 8l6 4-6 4V8z" fill="white" />
            </svg>
          </div>
        </div>
      </header>

      <main className="main">
        <section className="panel">
          <div className="center-content">
            <h2>О программе</h2>
            <p className="muted">Программа готовит архитекторов, способных вести проектно‑конструкторскую деятельность: от предпроектного анализа и концепции до авторского надзора за строительством. Учебный план сочетает художественные и инженерные дисциплины, включая градостроительство и ресурсосберегающие технологии.</p>

            <h3>Почему стоит выбрать эту программу</h3>
            <ul className="muted">
              <li>Интенсивная студенческая практика и портфолио</li>
              <li>Проекты в сотрудничестве с городскими архитекторами</li>
              <li>Навыки BIM и цифровой визуализации</li>
              <li>Подготовка к авторскому надзору и работе при строительстве</li>
            </ul>

            <h3>Структура обучения (кратко)</h3>
            <div className="structure">
              <div className="card course-card"> 
                <strong>1–2 курс</strong>
                <p className="muted">Композиция, рисунок, история архитектуры</p>
              </div>
              <div className="card course-card">
                <strong>3–4 курс</strong>
                <p className="muted">Проектирование, градостроительство, рабочая документация</p>
              </div>
              <div className="card course-card">
                <strong>5 курс</strong>
                <p className="muted">Дипломный проект и практика</p>
              </div>
            </div>

            <h3>Основные дисциплины</h3>
            <details open>
              <summary>Посмотреть список дисциплин</summary>
              <div className="disc-list">
                <div className="disc-item">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M3 21l18-18" stroke="var(--brand-blue)" strokeWidth="1.6"/><path d="M3 3l18 18" stroke="var(--brand-blue)" strokeWidth="1.6"/></svg>
                  <p>Архитектурное проектирование</p>
                </div>
                <div className="disc-item">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="var(--brand-blue)" strokeWidth="1.6"/><path d="M12 6v12M6 12h12" stroke="var(--brand-blue)" strokeWidth="1.6"/></svg>
                  <p>Теория архитектуры</p>
                </div>
                <div className="disc-item">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><rect x="4" y="4" width="16" height="16" stroke="var(--brand-blue)" strokeWidth="1.6"/><path d="M4 12h16" stroke="var(--brand-blue)" strokeWidth="1.6"/></svg>
                  <p>История архитектуры</p>
                </div>
                <div className="disc-item">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><polygon points="12,2 22,22 2,22" stroke="var(--brand-blue)" strokeWidth="1.6" fill="none"/></svg>
                  <p>Методология проектирования</p>
                </div>
                <div className="disc-item">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M2 12h20" stroke="var(--brand-blue)" strokeWidth="1.6"/><circle cx="12" cy="12" r="4" stroke="var(--brand-blue)" strokeWidth="1.6"/></svg>
                  <p>Типология зданий</p>
                </div>
                <div className="disc-item">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><rect x="3" y="6" width="18" height="12" stroke="var(--brand-blue)" strokeWidth="1.6"/><path d="M3 12h18" stroke="var(--brand-blue)" strokeWidth="1.6"/></svg>
                  <p>Рабочее проектирование</p>
                </div>
                <div className="disc-item">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M4 20h16v-8L12 4 4 12v8z" stroke="var(--brand-blue)" strokeWidth="1.6" fill="none"/><line x1="12" y1="4" x2="12" y2="20" stroke="var(--brand-blue)" strokeWidth="1.6"/></svg>
                  <p>Основы теории градостроительства</p>
                </div>
                <div className="disc-item">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><path d="M2 12h20" stroke="var(--brand-blue)" strokeWidth="1.6"/><circle cx="16" cy="12" r="2" stroke="var(--brand-blue)" strokeWidth="1.6"/><circle cx="8" cy="12" r="2" stroke="var(--brand-blue)" strokeWidth="1.6"/></svg>
                  <p>Транспорт в планировке городов</p>
                </div>
                <div className="disc-item">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none"><polygon points="12,2 22,22 2,22" stroke="var(--brand-blue)" strokeWidth="1.6" fill="none"/><circle cx="12" cy="12" r="3" stroke="var(--brand-blue)" strokeWidth="1.6"/></svg>
                  <p>Ресурсосберегающие технологии в архитектуре и градостроительстве</p>
                </div>
              </div>
            </details>

            <h3>Практика студентов</h3>
            <p className="muted">Производственную практику студенты проходят в профильных организациях:</p>
            <div className="partners">
              <div className="partner">Управление Главного архитектора Администрации г. Воронеж</div>
              <div className="partner">ООО "Архитектурная мастерская Сорокина", Воронеж</div>
              <div className="partner">ООО "Архстрой", Воронеж</div>
              <div className="partner">ООО Проектно-строительная фирма "ЭРЛИТ", Воронеж</div>
              <div className="partner">Архитектурное бюро "Трибар", Воронеж</div>
              <div className="partner">Архитектурное бюро "2 Портала", Воронеж</div>
              <div className="partner">ООО ПТМ, Воронеж</div>
              <div className="partner">ООО "HEФ", Курск</div>
              <div className="partner">ООО ПТАМ №2, Воронеж</div>
              <div className="partner">ООО ПТАМ 3, Воронеж</div>
              <div className="partner">ООО ПТАМ Виссарионова, Москва</div>
              <div className="partner">ООО "Архитектурная студия Контраст", Воронеж</div>
              <div className="partner">ООО "Эко-Проект ЦЧР", Воронеж</div>
              <div className="partner">ВОПОО "Наш регион", Воронеж</div>
            </div>

            <h3>Трудоустройство</h3>
            <p className="muted">Области профессиональной деятельности выпускников: архитектура, проектирование, дизайн (в сфере архитектурного проектирования).</p>
            <p className="muted">Объектами профессиональной деятельности выпускников, освоивших программу бакалавриата, являются искусственная материально-пространственная среда жизнедеятельности человека и общества с ее компонентами – населенными местами, городской средой, зданиями, сооружениями и их комплексами с системами жизнеобеспечения, безопасности, ландшафтами.</p>

            <h3>Кадровое обеспечение образовательной программы</h3>
            <p className="muted">В реализации образовательной программы задействовано более 70 преподавателей из числа научно-педагогических работников ВГТУ и специалистов проектных и производственных организаций строительного комплекса, привлекаемых к реализации ОПОП на условиях гражданско-правового договора. Из них 3 доктора наук, профессоры и 25 кандидатов наук, доцентов.</p>
          </div>
        </section>
      </main>
    </div>
  );
}
