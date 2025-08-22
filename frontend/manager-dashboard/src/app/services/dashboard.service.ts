import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

// Types
export type Lead = {
  name: string;
  industry: string;
  score: number;
  stage: string;
  compatibility: boolean;
  interest: 'High' | 'Medium' | 'Low';
  phone: boolean;
  email: boolean;
  adsExp: boolean;
  lastMessage: string;
  lastSeenSec: number;
  notes: string;
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
  role: string;
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
    return this.http.get<Lead[]>(`${this.baseUrl}/leads/`);
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

  getChats(): Observable<ChatLog[]> {
    return this.http.get<ChatLog[]>(`${this.baseUrl}/chats/`);
  }
}
