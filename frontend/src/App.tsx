import { type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import './App.css';
import { ApiClientError, getMeals, searchSchools } from './api/client';
import type { MealSearchResponse, School } from './api/types';

type SearchState =
  | { status: 'idle' }
  | { status: 'loading'; query: string }
  | { status: 'success'; query: string; schools: School[] }
  | { status: 'empty'; query: string }
  | { status: 'validation'; message: string }
  | { status: 'error'; query: string; message: string };

type MealState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; response: MealSearchResponse }
  | { status: 'empty'; response: MealSearchResponse }
  | { status: 'error'; message: string };

const SEARCH_DEBOUNCE_MS = 350;

function App() {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchState, setSearchState] = useState<SearchState>({ status: 'idle' });
  const [selectedSchool, setSelectedSchool] = useState<School | null>(null);
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [mealState, setMealState] = useState<MealState>({ status: 'idle' });

  const searchAbortControllerRef = useRef<AbortController | null>(null);
  const mealAbortControllerRef = useRef<AbortController | null>(null);
  const searchRequestIdRef = useRef(0);
  const mealRequestIdRef = useRef(0);
  const activeSearchQueryRef = useRef<string | null>(null);
  const lastCompletedSearchQueryRef = useRef<string | null>(null);

  const dateValidationMessage = useMemo(() => {
    if (!selectedSchool) {
      return '학교를 먼저 선택해 주세요.';
    }

    if (!fromDate || !toDate) {
      return '시작일과 종료일을 모두 선택해 주세요.';
    }

    if (fromDate > toDate) {
      return '시작일은 종료일보다 늦을 수 없습니다.';
    }

    return null;
  }, [fromDate, selectedSchool, toDate]);

  const visibleDateValidationMessage = selectedSchool ? dateValidationMessage : null;

  const runSchoolSearch = useCallback(
    async (rawQuery: string, options?: { force?: boolean }) => {
      const normalizedQuery = rawQuery.trim();
      if (!normalizedQuery) {
        setSearchState({ status: 'validation', message: '학교 이름을 입력한 후 검색해 주세요.' });
        return;
      }

      const force = options?.force ?? false;
      const alreadyCompleted = lastCompletedSearchQueryRef.current === normalizedQuery;
      const alreadyLoading = activeSearchQueryRef.current === normalizedQuery;

      if (!force && (alreadyCompleted || alreadyLoading)) {
        return;
      }

      searchAbortControllerRef.current?.abort();
      const abortController = new AbortController();
      searchAbortControllerRef.current = abortController;

      const requestId = searchRequestIdRef.current + 1;
      searchRequestIdRef.current = requestId;
      activeSearchQueryRef.current = normalizedQuery;
      setSearchState({ status: 'loading', query: normalizedQuery });

      try {
        const response = await searchSchools(normalizedQuery, abortController.signal);
        if (requestId !== searchRequestIdRef.current) {
          return;
        }

        activeSearchQueryRef.current = null;
        lastCompletedSearchQueryRef.current = normalizedQuery;

        if (response.schools.length === 0) {
          setSearchState({ status: 'empty', query: normalizedQuery });
          return;
        }

        setSearchState({
          status: 'success',
          query: normalizedQuery,
          schools: response.schools,
        });
      } catch (error) {
        if (abortController.signal.aborted || requestId !== searchRequestIdRef.current) {
          return;
        }

        activeSearchQueryRef.current = null;
        setSearchState({
          status: 'error',
          query: normalizedQuery,
          message: toUserMessage(error, '학교 검색 중 오류가 발생했습니다.'),
        });
      }
    },
    [],
  );

  const runMealSearch = useCallback(
    async (school: School) => {
      if (dateValidationMessage) {
        return;
      }

      mealAbortControllerRef.current?.abort();
      const abortController = new AbortController();
      mealAbortControllerRef.current = abortController;

      const requestId = mealRequestIdRef.current + 1;
      mealRequestIdRef.current = requestId;
      setMealState({ status: 'loading' });

      try {
        const response = await getMeals(
          {
            educationOfficeCode: school.educationOfficeCode,
            schoolCode: school.schoolCode,
            from: fromDate,
            to: toDate,
            mealType: 'lunch',
          },
          abortController.signal,
        );
        if (requestId !== mealRequestIdRef.current) {
          return;
        }

        const sortedMeals = [...response.meals].sort((left, right) => left.date.localeCompare(right.date));
        const normalizedResponse: MealSearchResponse = {
          ...response,
          meals: sortedMeals,
        };

        if (normalizedResponse.meals.length === 0) {
          setMealState({ status: 'empty', response: normalizedResponse });
          return;
        }

        setMealState({ status: 'success', response: normalizedResponse });
      } catch (error) {
        if (abortController.signal.aborted || requestId !== mealRequestIdRef.current) {
          return;
        }

        setMealState({
          status: 'error',
          message: toUserMessage(error, '급식 정보를 불러오지 못했습니다.'),
        });
      }
    },
    [dateValidationMessage, fromDate, toDate],
  );

  useEffect(() => {
    const normalizedQuery = searchTerm.trim();
    if (!normalizedQuery) {
      searchAbortControllerRef.current?.abort();
      activeSearchQueryRef.current = null;
      lastCompletedSearchQueryRef.current = null;
      setSearchState({ status: 'idle' });
      return undefined;
    }

    const handle = window.setTimeout(() => {
      void runSchoolSearch(normalizedQuery);
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      window.clearTimeout(handle);
    };
  }, [runSchoolSearch, searchTerm]);

  useEffect(() => {
    return () => {
      searchAbortControllerRef.current?.abort();
      mealAbortControllerRef.current?.abort();
    };
  }, []);

  const liveRegionMessage = useMemo(() => {
    if (mealState.status === 'loading') {
      return '중식 정보를 불러오는 중입니다.';
    }

    if (mealState.status === 'error') {
      return mealState.message;
    }

    if (mealState.status === 'empty') {
      return `${mealState.response.from}부터 ${mealState.response.to}까지 표시할 중식 정보가 없습니다.`;
    }

    if (mealState.status === 'success') {
      return `${mealState.response.meals.length}건의 중식 정보를 표시했습니다.`;
    }

    if (searchState.status === 'loading') {
      return `"${searchState.query}" 검색 중입니다.`;
    }

    if (searchState.status === 'error') {
      return searchState.message;
    }

    if (searchState.status === 'empty') {
      return `"${searchState.query}"에 해당하는 학교가 없습니다.`;
    }

    if (searchState.status === 'success') {
      return `${searchState.schools.length}개의 학교 검색 결과가 있습니다.`;
    }

    if (searchState.status === 'validation') {
      return searchState.message;
    }

    return '학교 검색과 중식 조회를 시작할 수 있습니다.';
  }, [mealState, searchState]);

  const handleSearchSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await runSchoolSearch(searchTerm, { force: true });
  };

  const handleSchoolSelect = (school: School) => {
    setSelectedSchool(school);
    mealAbortControllerRef.current?.abort();
    setMealState({ status: 'idle' });
  };

  const handleMealSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedSchool || dateValidationMessage) {
      return;
    }
    await runMealSearch(selectedSchool);
  };

  return (
    <main className="page-shell">
      <div className="page-header">
        <p className="eyebrow">Battle School Lunch</p>
        <h1>학교 급식 조회 앱</h1>
        <p className="lead">
          학교를 검색하고 날짜 범위를 선택하면 백엔드를 통해 중식 정보를 안전하게 조회합니다.
        </p>
      </div>

      <p aria-live="polite" className="sr-only">
        {liveRegionMessage}
      </p>

      <div className="page-grid">
        <section className="panel" aria-labelledby="search-heading">
          <h2 id="search-heading">1. 학교 검색 및 선택</h2>
          <form className="search-form" onSubmit={(event) => void handleSearchSubmit(event)}>
            <label className="field-label" htmlFor="school-query">
              학교 이름
            </label>
            <div className="search-controls">
              <input
                id="school-query"
                name="schoolQuery"
                type="search"
                autoComplete="off"
                value={searchTerm}
                onChange={(event) => {
                  searchAbortControllerRef.current?.abort();
                  activeSearchQueryRef.current = null;
                  lastCompletedSearchQueryRef.current = null;
                  searchRequestIdRef.current += 1;
                  setSearchState({ status: 'idle' });
                  setSearchTerm(event.target.value);
                }}
                placeholder="예: 한국중"
              />
              <button type="submit">검색</button>
            </div>
            <p className="field-hint">학교 이름 일부만 입력해도 검색할 수 있습니다.</p>
          </form>

          {searchState.status === 'validation' ? (
            <p className="message message-warning" role="alert">
              {searchState.message}
            </p>
          ) : null}

          {searchState.status === 'loading' ? (
            <p className="message message-status" role="status">
              “{searchState.query}” 검색 중입니다...
            </p>
          ) : null}

          {searchState.status === 'error' ? (
            <div className="message message-error" role="alert">
              <p>{searchState.message}</p>
              <button
                type="button"
                className="secondary-button"
                onClick={() => {
                  void runSchoolSearch(searchState.query, { force: true });
                }}
              >
                다시 시도
              </button>
            </div>
          ) : null}

          {searchState.status === 'empty' ? (
            <p className="message message-empty" role="status">
              “{searchState.query}”에 해당하는 학교가 없습니다. 다른 검색어를 시도해 보세요.
            </p>
          ) : null}

          {searchState.status === 'success' ? (
            <ul className="school-list" aria-label="학교 검색 결과">
              {searchState.schools.map((school) => {
                const isSelected =
                  selectedSchool?.educationOfficeCode === school.educationOfficeCode &&
                  selectedSchool.schoolCode === school.schoolCode;

                return (
                  <li key={`${school.educationOfficeCode}-${school.schoolCode}`}>
                    <button
                      type="button"
                      className={isSelected ? 'school-button selected' : 'school-button'}
                      aria-pressed={isSelected}
                      onClick={() => {
                        handleSchoolSelect(school);
                      }}
                    >
                      <span className="school-name">{school.name}</span>
                      <span className="school-meta">{school.region}</span>
                      <span className="school-meta">{school.address}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : null}

          <div className="selection-summary" aria-live="polite">
            <h3>선택한 학교</h3>
            {selectedSchool ? (
              <p>
                <strong>{selectedSchool.name}</strong>
                <span>{selectedSchool.region}</span>
                <span>{selectedSchool.address}</span>
              </p>
            ) : (
              <p>아직 선택한 학교가 없습니다.</p>
            )}
          </div>
        </section>

        <section className="panel" aria-labelledby="meal-heading">
          <h2 id="meal-heading">2. 날짜 범위 선택 및 중식 조회</h2>
          <form className="date-form" onSubmit={(event) => void handleMealSubmit(event)}>
            <fieldset disabled={!selectedSchool}>
              <legend>조회 기간</legend>
              <div className="date-grid">
                <label className="field-label" htmlFor="from-date">
                  시작일
                  <input
                    id="from-date"
                    type="date"
                    value={fromDate}
                    onChange={(event) => {
                      setFromDate(event.target.value);
                    }}
                  />
                </label>
                <label className="field-label" htmlFor="to-date">
                  종료일
                  <input
                    id="to-date"
                    type="date"
                    value={toDate}
                    onChange={(event) => {
                      setToDate(event.target.value);
                    }}
                  />
                </label>
              </div>
            </fieldset>

            <div className="submit-row">
              <button type="submit" disabled={!selectedSchool || Boolean(dateValidationMessage) || mealState.status === 'loading'}>
                중식 조회
              </button>
              <p className="field-hint">
                브라우저는 NEIS에 직접 연결하지 않고 애플리케이션 백엔드를 통해서만 데이터를 가져옵니다.
              </p>
            </div>
          </form>

          {visibleDateValidationMessage ? (
            <p className="message message-warning" role="alert">
              {visibleDateValidationMessage}
            </p>
          ) : null}

          {mealState.status === 'loading' ? (
            <p className="message message-status" role="status">
              중식 정보를 불러오는 중입니다...
            </p>
          ) : null}

          {mealState.status === 'error' ? (
            <div className="message message-error" role="alert">
              <p>{mealState.message}</p>
              {selectedSchool ? (
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => {
                    void runMealSearch(selectedSchool);
                  }}
                >
                  다시 시도
                </button>
              ) : null}
            </div>
          ) : null}

          {mealState.status === 'empty' ? (
            <div className="message message-empty" role="status">
              <p>
                {mealState.response.school.name}의 {mealState.response.from}부터 {mealState.response.to}
                까지 표시할 중식 정보가 없습니다.
              </p>
            </div>
          ) : null}

          {mealState.status === 'success' ? (
            <div className="meal-results" aria-live="polite">
              <h3>
                {mealState.response.school.name} · {mealState.response.from} ~ {mealState.response.to}
              </h3>
              <ol className="meal-list">
                {mealState.response.meals.map((meal) => (
                  <li className="meal-card" key={`${meal.date}-${meal.menu.join('|')}`}>
                    <div className="meal-card-header">
                      <h4>{meal.date}</h4>
                      <span className="pill">중식</span>
                    </div>
                    <ul className="menu-list">
                      {meal.menu.map((item) => (
                        <li key={`${meal.date}-${item}`}>{item}</li>
                      ))}
                    </ul>
                    {meal.calories ? (
                      <p className="meal-extra">
                        <strong>열량</strong> {meal.calories}
                      </p>
                    ) : null}
                    {meal.origin ? (
                      <div className="meal-extra">
                        <strong>원산지</strong>
                        <pre>{meal.origin}</pre>
                      </div>
                    ) : null}
                    {meal.nutrition ? (
                      <dl className="nutrition-list">
                        {Object.entries(meal.nutrition).map(([label, value]) => (
                          <div key={`${meal.date}-${label}`}>
                            <dt>{label}</dt>
                            <dd>{value}</dd>
                          </div>
                        ))}
                      </dl>
                    ) : null}
                  </li>
                ))}
              </ol>
            </div>
          ) : (
            <div className="placeholder">
              <h3>3. 결과 확인</h3>
              <p>학교와 날짜를 선택하면 이 영역에 날짜순 중식 결과가 표시됩니다.</p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function toUserMessage(error: unknown, fallbackMessage: string) {
  if (error instanceof ApiClientError) {
    return error.message;
  }

  if (error instanceof Error && error.name === 'AbortError') {
    return fallbackMessage;
  }

  return fallbackMessage;
}

export default App;
