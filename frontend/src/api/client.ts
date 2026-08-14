import { HttpAgent } from '@ag-ui/client';
import type {
  AnalysisRequest,
  AnalysisResult,
  Meal,
  MealSearchParams,
  MealSearchResponse,
  RandomSchoolResponse,
  School,
  SchoolSearchResponse,
} from './types';

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? '';

export class ApiClientError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;

  constructor(status: number, code: string, message: string, requestId: string | null) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

export async function searchSchools(query: string, signal?: AbortSignal): Promise<SchoolSearchResponse> {
  const url = createUrl('/api/schools', { query });
  return requestJson(url, isSchoolSearchResponse, signal);
}

export async function getMeals(params: MealSearchParams, signal?: AbortSignal): Promise<MealSearchResponse> {
  const url = createUrl(
    `/api/schools/${encodeURIComponent(params.educationOfficeCode)}/${encodeURIComponent(params.schoolCode)}/meals`,
    {
      from: params.from,
      to: params.to,
      mealType: params.mealType,
    },
  );

  return requestJson(url, isMealSearchResponse, signal);
}

export async function getRandomSchools(signal?: AbortSignal): Promise<RandomSchoolResponse> {
  const url = createUrl('/api/schools/random', {});
  const response = await requestJson(url, isSchoolSearchResponse, signal);
  if (response.schools.length !== 10) {
    throw new ApiClientError(502, 'INVALID_API_RESPONSE', '학교 후보는 정확히 10개여야 합니다.', null);
  }
  return response;
}

export async function analyzeMeals(
  request: AnalysisRequest,
  onProgress?: (message: string) => void,
): Promise<AnalysisResult> {
  const agent = new HttpAgent({
    url: createUrl('/api/analysis', {}),
    agentId: 'school-lunch-evaluation',
    threadId: crypto.randomUUID(),
    initialMessages: [
      {
        id: crypto.randomUUID(),
        role: 'user',
        content: JSON.stringify(request),
      },
    ],
  });

  const result = await agent.runAgent(
    {},
    {
      onRunStartedEvent: () => {
        onProgress?.('분석 워크플로를 시작했습니다.');
      },
      onStepStartedEvent: ({ event }) => {
        onProgress?.(`${event.stepName} 단계를 실행하고 있습니다.`);
      },
    },
  );
  const assistantMessage = [...result.newMessages].reverse().find((message) => message.role === 'assistant');
  if (!assistantMessage || typeof assistantMessage.content !== 'string') {
    throw new ApiClientError(502, 'INVALID_AGENT_RESPONSE', '분석 결과가 비어 있습니다.', null);
  }

  try {
    const payload: unknown = JSON.parse(assistantMessage.content);
    if (!isAnalysisResult(payload)) {
      throw new Error('invalid shape');
    }
    return payload;
  } catch {
    throw new ApiClientError(502, 'INVALID_AGENT_RESPONSE', '분석 결과 형식이 올바르지 않습니다.', null);
  }
}

function createUrl(pathname: string, queryParams: Record<string, string>): string {
  const url = new URL(configuredBaseUrl ? `${configuredBaseUrl}${pathname}` : pathname, window.location.origin);
  Object.entries(queryParams).forEach(([key, value]) => {
    url.searchParams.set(key, value);
  });
  return url.toString();
}

async function requestJson<T>(
  url: string,
  validate: (value: unknown) => value is T,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    signal,
  });

  if (!response.ok) {
    throw await toApiError(response);
  }

  const payload: unknown = await response.json();
  if (!validate(payload)) {
    throw new ApiClientError(
      502,
      'INVALID_API_RESPONSE',
      '서버 응답 형식이 올바르지 않습니다. 잠시 후 다시 시도해 주세요.',
      response.headers.get('X-Request-ID'),
    );
  }
  return payload;
}

async function toApiError(response: Response): Promise<ApiClientError> {
  const fallbackMessage = response.status >= 500
    ? '서버 또는 외부 급식 서비스에 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.'
    : '요청을 처리할 수 없습니다. 입력값을 확인해 주세요.';

  try {
    const payload: unknown = await response.json();
    if (!isApiErrorPayload(payload)) {
      return new ApiClientError(response.status, 'UNKNOWN_ERROR', fallbackMessage, null);
    }
    return new ApiClientError(
      response.status,
      payload.error.code,
      payload.error.message || fallbackMessage,
      payload.error.requestId ?? null,
    );
  } catch {
    return new ApiClientError(response.status, 'UNKNOWN_ERROR', fallbackMessage, null);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isStringRecord(value: unknown): value is Record<string, string> {
  return isRecord(value) && Object.values(value).every((item) => typeof item === 'string');
}

function isSchool(value: unknown): value is School {
  return (
    isRecord(value) &&
    typeof value.educationOfficeCode === 'string' &&
    typeof value.schoolCode === 'string' &&
    typeof value.name === 'string' &&
    typeof value.region === 'string' &&
    typeof value.address === 'string'
  );
}

function isSchoolSearchResponse(value: unknown): value is SchoolSearchResponse {
  return isRecord(value) && Array.isArray(value.schools) && value.schools.every(isSchool);
}

function isMeal(value: unknown): value is Meal {
  return (
    isRecord(value) &&
    typeof value.date === 'string' &&
    value.mealType === 'lunch' &&
    Array.isArray(value.menu) &&
    value.menu.every((item) => typeof item === 'string') &&
    (value.calories === undefined || typeof value.calories === 'string') &&
    (value.nutrition === undefined || isStringRecord(value.nutrition)) &&
    (value.origin === undefined || typeof value.origin === 'string') &&
    (value.mealCount === undefined || typeof value.mealCount === 'string')
  );
}

function isMealSearchResponse(value: unknown): value is MealSearchResponse {
  if (!isRecord(value) || !isRecord(value.school)) {
    return false;
  }
  return (
    typeof value.school.educationOfficeCode === 'string' &&
    typeof value.school.schoolCode === 'string' &&
    typeof value.school.name === 'string' &&
    typeof value.from === 'string' &&
    typeof value.to === 'string' &&
    Array.isArray(value.meals) &&
    value.meals.every(isMeal)
  );
}

function isAnalysisResult(value: unknown): value is AnalysisResult {
  const validAreas = new Set(['nutrition_balance', 'healthiness', 'ingredient_menu_quality']);
  return (
    isRecord(value) &&
    Array.isArray(value.scores) &&
    value.scores.length === 2 &&
    value.scores.every(
      (score) =>
        isRecord(score) &&
        isRecord(score.school) &&
        typeof score.school.schoolCode === 'string' &&
        typeof score.school.name === 'string' &&
        typeof score.totalScore === 'number' &&
        Array.isArray(score.areas) &&
        score.areas.length === 3 &&
        score.areas.every(
          (area) =>
            isRecord(area) &&
            typeof area.area === 'string' &&
            validAreas.has(area.area) &&
            typeof area.rating === 'number' &&
            typeof area.weight === 'number' &&
            typeof area.weightedScore === 'number' &&
            typeof area.rationale === 'string' &&
            Array.isArray(area.evidence) &&
            area.evidence.every((evidence) => typeof evidence === 'string') &&
            Array.isArray(area.estimatedFlags) &&
            area.estimatedFlags.every((flag) => typeof flag === 'string'),
        ),
    ) &&
    (value.outcome === 'first' || value.outcome === 'second' || value.outcome === 'tie') &&
    (
      value.winnerSchool === null ||
      (
        isRecord(value.winnerSchool) &&
        typeof value.winnerSchool.educationOfficeCode === 'string' &&
        typeof value.winnerSchool.schoolCode === 'string' &&
        typeof value.winnerSchool.name === 'string'
      )
    ) &&
    isRecord(value.review) &&
    typeof value.review.summary === 'string' &&
    typeof value.review.keyReason === 'string' &&
    typeof value.review.firstSchoolImprovement === 'string' &&
    typeof value.review.secondSchoolImprovement === 'string' &&
    Array.isArray(value.review.qualityWarnings) &&
    value.review.qualityWarnings.every((warning) => typeof warning === 'string') &&
    typeof value.disclaimer === 'string'
  );
}

function isApiErrorPayload(value: unknown): value is {
  error: { code: string; message: string; requestId?: string };
} {
  return (
    isRecord(value) &&
    isRecord(value.error) &&
    typeof value.error.code === 'string' &&
    typeof value.error.message === 'string' &&
    (value.error.requestId === undefined || typeof value.error.requestId === 'string')
  );
}
