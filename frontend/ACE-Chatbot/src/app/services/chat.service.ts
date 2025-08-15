import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

export type ChatMode = 'guided' | 'open';

export interface QuickReply { title: string; payload: string; }
export interface UIChoices { type: 'choices'; buttons: QuickReply[]; }
export interface UIFormField {
  name: 'industry'|'budget'|'experience';
  label: string;
  type: 'text'|'select'|'textarea';
  required?: boolean;
  options?: { label: string; value: string }[];
}
export interface UIForm { type: 'form'; form: { title: string; fields: UIFormField[]; submitLabel: string; }; }
export type UIBlock = UIChoices | UIForm | null;

export interface ChatResponse {
  reply: string;
  quickReplies?: QuickReply[] | null;
  ui?: UIBlock;
  chatMode: ChatMode;
  storyComplete: boolean;
  imageUrl?: string | null;
}

@Injectable({ providedIn: 'root' })
export class ChatService {
  private base = 'http://localhost:8000';
  constructor(private http: HttpClient) {}

  chat(sid: string, message: string, firstVisit = false) {
    return this.http.post<ChatResponse>(`${this.base}/chat`, { sid, message, meta: { first_visit: firstVisit } });
  }

  survey(sid: string, industry: string, budget: string, experience: string) {
    return this.http.post<ChatResponse>(`${this.base}/survey`, { sid, industry, budget, experience });
  }
}
