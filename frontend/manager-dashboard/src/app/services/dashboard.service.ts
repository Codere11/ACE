import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';

// Types
export type Lead = {
  id: string;
  name: string;
  industry: string;
  score: number;
  stage: string;
  compatibility: boolean;
  interest: 'High' | 'Medium' | 'Low';
  /** NEW: actual strings coming from backend (may be empty). */
  phoneText?: string;
  emailText?: string;
  /** Back-compat flags for UI conditions. */
  phone: boolean;
  email: boolean;
  adsExp: boolean;
  lastMessage: string;
  lastSeenSec: number;
  notes: string;
  
  // Survey fields
  survey_started_at?: string | null;
  survey_completed_at?: string | null;
  survey_answers?: Record<string, any> | null;
  survey_progress?: number;
};

export type KPIs = {
  visitors: number;
  interactions: number;
  contacts: number;
  avgResponseSec: number;
  activeLeads: number;
};

export type Funnel = {
  awareness: number;
  interest: number;
  meeting: number;
  close: number;
};

export type ChatLog = {
  sid: string;
  role: 'user' | 'assistant' | 'staff';
  text: string;
  timestamp: number;
};

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private baseUrl = 'http://127.0.0.1:8000';

  constructor(private http: HttpClient) {}

  getLeads(): Observable<Lead[]> {
    return this.http.get<Lead[]>(`${this.baseUrl}/leads/`).pipe(
      map(list =>
        list.map(l => ({
          ...l,
          // ensure booleans exist even if backend only sends strings
          phone: !!(l as any).phone || !!l.phoneText,
          email: !!(l as any).email || !!l.emailText,
        }))
      )
    );
  }

  getKPIs(): Observable<KPIs> {
    return this.http.get<KPIs>(`${this.baseUrl}/kpis/`);
  }

  getFunnel(): Observable<Funnel> {
    return this.http.get<Funnel>(`${this.baseUrl}/funnel/`);
  }

  getObjections(): Observable<string[]> {
    return this.http.get<string[]>(`${this.baseUrl}/objections/`);
  }

  /** All chats (flat) */
  getChats(): Observable<ChatLog[]> {
    return this.http.get<ChatLog[]>(`${this.baseUrl}/chats/`);
  }

  /** Chats for a specific lead/session id (persistent-first) */
  getChatsForLead(sid: string): Observable<ChatLog[]> {
    return this.http.get<ChatLog[]>(`${this.baseUrl}/chats?sid=${encodeURIComponent(sid)}`);
  }

  /** Send a STAFF message (dashboard takeover) -> persisted as role=staff */
  sendStaffMessage(sid: string, text: string): Observable<{ ok: boolean; message?: ChatLog }> {
    return this.http.post<{ ok: boolean; message?: ChatLog }>(`${this.baseUrl}/chat/staff`, { sid, text });
  }

  /** Delete a lead by ID */
  deleteLead(leadId: string): Observable<{ success: boolean; message: string }> {
    return this.http.delete<{ success: boolean; message: string }>(`${this.baseUrl}/leads/${leadId}`);
  }

  /** Get survey flow for score calculation */
  getSurveyFlow(orgSlug: string, surveySlug: string): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/s/${orgSlug}/${surveySlug}`);
  }
}
