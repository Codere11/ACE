import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Survey, SurveyCreate, SurveyUpdate, SurveyStats } from '../models/survey.model';
import { SurveyResponse } from '../models/response.model';
import { AuthService } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class SurveysService {
  private apiUrl = 'http://localhost:8000/api/organizations';

  constructor(
    private http: HttpClient,
    private authService: AuthService
  ) {}

  private getOrgId(): number {
    return this.authService.getCurrentUser()?.organization_id || 1;
  }

  listSurveys(status?: string): Observable<Survey[]> {
    const params = status ? { status } : {};
    return this.http.get<Survey[]>(`${this.apiUrl}/${this.getOrgId()}/surveys`, { params });
  }

  getSurvey(surveyId: number): Observable<Survey> {
    return this.http.get<Survey>(`${this.apiUrl}/${this.getOrgId()}/surveys/${surveyId}`);
  }

  createSurvey(survey: SurveyCreate): Observable<Survey> {
    return this.http.post<Survey>(`${this.apiUrl}/${this.getOrgId()}/surveys`, survey);
  }

  updateSurvey(surveyId: number, survey: SurveyUpdate): Observable<Survey> {
    return this.http.put<Survey>(`${this.apiUrl}/${this.getOrgId()}/surveys/${surveyId}`, survey);
  }

  publishSurvey(surveyId: number): Observable<Survey> {
    return this.http.post<Survey>(`${this.apiUrl}/${this.getOrgId()}/surveys/${surveyId}/publish`, {});
  }

  archiveSurvey(surveyId: number): Observable<Survey> {
    return this.http.post<Survey>(`${this.apiUrl}/${this.getOrgId()}/surveys/${surveyId}/archive`, {});
  }

  deleteSurvey(surveyId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${this.getOrgId()}/surveys/${surveyId}`);
  }

  getSurveyStats(surveyId: number): Observable<SurveyStats> {
    return this.http.get<SurveyStats>(`${this.apiUrl}/${this.getOrgId()}/surveys/${surveyId}/stats`);
  }

  getSurveyResponses(surveyId: number): Observable<SurveyResponse[]> {
    return this.http.get<SurveyResponse[]>(`${this.apiUrl}/${this.getOrgId()}/surveys/${surveyId}/responses`);
  }
}
