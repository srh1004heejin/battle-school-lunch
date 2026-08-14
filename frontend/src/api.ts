export interface School {
  educationOfficeCode: string;
  schoolCode: string;
  name: string;
  region: string;
  address: string;
}

export interface Meal {
  date: string;
  mealType: "lunch";
  menu: string[];
  calories?: string;
  nutrition?: Record<string, string>;
  origin?: string;
}

export interface MealsResponse {
  school: Pick<School, "educationOfficeCode" | "schoolCode" | "name">;
  from: string;
  to: string;
  meals: Meal[];
}

interface ErrorResponse {
  error?: {
    code?: string;
    message?: string;
    requestId?: string;
  };
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(path, {
    signal,
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    let body: ErrorResponse | undefined;
    try {
      body = (await response.json()) as ErrorResponse;
    } catch {
      body = undefined;
    }
    throw new ApiError(
      body?.error?.message ?? "요청을 처리하지 못했어요. 잠시 후 다시 시도해 주세요.",
      response.status,
      body?.error?.requestId,
    );
  }

  return (await response.json()) as T;
}

export async function searchSchools(
  query: string,
  signal?: AbortSignal,
): Promise<School[]> {
  const data = await request<{ schools: School[] }>(
    `/api/schools?query=${encodeURIComponent(query)}`,
    signal,
  );
  return data.schools;
}

export function getMeals(
  school: School,
  from: string,
  to: string,
  signal?: AbortSignal,
): Promise<MealsResponse> {
  const path = `/api/schools/${encodeURIComponent(school.educationOfficeCode)}/${encodeURIComponent(school.schoolCode)}/meals`;
  const query = new URLSearchParams({ from, to, mealType: "lunch" });
  return request<MealsResponse>(`${path}?${query.toString()}`, signal);
}
