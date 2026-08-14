import {
  ArrowRight,
  CalendarDays,
  Check,
  ChevronRight,
  CircleAlert,
  MapPin,
  RotateCcw,
  Search,
  Sparkles,
  UtensilsCrossed,
  X,
} from "lucide-react";
import { FormEvent, useEffect, useId, useRef, useState } from "react";
import {
  ApiError,
  type Meal,
  type School,
  getMeals,
  searchSchools,
} from "./api";

type RequestState = "idle" | "loading" | "success" | "empty" | "error";

const dateFormatter = new Intl.DateTimeFormat("ko-KR", {
  month: "long",
  day: "numeric",
  weekday: "short",
});

function localDate(offsetDays = 0): string {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function readableError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) {
    return "서버에 연결할 수 없어요. 네트워크 상태를 확인해 주세요.";
  }
  return "예상하지 못한 문제가 생겼어요. 잠시 후 다시 시도해 주세요.";
}

function MealCard({ meal, index }: { meal: Meal; index: number }) {
  const nutritionEntries = Object.entries(meal.nutrition ?? {});

  return (
    <article className="meal-card glass" style={{ "--delay": `${index * 70}ms` } as React.CSSProperties}>
      <div className="meal-date">
        <span>{dateFormatter.format(new Date(`${meal.date}T00:00:00`))}</span>
        <span className="lunch-badge">중식</span>
      </div>
      <ul className="menu-list" aria-label={`${meal.date} 메뉴`}>
        {meal.menu.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      {(meal.calories || nutritionEntries.length > 0 || meal.origin) && (
        <details className="meal-details">
          <summary>영양·원산지 정보</summary>
          <div className="detail-grid">
            {meal.calories && <p><strong>열량</strong>{meal.calories}</p>}
            {nutritionEntries.map(([name, value]) => (
              <p key={name}><strong>{name}</strong>{value}</p>
            ))}
            {meal.origin && <p className="origin"><strong>원산지</strong>{meal.origin}</p>}
          </div>
        </details>
      )}
    </article>
  );
}

function App() {
  const [query, setQuery] = useState("");
  const [schools, setSchools] = useState<School[]>([]);
  const [selectedSchool, setSelectedSchool] = useState<School | null>(null);
  const [searchState, setSearchState] = useState<RequestState>("idle");
  const [searchError, setSearchError] = useState("");
  const [from, setFrom] = useState(localDate());
  const [to, setTo] = useState(localDate(6));
  const [meals, setMeals] = useState<Meal[]>([]);
  const [mealState, setMealState] = useState<RequestState>("idle");
  const [mealError, setMealError] = useState("");
  const searchController = useRef<AbortController | null>(null);
  const mealController = useRef<AbortController | null>(null);
  const searchId = useId();
  const fromId = useId();
  const toId = useId();

  const dateError = from && to && from > to
    ? "시작일은 종료일보다 늦을 수 없어요."
    : "";
  const canSearch = query.trim().length > 0 && searchState !== "loading";
  const canGetMeals = Boolean(selectedSchool && from && to && !dateError && mealState !== "loading");

  useEffect(() => () => {
    searchController.current?.abort();
    mealController.current?.abort();
  }, []);

  async function handleSearch(event: FormEvent) {
    event.preventDefault();
    const normalizedQuery = query.trim();
    if (!normalizedQuery || searchState === "loading") return;

    searchController.current?.abort();
    const controller = new AbortController();
    searchController.current = controller;
    setSearchState("loading");
    setSearchError("");

    try {
      const result = await searchSchools(normalizedQuery, controller.signal);
      setSchools(result);
      setSearchState(result.length ? "success" : "empty");
    } catch (error) {
      if (controller.signal.aborted) return;
      setSchools([]);
      setSearchError(readableError(error));
      setSearchState("error");
    }
  }

  function chooseSchool(school: School) {
    setSelectedSchool(school);
    setQuery(school.name);
    setSchools([]);
    setSearchState("idle");
    setMeals([]);
    setMealState("idle");
    setMealError("");
  }

  function clearSchool() {
    mealController.current?.abort();
    setSelectedSchool(null);
    setQuery("");
    setSchools([]);
    setSearchState("idle");
    setMeals([]);
    setMealState("idle");
    setMealError("");
  }

  async function handleMeals(event: FormEvent) {
    event.preventDefault();
    if (!selectedSchool || !canGetMeals) return;

    mealController.current?.abort();
    const controller = new AbortController();
    mealController.current = controller;
    setMealState("loading");
    setMealError("");

    try {
      const result = await getMeals(selectedSchool, from, to, controller.signal);
      const orderedMeals = [...result.meals].sort((a, b) => a.date.localeCompare(b.date));
      setMeals(orderedMeals);
      setMealState(orderedMeals.length ? "success" : "empty");
    } catch (error) {
      if (controller.signal.aborted) return;
      setMealError(readableError(error));
      setMealState("error");
    }
  }

  return (
    <div className="app-shell">
      <div className="orb orb-one" />
      <div className="orb orb-two" />
      <div className="orb orb-three" />

      <header className="topbar">
        <a className="brand" href="#" aria-label="급식한눈 홈">
          <span className="brand-mark"><UtensilsCrossed size={20} /></span>
          <span>급식한눈</span>
        </a>
        <span className="service-pill"><span /> NEIS 실시간 연동</span>
      </header>

      <main>
        <section className="hero">
          <div className="eyebrow"><Sparkles size={15} /> 오늘의 맛있는 한 끼</div>
          <h1>우리 학교 급식,<br /><em>한눈에 만나보세요.</em></h1>
          <p>학교를 찾고 날짜를 선택하면 매일의 중식 메뉴와<br className="desktop-only" /> 영양 정보를 간편하게 확인할 수 있어요.</p>
        </section>

        <section className="finder glass" aria-label="급식 조회">
          <div className="steps" aria-label="조회 단계">
            <div className={`step active ${selectedSchool ? "complete" : ""}`}>
              <span>{selectedSchool ? <Check size={16} /> : "1"}</span>
              <div><strong>학교 찾기</strong><small>학교를 검색해 주세요</small></div>
            </div>
            <ChevronRight className="step-arrow" />
            <div className={`step ${selectedSchool ? "active" : ""} ${mealState === "success" ? "complete" : ""}`}>
              <span>{mealState === "success" ? <Check size={16} /> : "2"}</span>
              <div><strong>날짜 선택</strong><small>조회 기간을 정해 주세요</small></div>
            </div>
            <ChevronRight className="step-arrow" />
            <div className={`step ${mealState === "success" ? "active complete" : ""}`}>
              <span>{mealState === "success" ? <Check size={16} /> : "3"}</span>
              <div><strong>급식 확인</strong><small>맛있는 메뉴를 확인해요</small></div>
            </div>
          </div>

          <div className="finder-content">
            <form className="search-form" onSubmit={handleSearch}>
              <label htmlFor={searchId}>학교 이름</label>
              <div className="search-row">
                <div className="input-wrap">
                  <Search size={19} aria-hidden="true" />
                  <input
                    id={searchId}
                    value={query}
                    onChange={(event) => {
                      if (selectedSchool) {
                        mealController.current?.abort();
                        setSelectedSchool(null);
                        setMeals([]);
                        setMealState("idle");
                        setMealError("");
                      }
                      setQuery(event.target.value);
                    }}
                    placeholder="예: 서울고등학교"
                    autoComplete="off"
                    disabled={searchState === "loading"}
                  />
                  {query && !selectedSchool && (
                    <button className="clear-input" type="button" onClick={() => setQuery("")} aria-label="검색어 지우기">
                      <X size={16} />
                    </button>
                  )}
                </div>
                <button className="primary-button search-button" disabled={!canSearch}>
                  {searchState === "loading" ? <><span className="spinner" /> 찾는 중</> : <>학교 찾기 <ArrowRight size={18} /></>}
                </button>
              </div>
            </form>

            <div className="search-feedback" role="status" aria-live="polite">
              {searchState === "success" && (
                <ul className="school-list glass">
                  {schools.map((school) => (
                    <li key={`${school.educationOfficeCode}-${school.schoolCode}`}>
                      <button type="button" onClick={() => chooseSchool(school)}>
                        <span className="school-icon"><UtensilsCrossed size={18} /></span>
                        <span className="school-copy">
                          <strong>{school.name}</strong>
                          <small><MapPin size={13} /> {school.address || school.region}</small>
                        </span>
                        <ChevronRight size={19} />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              {searchState === "empty" && (
                <div className="notice empty"><Search size={20} /><span><strong>일치하는 학교가 없어요.</strong>학교 이름을 줄여 다시 검색해 보세요.</span></div>
              )}
              {searchState === "error" && (
                <div className="notice error"><CircleAlert size={20} /><span><strong>학교를 찾지 못했어요.</strong>{searchError}</span><button type="button" onClick={() => void handleSearch(new Event("submit") as unknown as FormEvent)}><RotateCcw size={15} /> 재시도</button></div>
              )}
            </div>

            {selectedSchool && (
              <div className="selected-school">
                <span className="school-icon"><Check size={18} /></span>
                <span><small>선택한 학교</small><strong>{selectedSchool.name}</strong><em>{selectedSchool.region}</em></span>
                <button type="button" onClick={clearSchool}>변경</button>
              </div>
            )}

            <div className={`date-section ${selectedSchool ? "" : "disabled-section"}`} aria-disabled={!selectedSchool}>
              <div className="section-heading">
                <div><CalendarDays size={19} /><span><strong>조회할 기간</strong><small>원하는 기간의 급식을 한 번에 확인해 보세요.</small></span></div>
                {!selectedSchool && <span className="hint">학교를 먼저 선택해 주세요</span>}
              </div>
              <form className="date-form" onSubmit={handleMeals}>
                <div className="date-field">
                  <label htmlFor={fromId}>시작일</label>
                  <input id={fromId} type="date" value={from} onChange={(event) => setFrom(event.target.value)} disabled={!selectedSchool} />
                </div>
                <span className="date-dash">—</span>
                <div className="date-field">
                  <label htmlFor={toId}>종료일</label>
                  <input id={toId} type="date" value={to} min={from} onChange={(event) => setTo(event.target.value)} disabled={!selectedSchool} />
                </div>
                <button className="primary-button meal-button" disabled={!canGetMeals}>
                  {mealState === "loading" ? <><span className="spinner" /> 불러오는 중</> : <><UtensilsCrossed size={18} /> 급식 조회</>}
                </button>
              </form>
              {dateError && <p className="field-error" role="alert"><CircleAlert size={15} /> {dateError}</p>}
            </div>
          </div>
        </section>

        <section className="results" aria-live="polite" aria-busy={mealState === "loading"}>
          {mealState === "loading" && (
            <div className="loading-panel glass"><span className="large-spinner" /><strong>맛있는 급식을 불러오고 있어요</strong><p>잠시만 기다려 주세요.</p></div>
          )}
          {mealState === "error" && (
            <div className="result-notice glass"><CircleAlert size={32} /><h2>급식을 불러오지 못했어요</h2><p>{mealError}</p><button className="secondary-button" type="button" onClick={() => document.querySelector<HTMLButtonElement>(".meal-button")?.click()}><RotateCcw size={16} /> 다시 시도</button></div>
          )}
          {mealState === "empty" && (
            <div className="result-notice glass"><CalendarDays size={32} /><h2>이 기간에는 등록된 중식이 없어요</h2><p>주말이나 방학 기간인지 확인하고 다른 날짜를 선택해 보세요.</p></div>
          )}
          {mealState === "success" && (
            <>
              <div className="results-heading">
                <div><span className="result-icon"><UtensilsCrossed size={21} /></span><div><p>{selectedSchool?.name}</p><h2>맛있는 급식이 준비됐어요</h2></div></div>
                <span>{meals.length}일의 메뉴</span>
              </div>
              <div className="meal-grid">
                {meals.map((meal, index) => <MealCard key={meal.date} meal={meal} index={index} />)}
              </div>
              <p className="allergy-note"><CircleAlert size={14} /> 메뉴 뒤 숫자는 알레르기 유발 식품 번호예요. 자세한 내용은 학교 안내를 확인해 주세요.</p>
            </>
          )}
        </section>
      </main>

      <footer><span>NEIS 나이스 교육정보 개방 포털의 공공데이터를 활용합니다.</span><span>© 2026 급식한눈</span></footer>
    </div>
  );
}

export default App;
