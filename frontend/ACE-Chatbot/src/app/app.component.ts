import { Component, OnInit, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser, CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule, HttpHeaders } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

interface Message { role: 'user' | 'assistant'; text?: string; typing?: boolean; }
interface ChatResponse { reply?: string; quickReplies?: { title: string; payload: string }[]; ui?: any; chatMode: 'guided'|'open'; storyComplete?: boolean; imageUrl?: string|null; }

@Component({
  selector: 'app-root',
  standalone: true,
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  imports: [CommonModule, FormsModule, HttpClientModule]
})
export class AppComponent implements OnInit {
  messages: Message[] = [];
  ui: any = null;
  chatMode: 'guided'|'open' = 'guided';
  loading = false;

  // NOTE: SID is created ONLY on the browser and stored in localStorage
  sid = 'SSR_NO_SID';
  backendUrl = 'http://localhost:8000';

  private singleSubmitting = false;
  private surveySubmitting = false;
  private isBrowser = false;

  constructor(private http: HttpClient, @Inject(PLATFORM_ID) platformId: Object) {
    this.isBrowser = isPlatformBrowser(platformId);

    if (this.isBrowser) {
      // one stable SID per browser (tab refresh-safe)
      const existing = localStorage.getItem('ace_sid');
      if (existing && existing.length >= 8) {
        this.sid = existing;
      } else {
        this.sid = Math.random().toString(36).slice(2);
        localStorage.setItem('ace_sid', this.sid);
      }
      console.debug('[SID] init(browser)', { sid: this.sid });
    } else {
      // SSR path: DO NOT start chat or call backend here
      this.sid = 'SSR_NO_SID';
      console.debug('[SID] init(ssr) — no network calls, no SID creation');
    }
  }

  ngOnInit() {
    if (!this.isBrowser) return;           // ✅ prevent SSR double-start
    this.send('/start');                   // only on the client
  }

  private rid(prefix: string) {
    return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2,8)}`;
  }

  private headers(rid: string) {
    return new HttpHeaders({ 'X-Req-Id': rid, 'X-Sid': this.sid, 'Content-Type': 'application/json' });
  }

  send(text: string) {
    if (!this.isBrowser) return;           // ✅ never send from SSR
    if (!text.trim()) return;
    const rid = this.rid('SEND');

    console.groupCollapsed(`[FE] ${rid} send() text='${text}'`);
    console.debug('[SID] using', { sid: this.sid });

    this.messages.push({ role: 'user', text });
    this.startTyping();
    this.loading = true;

    const isOpenInput = !!(this.ui && this.ui.openInput === true);
    console.debug('[FE] state before send', { chatMode: this.chatMode, isOpenInput, ui: this.ui });

    if (this.chatMode === 'open' && !isOpenInput) {
      console.debug('[FE] streaming /chat/stream', { rid, sid: this.sid, url: `${this.backendUrl}/chat/stream` });
      console.groupEnd();
      this.sendStream(text, rid);
      return;
    }

    const body = { message: text, sid: this.sid };
    console.debug('[FE] POST /chat/ body', body);

    this.http.post<ChatResponse>(`${this.backendUrl}/chat/`, body, { headers: this.headers(rid) })
      .subscribe({
        next: res => { console.debug('[FE] /chat/ OK', { rid, res }); console.groupEnd(); this.consume(res); },
        error: err => { console.error('[FE] /chat/ ERR', { rid, err }); console.groupEnd(); this.loading = false; this.stopTyping('⚠️ Napaka pri komunikaciji s strežnikom.'); }
      });
  }

  async sendStream(text: string, ridOuter?: string) {
    if (!this.isBrowser) return;           // ✅ never stream from SSR
    const rid = ridOuter || this.rid('STRM');
    console.groupCollapsed(`[FE] ${rid} sendStream() text='${text}'`);
    console.debug('[SID] using', { sid: this.sid });

    try {
      const response = await fetch(`${this.backendUrl}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Req-Id': rid, 'X-Sid': this.sid },
        body: JSON.stringify({ message: text, sid: this.sid })
      });

      if (!response.body) throw new Error('No response body');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      this.messages.pop();
      this.messages.push({ role: 'assistant', text: '' });

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        this.messages[this.messages.length - 1].text = buffer;
      }

      this.loading = false;
      console.groupEnd();
    } catch (err) {
      console.error('[FE] stream ERR', { rid, err });
      this.loading = false;
      this.stopTyping('⚠️ Napaka pri pretakanju odgovora.');
      console.groupEnd();
    }
  }

  sendSingle(answer: string) {
    if (!this.isBrowser) return;           // ✅ guard
    if (!answer.trim()) return;
    if (this.singleSubmitting) return;
    this.singleSubmitting = true;

    const rid = this.rid('SINGLE');
    console.groupCollapsed(`[FE] ${rid} sendSingle() answer='${answer}'`);
    console.debug('[SID] using', { sid: this.sid });

    this.messages.push({ role: 'user', text: answer });
    this.startTyping();
    this.loading = true;

    const body = { sid: this.sid, message: answer };
    console.debug('[FE] POST /chat/ body', body);

    this.http.post<ChatResponse>(`${this.backendUrl}/chat/`, body, { headers: this.headers(rid) })
      .subscribe({
        next: res => { this.singleSubmitting = false; console.debug('[FE] /chat/ OK', { rid, res }); console.groupEnd(); this.consume(res); },
        error: err => { this.singleSubmitting = false; console.error('[FE] /chat/ ERR', { rid, err }); console.groupEnd(); this.loading = false; this.stopTyping('⚠️ Napaka pri pošiljanju odgovora.'); }
      });
  }

  sendSurvey(ans1: string, ans2: string) {
    if (!this.isBrowser) return;           // ✅ guard
    if (!ans1.trim() && !ans2.trim()) return;
    if (this.surveySubmitting) return;
    this.surveySubmitting = true;

    const rid = this.rid('SURVEY');
    console.groupCollapsed(`[FE] ${rid} sendSurvey() Q1='${ans1}' Q2='${ans2}'`);
    console.debug('[SID] using', { sid: this.sid });

    this.messages.push({ role: 'user', text: `Q1: ${ans1} | Q2: ${ans2}` });
    this.startTyping();
    this.loading = true;

    const body = { sid: this.sid, industry: '', budget: '', experience: '', question1: ans1, question2: ans2 };
    console.debug('[FE] POST /chat/survey body', body);

    this.http.post<ChatResponse>(`${this.backendUrl}/chat/survey`, body, { headers: this.headers(rid) })
      .subscribe({
        next: res => { this.surveySubmitting = false; console.debug('[FE] /chat/survey OK', { rid, res }); console.groupEnd(); this.consume(res); },
        error: err => { this.surveySubmitting = false; console.error('[FE] /chat/survey ERR', { rid, err }); console.groupEnd(); this.loading = false; this.stopTyping('⚠️ Napaka pri pošiljanju ankete.'); }
      });
  }

  onSubmitSingle(input: HTMLInputElement) {
    const v = input.value.trim();
    if (!v) return;
    input.value = '';
    this.sendSingle(v);
  }

  onSubmitSurvey(i1: HTMLInputElement, i2: HTMLInputElement) {
    const a1 = i1.value.trim();
    const a2 = i2.value.trim();
    if (!a1 && !a2) return;
    i1.value = ''; i2.value = '';
    this.sendSurvey(a1, a2);
  }

  clickQuickReply(q: any) { this.send(q.title); }

  private consume(res: ChatResponse) {
    this.loading = false;
    if (res.reply !== undefined) this.stopTyping(res.reply);
    if (res.ui) this.ui = res.ui;
    else if (res.quickReplies) this.ui = { type: 'choices', buttons: res.quickReplies };
    else this.ui = null;
    this.chatMode = res.chatMode;
  }

  private startTyping() { if (!this.isTypingActive()) this.messages.push({ role: 'assistant', typing: true }); }
  private stopTyping(replaceWith?: string) {
    const last = this.messages[this.messages.length - 1];
    if (last && last.typing) { this.messages.pop(); if (replaceWith !== undefined) this.messages.push({ role: 'assistant', text: replaceWith }); }
  }
  private isTypingActive(): boolean {
    const last = this.messages[this.messages.length - 1];
    return !!(last && last.typing);
  }
}
