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

export interface Meal {
  date: string;
  mealType: 'lunch';
  menu: string[];
  calories?: string;
  nutrition?: Record<string, string>;
  origin?: string;
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
