import { Component, OnInit, OnDestroy, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser, CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule, HttpHeaders } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { LiveEventsService, ChatEvent } from './services/live-events.service';
import { Subscription } from 'rxjs';

interface Message { role: 'user' | 'assistant' | 'staff'; text?: string; typing?: boolean; }
interface ChatResponse {
  reply?: string;
  quickReplies?: { title: string; payload: string }[];
  ui?: any;
  chatMode: 'guided'|'open';
  storyComplete?: boolean;
  imageUrl?: string|null;
}

@Component({
  selector: 'app-root',
  standalone: true,
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  imports: [CommonModule, FormsModule, HttpClientModule]
})
export class AppComponent implements OnInit, OnDestroy {
  messages: Message[] = [];
  ui: any = null;
  chatMode: 'guided'|'open' = 'guided';
  loading = false;

  sid = 'SSR_NO_SID';
  backendUrl = 'http://localhost:8000';

  private singleSubmitting = false;
  private surveySubmitting = false;
  private isBrowser = false;

  private liveSub?: Subscription;
  private pendingUserTexts = new Set<string>();
  private recentHashes: string[] = [];

  /** When true, we’re in full human takeover: ignore assistant messages */
  humanMode = false;

  constructor(
    private http: HttpClient,
    private live: LiveEventsService,
    @Inject(PLATFORM_ID) platformId: Object
  ) {
    this.isBrowser = isPlatformBrowser(platformId);

    if (this.isBrowser) {
      const existing = localStorage.getItem('ace_sid');
      if (existing && existing.length >= 8) {
        this.sid = existing;
      } else {
        this.sid = Math.random().toString(36).slice(2);
        localStorage.setItem('ace_sid', this.sid);
      }
      console.debug('[SID] init(browser)', { sid: this.sid });
    } else {
      this.sid = 'SSR_NO_SID';
      console.debug('[SID] init(ssr) — no network calls, no SID creation');
    }
  }

  ngOnInit() {
  if (!this.isBrowser) return;

  // Start listening for live events for THIS SID
  this.live.start(this.sid);
  this.liveSub = this.live.events$.subscribe((evt: ChatEvent | null) => {
    if (!evt) return;
    if (evt.type !== 'message.created') return;
    if (evt.sid !== this.sid) return;

    const role = (evt.payload?.role as 'user'|'assistant'|'staff') ?? 'assistant';
    const text = (evt.payload?.text as string) ?? '';

    // If staff speaks -> enable human takeover mode and keep an open composer
    if (role === 'staff') {
      this.humanMode = true;
      this.chatMode = 'open';
      this.ui = { inputType: 'single' };
    }

    // Skip our own just-sent user messages (already shown optimistically)
    if (role === 'user' && this.pendingUserTexts.has(text)) {
      this.pendingUserTexts.delete(text);
      return;
    }

    // During human mode, suppress assistant messages entirely
    if (this.humanMode && role === 'assistant') return;

    // De-dupe
    const h = `${role}|${text}`;
    if (this.recentHashes.includes(h)) return;
    this._rememberHash(h);

    this.messages.push({ role, text });
    this._removeTrailingTypingIfNeeded();
  });

  // ✅ Kick off the conversation (bot greeting) IF not already in human mode
  if (!this.humanMode) {
    this.send('/start');
    }
  }


  ngOnDestroy() {
    if (!this.isBrowser) return;
    this.liveSub?.unsubscribe();
    this.live.stop();
  }

  // Helpers
  private rid(prefix: string) {
    return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2,8)}`;
  }
  private headers(rid: string) {
    return new HttpHeaders({ 'X-Req-Id': rid, 'X-Sid': this.sid, 'Content-Type': 'application/json' });
  }
  private _rememberHash(h: string) {
    this.recentHashes.push(h);
    if (this.recentHashes.length > 100) this.recentHashes.shift();
  }
  private _removeTrailingTypingIfNeeded() {
    const last = this.messages[this.messages.length - 1];
    const prev = this.messages[this.messages.length - 2];
    if (last && prev && prev.typing) this.messages.splice(this.messages.length - 2, 1);
  }

  // Send paths
  send(text: string) {
    if (!this.isBrowser) return;
    if (!text.trim()) return;
    const rid = this.rid('SEND');

    console.groupCollapsed(`[FE] ${rid} send() text='${text}'`);
    console.debug('[SID] using', { sid: this.sid });

    this.messages.push({ role: 'user', text });
    this._rememberHash(`user|${text}`);
    this.pendingUserTexts.add(text);
    setTimeout(() => this.pendingUserTexts.delete(text), 5000);

    this.startTyping();
    this.loading = true;

    // When in human mode, backend will short-circuit with no assistant reply.
    // We still POST so the message is persisted and the manager sees it live.
    const body = { message: text, sid: this.sid };

    this.http.post<ChatResponse>(`${this.backendUrl}/chat/`, body, { headers: this.headers(rid) })
      .subscribe({
        next: res => { console.debug('[FE] /chat/ OK', { rid, res }); console.groupEnd(); this.consume(res); },
        error: err => { console.error('[FE] /chat/ ERR', { rid, err }); console.groupEnd(); this.loading = false; this.stopTyping('⚠️ Napaka pri komunikaciji s strežnikom.'); }
      });
  }

  async sendStream(text: string, ridOuter?: string) {
    if (!this.isBrowser) return;
    const rid = ridOuter || this.rid('STRM');

    // If human mode is on, do not stream; fall back to normal POST.
    if (this.humanMode) {
      this.send(text);
      return;
    }

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

      this._rememberHash(`assistant|${buffer}`);
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
    if (!this.isBrowser) return;
    if (!answer.trim()) return;
    if (this.singleSubmitting) return;
    this.singleSubmitting = true;

    const rid = this.rid('SINGLE');
    console.groupCollapsed(`[FE] ${rid} sendSingle() answer='${answer}'`);
    console.debug('[SID] using', { sid: this.sid });

    this.messages.push({ role: 'user', text: answer });
    this._rememberHash(`user|${answer}`);
    this.pendingUserTexts.add(answer);
    setTimeout(() => this.pendingUserTexts.delete(answer), 5000);

    this.startTyping();
    this.loading = true;

    const body = { sid: this.sid, message: answer };

    this.http.post<ChatResponse>(`${this.backendUrl}/chat/`, body, { headers: this.headers(rid) })
      .subscribe({
        next: res => { this.singleSubmitting = false; console.debug('[FE] /chat/ OK', { rid, res }); console.groupEnd(); this.consume(res); },
        error: err => { this.singleSubmitting = false; console.error('[FE] /chat/ ERR', { rid, err }); console.groupEnd(); this.loading = false; this.stopTyping('⚠️ Napaka pri pošiljanju odgovora.'); }
      });
  }

  sendSurvey(ans1: string, ans2: string) {
    if (!this.isBrowser) return;
    if (!ans1.trim() && !ans2.trim()) return;
    if (this.surveySubmitting) return;
    this.surveySubmitting = true;

    const rid = this.rid('SURVEY');
    console.groupCollapsed(`[FE] ${rid} sendSurvey() Q1='${ans1}' Q2='${ans2}'`);
    console.debug('[SID] using', { sid: this.sid });

    const combo = `Q1: ${ans1} | Q2: ${ans2}`;
    this.messages.push({ role: 'user', text: combo });
    this._rememberHash(`user|${combo}`);
    this.pendingUserTexts.add(combo);
    setTimeout(() => this.pendingUserTexts.delete(combo), 5000);

    this.startTyping();
    this.loading = true;

    const body = { sid: this.sid, industry: '', budget: '', experience: '', question1: ans1, question2: ans2 };

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

  // Default UI shape when in open mode and backend didn't specify one
  if (res.ui == null && res.chatMode === 'open') {
    res.ui = { inputType: 'single' };
  } else if (res.ui && res.chatMode === 'open' && !res.ui.inputType && res.ui.type !== 'choices') {
    res.ui.inputType = 'single';
  }

  // If human takeover is active, ignore assistant replies from POST responses.
  if (!this.humanMode && res.reply !== undefined) {
    this._rememberHash(`assistant|${res.reply}`);
    this.stopTyping(res.reply);
  } else {
    // just remove typing indicator if present
    this.stopTyping();
  }

  // In human mode keep an open composer and do not alter UI based on bot output
  if (this.humanMode) {
    this.chatMode = 'open';
    this.ui = { inputType: 'single' };
    return;
  }

  // Normal (non-takeover) path
  if (res.ui) this.ui = res.ui;
  else if (res.quickReplies) this.ui = { type: 'choices', buttons: res.quickReplies };
  else this.ui = null;

  this.chatMode = res.chatMode;
  }

  private startTyping() {
    if (!this.isTypingActive()) this.messages.push({ role: 'assistant', typing: true });
  }

  private stopTyping(replaceWith?: string) {
    const last = this.messages[this.messages.length - 1];
    if (last && last.typing) {
      this.messages.pop();
      if (replaceWith !== undefined) this.messages.push({ role: 'assistant', text: replaceWith });
    }
  }

  private isTypingActive(): boolean {
    const last = this.messages[this.messages.length - 1];
    return !!(last && last.typing);
  }
  
}
