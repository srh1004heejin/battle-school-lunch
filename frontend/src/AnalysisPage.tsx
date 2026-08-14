import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { analyzeMeals, getRandomSchools } from './api/client';
import type { AnalysisResult, EvaluationAreaId, School } from './api/types';

type AnalysisState =
  | { status: 'idle' }
  | { status: 'loading'; progress: string }
  | { status: 'success'; result: AnalysisResult }
  | { status: 'error'; message: string };

const AREA_LABELS: Record<EvaluationAreaId, string> = {
  nutrition_balance: '영양 균형',
  healthiness: '건강성',
  ingredient_menu_quality: '식재료 및 메뉴 품질',
};

function toIsoDate(value: Date) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function AnalysisPage() {
  const today = useMemo(() => new Date(), []);
  const minDate = useMemo(
    () => toIsoDate(new Date(today.getFullYear(), today.getMonth() - 1, 1)),
    [today],
  );
  const maxDate = useMemo(() => toIsoDate(today), [today]);
  const [schools, setSchools] = useState<School[]>([]);
  const [selectedSchools, setSelectedSchools] = useState<School[]>([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [prompt, setPrompt] = useState('');
  const [schoolError, setSchoolError] = useState<string | null>(null);
  const [analysisState, setAnalysisState] = useState<AnalysisState>({ status: 'idle' });

  const loadSchools = async () => {
    setSchoolError(null);
    setSelectedSchools([]);
    try {
      const response = await getRandomSchools();
      setSchools(response.schools);
    } catch {
      setSchoolError('학교 후보를 불러오지 못했습니다. 다시 시도해 주세요.');
    }
  };

  useEffect(() => {
    void loadSchools();
  }, []);

  useEffect(() => {
    if (selectedSchools.length !== 2 || !selectedDate) {
      return;
    }
    setPrompt(
      `${selectedSchools[0].name}와 ${selectedSchools[1].name}의 ${selectedDate} 중식을 ` +
        'EVALUATION_RUBRIC.md의 세 평가영역에 따라 비교하고, 근거와 개선안을 한국어로 설명해 주세요.',
    );
  }, [selectedDate, selectedSchools]);

  const toggleSchool = (school: School) => {
    setAnalysisState({ status: 'idle' });
    setSelectedSchools((current) => {
      const selected = current.some(
        (candidate) =>
          candidate.educationOfficeCode === school.educationOfficeCode &&
          candidate.schoolCode === school.schoolCode,
      );
      if (selected) {
        return current.filter(
          (candidate) =>
            candidate.educationOfficeCode !== school.educationOfficeCode ||
            candidate.schoolCode !== school.schoolCode,
        );
      }
      return current.length < 2 ? [...current, school] : current;
    });
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (selectedSchools.length !== 2 || !selectedDate || !prompt.trim()) {
      return;
    }
    setAnalysisState({ status: 'loading', progress: '분석 요청을 전송하고 있습니다.' });
    try {
      const result = await analyzeMeals(
        {
          schools: selectedSchools.map(({ educationOfficeCode, schoolCode, name }) => ({
            educationOfficeCode,
            schoolCode,
            name,
          })),
          date: selectedDate,
          prompt: prompt.trim(),
        },
        (progress) => {
          setAnalysisState({ status: 'loading', progress });
        },
      );
      setAnalysisState({ status: 'success', result });
    } catch {
      setAnalysisState({ status: 'error', message: '급식 분석을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.' });
    }
  };

  return (
    <main className="page-shell">
      <header className="page-header">
        <p className="eyebrow">Multi-agent evaluation</p>
        <h1>학교 급식 분석</h1>
        <p className="lead">
          두 학교의 같은 날짜 중식을 세 전문 에이전트가 독립적으로 평가하고 최종 평가자가 검토합니다.
        </p>
      </header>

      <form className="analysis-flow" onSubmit={(event) => void handleSubmit(event)}>
        <section className="panel" aria-labelledby="candidate-heading">
          <div className="section-title-row">
            <h2 id="candidate-heading">1. 학교 두 곳 선택</h2>
            <button type="button" className="secondary-button" onClick={() => void loadSchools()}>
              후보 새로고침
            </button>
          </div>
          <p className="field-hint">무작위 후보 10개 중 정확히 두 곳을 선택하세요. ({selectedSchools.length}/2)</p>
          {schoolError ? <p className="message message-error" role="alert">{schoolError}</p> : null}
          <ul className="candidate-grid" aria-label="무작위 학교 후보">
            {schools.map((school) => {
              const selected = selectedSchools.some(
                (candidate) =>
                  candidate.educationOfficeCode === school.educationOfficeCode &&
                  candidate.schoolCode === school.schoolCode,
              );
              return (
                <li key={`${school.educationOfficeCode}-${school.schoolCode}`}>
                  <button
                    type="button"
                    className={selected ? 'school-button selected' : 'school-button'}
                    aria-pressed={selected}
                    disabled={!selected && selectedSchools.length === 2}
                    onClick={() => toggleSchool(school)}
                  >
                    <span className="school-name">{school.name}</span>
                    <span className="school-meta">{school.region} · {school.address}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </section>

        <section className="panel" aria-labelledby="analysis-input-heading">
          <h2 id="analysis-input-heading">2. 날짜와 분석 프롬프트</h2>
          <label className="field-label" htmlFor="analysis-date">
            분석 날짜
            <input
              id="analysis-date"
              type="date"
              min={minDate}
              max={maxDate}
              value={selectedDate}
              onChange={(event) => setSelectedDate(event.target.value)}
            />
          </label>
          <label className="field-label" htmlFor="analysis-prompt">
            분석 프롬프트
            <textarea
              id="analysis-prompt"
              rows={6}
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="학교 두 곳과 날짜를 선택하면 기본 프롬프트가 생성됩니다."
            />
          </label>
          <button
            type="submit"
            disabled={
              selectedSchools.length !== 2 ||
              !selectedDate ||
              !prompt.trim() ||
              analysisState.status === 'loading'
            }
          >
            멀티에이전트 분석 시작
          </button>
          {analysisState.status === 'loading' ? (
            <p className="message message-status" role="status">{analysisState.progress}</p>
          ) : null}
          {analysisState.status === 'error' ? (
            <p className="message message-error" role="alert">{analysisState.message}</p>
          ) : null}
        </section>
      </form>

      {analysisState.status === 'success' ? <AnalysisResults result={analysisState.result} /> : null}
    </main>
  );
}

function AnalysisResults({ result }: { result: AnalysisResult }) {
  const outcomeText =
    result.outcome === 'tie'
      ? '동점'
      : `${result.scores[result.outcome === 'first' ? 0 : 1].school.name} 승리`;

  return (
    <section className="panel analysis-results" aria-labelledby="analysis-result-heading">
      <h2 id="analysis-result-heading">3. 분석 결과 · {outcomeText}</h2>
      <p>{result.review.summary}</p>
      <p><strong>핵심 이유:</strong> {result.review.keyReason}</p>
      <div className="score-grid">
        {result.scores.map((score, schoolIndex) => (
          <article className="score-card" key={score.school.schoolCode}>
            <h3>
              {score.school.name} · {score.totalScore.toFixed(1)}점 ·{' '}
              {result.outcome === 'tie'
                ? '동점'
                : (result.outcome === 'first' ? schoolIndex === 0 : schoolIndex === 1)
                  ? '승자'
                  : '패자'}
            </h3>
            <dl>
              {score.areas.map((area) => (
                <div key={area.area} className="area-score">
                  <dt>{AREA_LABELS[area.area]} ({area.weight}%)</dt>
                  <dd>{area.rating}/5 · {area.weightedScore.toFixed(1)}점</dd>
                  <p>{area.rationale}</p>
                  <ul>{area.evidence.map((evidence) => <li key={evidence}>{evidence}</li>)}</ul>
                </div>
              ))}
            </dl>
            <p>
              <strong>개선안:</strong>{' '}
              {schoolIndex === 0 ? result.review.firstSchoolImprovement : result.review.secondSchoolImprovement}
            </p>
          </article>
        ))}
      </div>
      {result.review.qualityWarnings.length > 0 ? (
        <div className="message message-warning">
          <strong>품질 검토 경고</strong>
          <ul>{result.review.qualityWarnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
        </div>
      ) : null}
      <p className="field-hint">{result.disclaimer}</p>
    </section>
  );
}

export default AnalysisPage;
