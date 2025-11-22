export interface Survey {
  id: number;
  organization_id: number;
  name: string;
  slug: string;
  survey_type: 'regular' | 'ab_test';
  status: 'draft' | 'live' | 'archived';
  flow_json?: any;
  variant_a_flow?: any;
  variant_b_flow?: any;
  created_at: string;
  updated_at: string;
  published_at?: string;
}

export interface SurveyCreate {
  name: string;
  slug: string;
  survey_type: 'regular' | 'ab_test';
  status: 'draft' | 'live' | 'archived';
  organization_id: number;
  flow_json?: any;
  variant_a_flow?: any;
  variant_b_flow?: any;
}

export interface SurveyUpdate {
  name?: string;
  slug?: string;
  survey_type?: 'regular' | 'ab_test';
  status?: 'draft' | 'live' | 'archived';
  flow_json?: any;
  variant_a_flow?: any;
  variant_b_flow?: any;
}

export interface SurveyStats {
  survey_id: number;
  total_responses: number;
  completed_responses: number;
  avg_score: number;
  avg_completion_time_minutes?: number;
  variant_a_responses?: number;
  variant_b_responses?: number;
  variant_a_avg_score?: number;
  variant_b_avg_score?: number;
}
