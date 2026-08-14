import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';

vi.mock('@ag-ui/client', () => ({
  HttpAgent: class {
    async runAgent() {
      return {
        result: null,
        newMessages: [
          {
            id: 'analysis-result',
            role: 'assistant',
            content: JSON.stringify({
              analysisId: '00000000-0000-0000-0000-000000000001',
              scores: [
                {
                  school: { educationOfficeCode: 'B10', schoolCode: '7010001', name: '후보학교1' },
                  totalScore: 84,
                  areas: [
                    { area: 'nutrition_balance', rating: 5, weight: 45, weightedScore: 45, rationale: '균형 우수', evidence: ['열량 확인'], estimatedFlags: [] },
                    { area: 'healthiness', rating: 4, weight: 30, weightedScore: 24, rationale: '건강성 우수', evidence: ['영양정보 확인'], estimatedFlags: [] },
                    { area: 'ingredient_menu_quality', rating: 3, weight: 25, weightedScore: 15, rationale: '보통', evidence: ['메뉴 확인'], estimatedFlags: [] },
                  ],
                },
                {
                  school: { educationOfficeCode: 'C10', schoolCode: '7010002', name: '후보학교2' },
                  totalScore: 79,
                  areas: [
                    { area: 'nutrition_balance', rating: 4, weight: 45, weightedScore: 36, rationale: '균형 양호', evidence: ['열량 확인'], estimatedFlags: [] },
                    { area: 'healthiness', rating: 3, weight: 30, weightedScore: 18, rationale: '평균', evidence: ['영양정보 확인'], estimatedFlags: [] },
                    { area: 'ingredient_menu_quality', rating: 5, weight: 25, weightedScore: 25, rationale: '구성 우수', evidence: ['메뉴 확인'], estimatedFlags: [] },
                  ],
                },
              ],
              outcome: 'first',
              winnerSchool: { educationOfficeCode: 'B10', schoolCode: '7010001', name: '후보학교1' },
              review: {
                summary: '첫 번째 학교가 근소하게 우수합니다.',
                keyReason: '영양 균형 점수가 높습니다.',
                firstSchoolImprovement: '채소 반찬을 보강하세요.',
                secondSchoolImprovement: '나트륨을 줄이세요.',
                qualityWarnings: [],
              },
              disclaimer: '이 분석은 영양사의 전문 진단을 대체하지 않습니다.',
            }),
          },
        ],
      };
    }
  },
}));

type DeferredResponse = {
  promise: Promise<Response>;
  resolve: (response: Response) => void;
};

function toUrl(input: string | URL | Request) {
  if (typeof input === 'string') {
    return new URL(input);
  }

  if (input instanceof URL) {
    return input;
  }

  return new URL(input.url);
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json',
    },
  });
}

function errorResponse(status: number, message: string) {
  return jsonResponse(
    {
      error: {
        code: 'TEST_ERROR',
        message,
        requestId: 'test-request-id',
      },
    },
    status,
  );
}

function deferredResponse(): DeferredResponse {
  let resolveResponse: ((response: Response) => void) | undefined;
  const promise = new Promise<Response>((resolve) => {
    resolveResponse = resolve;
  });

  return {
    promise,
    resolve: (response) => {
      resolveResponse?.(response);
    },
  };
}

describe('App', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    cleanup();
  });

  it('searches schools, selects one, and renders meals in ascending date order', async () => {
    const fetchMock = vi.fn(async (input: string | URL | Request) => {
      const url = toUrl(input);

      if (url.pathname === '/api/schools') {
        return jsonResponse({
          schools: [
            {
              educationOfficeCode: 'B10',
              schoolCode: '7010569',
              name: '한국중학교',
              region: '서울',
              address: '서울특별시 중구 예시로 10',
            },
            {
              educationOfficeCode: 'B10',
              schoolCode: '7010570',
              name: '한국중학교',
              region: '부산',
              address: '부산광역시 중구 예시로 11',
            },
          ],
        });
      }

      if (url.pathname === '/api/schools/B10/7010570/meals') {
        return jsonResponse({
          school: {
            educationOfficeCode: 'B10',
            schoolCode: '7010570',
            name: '한국중학교',
          },
          from: '2026-08-01',
          to: '2026-08-02',
          meals: [
            {
              date: '2026-08-02',
              mealType: 'lunch',
              menu: ['잡곡밥 (5.6.)', '된장찌개 (5.6.)'],
              calories: '710.2 Kcal',
              nutrition: {
                탄수화물: '98.3g',
              },
              origin: '쌀: 국내산',
            },
            {
              date: '2026-08-01',
              mealType: 'lunch',
              menu: ['현미밥', '순두부찌개 (5.6.)'],
            },
          ],
        });
      }

      throw new Error(`Unhandled request: ${url.toString()}`);
    });

    vi.stubGlobal('fetch', fetchMock);

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText('학교 이름'), '한국중');
    await user.click(screen.getByRole('button', { name: '검색' }));

    const resultList = await screen.findByRole('list', { name: '학교 검색 결과' });
    const schoolButtons = within(resultList).getAllByRole('button');
    expect(schoolButtons).toHaveLength(2);

    await user.click(schoolButtons[1]);
    expect(schoolButtons[1]).toHaveTextContent('부산광역시 중구 예시로 11');

    await user.type(screen.getByLabelText('시작일', { selector: 'input' }), '2026-08-01');
    await user.type(screen.getByLabelText('종료일', { selector: 'input' }), '2026-08-02');
    await user.click(screen.getByRole('button', { name: '중식 조회' }));

    await screen.findByRole('heading', { name: '2026-08-01', level: 4 });
    const mealHeadings = screen
      .getAllByRole('heading', { level: 4 })
      .map((heading) => heading.textContent);

    expect(mealHeadings).toEqual(['2026-08-01', '2026-08-02']);
    expect(screen.getByText('잡곡밥 (5.6.)')).toBeInTheDocument();
    expect(screen.getByText('710.2 Kcal')).toBeInTheDocument();
    expect(screen.getByText('쌀: 국내산')).toBeInTheDocument();
    expect(screen.getByText('탄수화물')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/schools'), expect.any(Object));
  });

  it('supports keyboard-only school selection and keeps date controls disabled before selection', async () => {
    const fetchMock = vi.fn(async (input: string | URL | Request) => {
      const url = toUrl(input);

      if (url.pathname === '/api/schools') {
        return jsonResponse({
          schools: [
            {
              educationOfficeCode: 'B10',
              schoolCode: '7010001',
              name: '테스트고',
              region: '서울',
              address: '서울특별시 종로구 예시로 1',
            },
          ],
        });
      }

      throw new Error(`Unhandled request: ${url.toString()}`);
    });

    vi.stubGlobal('fetch', fetchMock);

    const user = userEvent.setup();
    render(<App />);

    expect(screen.getByLabelText('시작일', { selector: 'input' })).toBeDisabled();
    expect(screen.getByLabelText('종료일', { selector: 'input' })).toBeDisabled();

    await user.type(screen.getByLabelText('학교 이름'), '테스트고');
    await user.click(screen.getByRole('button', { name: '검색' }));

    const schoolButton = await screen.findByRole('button', { name: /테스트고/ });
    schoolButton.focus();
    expect(schoolButton).toHaveFocus();
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(schoolButton).toHaveAttribute('aria-pressed', 'true');
    });

    expect(screen.getByLabelText('시작일', { selector: 'input' })).toBeEnabled();
    expect(screen.getByLabelText('종료일', { selector: 'input' })).toBeEnabled();
  });

  it('prevents meal requests when the date range is invalid', async () => {
    const fetchMock = vi.fn(async (input: string | URL | Request) => {
      const url = toUrl(input);

      if (url.pathname === '/api/schools') {
        return jsonResponse({
          schools: [
            {
              educationOfficeCode: 'B10',
              schoolCode: '7010002',
              name: '범위중',
              region: '서울',
              address: '서울특별시 성북구 예시로 2',
            },
          ],
        });
      }

      throw new Error(`Unhandled request: ${url.toString()}`);
    });

    vi.stubGlobal('fetch', fetchMock);

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText('학교 이름'), '범위중');
    await user.click(screen.getByRole('button', { name: '검색' }));
    await user.click(await screen.findByRole('button', { name: /범위중/ }));

    await user.type(screen.getByLabelText('시작일', { selector: 'input' }), '2026-09-03');
    await user.type(screen.getByLabelText('종료일', { selector: 'input' }), '2026-09-01');

    expect(screen.getByText('시작일은 종료일보다 늦을 수 없습니다.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '중식 조회' })).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('shows retry UI when school search fails and preserves the entered query', async () => {
    let attempts = 0;
    const fetchMock = vi.fn(async (input: string | URL | Request) => {
      const url = toUrl(input);

      if (url.pathname !== '/api/schools') {
        throw new Error(`Unhandled request: ${url.toString()}`);
      }

      attempts += 1;
      if (attempts === 1) {
        return errorResponse(503, '학교 검색을 처리하지 못했습니다.');
      }

      return jsonResponse({
        schools: [
          {
            educationOfficeCode: 'B10',
            schoolCode: '7010003',
            name: '재시도고',
            region: '대전',
            address: '대전광역시 서구 예시로 3',
          },
        ],
      });
    });

    vi.stubGlobal('fetch', fetchMock);

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText('학교 이름'), '재시도고');
    await user.click(screen.getByRole('button', { name: '검색' }));

    await screen.findByRole('alert');
    expect(screen.getByDisplayValue('재시도고')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '다시 시도' }));
    expect(await screen.findByRole('button', { name: /재시도고/ })).toBeInTheDocument();
  });

  it('rejects a successful response that does not match the internal API contract', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse({ schools: [{ name: '식별자 없는 학교' }] })),
    );

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText('학교 이름'), '잘못된응답');
    await user.click(screen.getByRole('button', { name: '검색' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('서버 응답 형식이 올바르지 않습니다');
  });

  it('ignores stale school search responses that arrive after a newer search', async () => {
    const firstResponse = deferredResponse();
    const secondResponse = deferredResponse();

    const fetchMock = vi.fn((input: string | URL | Request) => {
      const url = toUrl(input);
      const query = url.searchParams.get('query');

      if (url.pathname !== '/api/schools' || query === null) {
        throw new Error(`Unhandled request: ${url.toString()}`);
      }

      if (query === '느린학교') {
        return firstResponse.promise;
      }

      if (query === '빠른학교') {
        return secondResponse.promise;
      }

      throw new Error(`Unexpected query: ${query}`);
    });

    vi.stubGlobal('fetch', fetchMock);

    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText('학교 이름'), '느린학교');
    await user.click(screen.getByRole('button', { name: '검색' }));
    await user.clear(screen.getByLabelText('학교 이름'));
    await user.type(screen.getByLabelText('학교 이름'), '빠른학교');

    firstResponse.resolve(
      jsonResponse({
        schools: [
          {
            educationOfficeCode: 'B10',
            schoolCode: '7010005',
            name: '느린학교',
            region: '울산',
            address: '울산광역시 남구 예시로 5',
          },
        ],
      }),
    );

    await waitFor(() => {
      expect(screen.queryByRole('button', { name: /느린학교/ })).not.toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: '검색' }));

    secondResponse.resolve(
      jsonResponse({
        schools: [
          {
            educationOfficeCode: 'B10',
            schoolCode: '7010004',
            name: '빠른학교',
            region: '광주',
            address: '광주광역시 북구 예시로 4',
          },
        ],
      }),
    );

    expect(await screen.findByRole('button', { name: /빠른학교/ })).toBeInTheDocument();
  });

  it('selects exactly two random schools, creates an editable prompt, and renders analysis results', async () => {
    const schools = Array.from({ length: 10 }, (_, index) => ({
      educationOfficeCode: index === 0 ? 'B10' : 'C10',
      schoolCode: `701000${index + 1}`,
      name: `후보학교${index + 1}`,
      region: '서울',
      address: `서울특별시 예시로 ${index + 1}`,
    }));
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: string | URL | Request) => {
        const url = toUrl(input);
        if (url.pathname === '/api/schools/random') {
          return jsonResponse({ schools });
        }
        throw new Error(`Unhandled request: ${url.toString()}`);
      }),
    );

    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('button', { name: '급식 정보 분석' }));

    const candidateList = await screen.findByRole('list', { name: '무작위 학교 후보' });
    const candidates = within(candidateList).getAllByRole('button');
    expect(candidates).toHaveLength(10);
    await user.click(candidates[0]);
    await user.click(candidates[1]);
    expect(candidates[2]).toBeDisabled();

    const dateInput = screen.getByLabelText('분석 날짜', { selector: 'input' });
    await user.type(dateInput, dateInput.getAttribute('max') ?? '');
    expect(await screen.findByDisplayValue(/후보학교1와 후보학교2/)).toBeInTheDocument();

    const promptInput = screen.getByLabelText('분석 프롬프트');
    await user.clear(promptInput);
    await user.type(promptInput, '수정한 분석 요청');
    await user.click(screen.getByRole('button', { name: '멀티에이전트 분석 시작' }));

    expect(await screen.findByRole('heading', { name: /후보학교1 승리/ })).toBeInTheDocument();
    expect(screen.getByText('84.0점', { exact: false })).toBeInTheDocument();
    expect(screen.getByText('79.0점', { exact: false })).toBeInTheDocument();
    expect(screen.getByText(/영양사의 전문 진단을 대체하지 않습니다/)).toBeInTheDocument();
  });
});
