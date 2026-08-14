export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    requestId: string;
  };
}

export interface School {
  educationOfficeCode: string;
  schoolCode: string;
  name: string;
  region: string;
  address: string;
}

export interface SchoolSearchResponse {
  schools: School[];
}

export interface RandomSchoolResponse {
  schools: School[];
}

export interface Meal {
  date: string;
  mealType: 'lunch';
  menu: string[];
  calories?: string;
  nutrition?: Record<string, string>;
  origin?: string;
  mealCount?: string;
}

export interface MealSearchResponse {
  school: {
    educationOfficeCode: string;
    schoolCode: string;
    name: string;
  };
  from: string;
  to: string;
  meals: Meal[];
}

export interface MealSearchParams {
  educationOfficeCode: string;
  schoolCode: string;
  from: string;
  to: string;
  mealType: 'lunch';
}

export type EvaluationAreaId =
  | 'nutrition_balance'
  | 'healthiness'
  | 'ingredient_menu_quality';

export interface WeightedAreaScore {
  area: EvaluationAreaId;
  rating: number;
  weight: number;
  weightedScore: number;
  rationale: string;
  evidence: string[];
  estimatedFlags: string[];
}

export interface SchoolScore {
  school: Pick<School, 'educationOfficeCode' | 'schoolCode' | 'name'>;
  areas: WeightedAreaScore[];
  totalScore: number;
}

export interface AnalysisResult {
  analysisId: string;
  scores: SchoolScore[];
  outcome: 'first' | 'second' | 'tie';
  winnerSchool: Pick<School, 'educationOfficeCode' | 'schoolCode' | 'name'> | null;
  review: {
    summary: string;
    keyReason: string;
    firstSchoolImprovement: string;
    secondSchoolImprovement: string;
    qualityWarnings: string[];
  };
  disclaimer: string;
}

export interface AnalysisRequest {
  schools: Array<Pick<School, 'educationOfficeCode' | 'schoolCode' | 'name'>>;
  date: string;
  prompt: string;
}
