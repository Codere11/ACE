import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { tap } from 'rxjs/operators';

export type ChatMode = 'guided' | 'open';

export interface QuickReply { title: string; payload: string; }

// Keep old UI types, but don’t block extra fields from BE.
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

// Loosen ChatResponse so we don’t “lose” fields like action/payload/images
export interface ChatResponse {
  reply: string;
  quickReplies?: QuickReply[] | null;
  ui?: UIBlock | any;
  chatMode: ChatMode;
  storyComplete: boolean;
  imageUrl?: string | null;

  // pass-through fields (if server sends them)
  uiAction?: string;
  action?: string;
  payload?: any;
  images?: any;
  image?: any;
  address?: string;
}

@Injectable({ providedIn: 'root' })
export class ChatService {
  private base = 'http://localhost:8000';

  constructor(private http: HttpClient) {
    console.debug('[FE][ChatService] init', { base: this.base });
  }

  chat(sid: string, message: string, firstVisit = false) {
    const payload = { sid, message };
    console.debug('[FE][ChatService] POST /chat/ payload', payload);
    return this.http.post<ChatResponse>(`${this.base}/chat/`, payload).pipe(
      tap({
        next: res => console.debug('[FE][ChatService] /chat OK', { sid, res }),
        error: err => console.debug('[FE][ChatService] /chat ERR', { sid, err })
      })
    );
  }

  survey(sid: string, industry: string, budget: string, experience: string, question1: string, question2: string) {
    const payload = { sid, industry, budget, experience, question1, question2 };
    console.debug('[FE][ChatService] POST /chat/survey payload', payload);
    return this.http.post<ChatResponse>(`${this.base}/chat/survey`, payload).pipe(
      tap({
        next: res => console.debug('[FE][ChatService] /chat/survey OK', { sid, res }),
        error: err => console.debug('[FE][ChatService] /chat/survey ERR', { sid, err })
      })
    );
  }
}
