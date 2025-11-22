export interface SurveyResponse {
  id: number;
  survey_id: number;
  organization_id: number;
  sid: string;
  variant?: 'a' | 'b';
  name: string;
  email: string;
  phone: string;
  survey_answers?: any;
  score: number;
  interest: 'Low' | 'Medium' | 'High';
  survey_started_at: string;
  survey_completed_at?: string;
  survey_progress: number;
  notes: string;
  created_at: string;
  updated_at: string;
}
