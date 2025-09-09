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

type Channel = 'email'|'phone'|'whatsapp'|'sms';

@Component({
  selector: 'app-root',
  standalone: true,
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  imports: [CommonModule, FormsModule, HttpClientModule]
})
export class AppComponent implements OnInit, OnDestroy {
  // === Agent identity (for the hero header) ===
  agentName = 'Matic';               // <- change name if needed
  agentPhotoUrl = '/agents/matic.png';

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

  /** Full human takeover: ignore assistant messages */
  humanMode = false;
  typingLabel: string | null = null;

  /** We no longer show the old gate form; the flow itself asks for dual contact first. */
  contactPending = false;

  contact: { name: string; email: string; phone: string; channel: Channel } = {
    name: '', email: '', phone: '', channel: 'email'
  };

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
      console.debug('[SID] init(ssr)');
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

      if (role === 'staff') {
        // when staff joins, switch to 1-on-1
        this.humanMode = true;
        this.chatMode = 'open';
        this.ui = { inputType: 'single' };
      }

      if (role === 'user' && this.pendingUserTexts.has(text)) {
        this.pendingUserTexts.delete(text);
        return;
      }

      if (this.humanMode && role === 'assistant') return;

      const h = `${role}|${text}`;
      if (this.recentHashes.includes(h)) return;
      this._rememberHash(h);

      this.messages.push({ role, text });
      this._removeTrailingTypingIfNeeded();
    });

    // Kick off bot greeting -> welcome node (dual-contact)
    if (!this.humanMode) {
      this.send('/start');
    }
  }

  ngOnDestroy() {
    if (!this.isBrowser) return;
    this.liveSub?.unsubscribe();
    this.live.stop();
  }

  // ---------- Dual contact sender ----------
  sendContactDual(email: string, phone: string) {
    const e = (email || '').trim();
    const p = (phone || '').trim();
    if (!e && !p) {
      this.messages.push({ role: 'assistant', text: 'Dodaj vsaj e-pošto ali telefon, prosim. 🙏' });
      return;
    }
    const rid = this.rid('CONTACT2');
    const payload = { email: e, phone: p, channel: e ? 'email' : 'phone' };

    this.startTyping('Shranjujem kontakt…');
    this.loading = true;

    this.http.post<ChatResponse>(
      `${this.backendUrl}/chat/`,
      { sid: this.sid, message: `/contact ${JSON.stringify(payload)}` },
      { headers: this.headers(rid) }
    ).subscribe({
      next: (res) => { this.loading = false; this.consume(res); },
      error: (err) => {
        console.error('[FE] contact dual ERR', { rid, err });
        this.loading = false;
        this.stopTyping('⚠️ Ni uspelo shraniti. Poskusi znova.');
      }
    });
  }

  // ---------- Global Skip → human 1-on-1 ----------
  skipToHuman(fromGate = false) {
    if (!this.isBrowser) return;
    const rid = this.rid('SKIP');

    // Mark UI state
    this.humanMode = true;
       this.chatMode = 'open';
    this.ui = { inputType: 'single' };

    // Show local notice
    this.messages.push({ role: 'assistant', text: 'Povezujem te z agentom. Piši vprašanje kar tukaj 👇' });

    // Notify backend (analytics / takeover trigger)
    fetch(`${this.backendUrl}/chat/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Req-Id': rid, 'X-Sid': this.sid },
      body: JSON.stringify({ sid: this.sid, message: '/skip_to_human' })
    }).catch(err => console.error('[FE] skip notify ERR', { rid, err }));
  }

  // ---------- Helpers ----------
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

  // ---------- Send paths ----------
  send(text: string) {
    if (!this.isBrowser) return;
    if (!text.trim()) return;
    const rid = this.rid('SEND');

    this.messages.push({ role: 'user', text });
    this._rememberHash(`user|${text}`);
    this.pendingUserTexts.add(text);
    setTimeout(() => this.pendingUserTexts.delete(text), 5000);

    this.startTyping('Razmišljam…');
    this.loading = true;

    const body = { message: text, sid: this.sid };

    this.http.post<ChatResponse>(`${this.backendUrl}/chat/`, body, { headers: this.headers(rid) })
      .subscribe({
        next: res => { this.consume(res); },
        error: err => { console.error('[FE] /chat/ ERR', { rid, err }); this.loading = false; this.stopTyping('⚠️ Napaka pri komunikaciji s strežnikom.'); }
      });
  }

  async sendStream(text: string, ridOuter?: string) {
    if (!this.isBrowser) return;
    const rid = ridOuter || this.rid('STRM');

    if (this.humanMode) {
      this.send(text);
      return;
    }

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
    } catch (err) {
      console.error('[FE] stream ERR', { rid, err });
      this.loading = false;
      this.stopTyping('⚠️ Napaka pri pretakanju odgovora.');
    }
  }

  sendSingle(answer: string) {
    if (!this.isBrowser) return;
    if (!answer.trim()) return;
    if (this.singleSubmitting) return;
    this.singleSubmitting = true;

    const rid = this.rid('SINGLE');

    this.messages.push({ role: 'user', text: answer });
    this._rememberHash(`user|${answer}`);
    this.pendingUserTexts.add(answer);
    setTimeout(() => this.pendingUserTexts.delete(answer), 5000);

    this.startTyping();
    this.loading = true;

    const body = { sid: this.sid, message: answer };

    this.http.post<ChatResponse>(`${this.backendUrl}/chat/`, body, { headers: this.headers(rid) })
      .subscribe({
        next: res => { this.singleSubmitting = false; this.consume(res); },
        error: err => { this.singleSubmitting = false; console.error('[FE] /chat/ ERR', { rid, err }); this.loading = false; this.stopTyping('⚠️ Napaka pri pošiljanju odgovora.'); }
      });
  }

  sendSurvey(ans1: string, ans2: string) {
    if (!this.isBrowser) return;
    if (!ans1.trim() && !ans2.trim()) return;
    if (this.surveySubmitting) return;
    this.surveySubmitting = true;

    const rid = this.rid('SURVEY');

    const combo = `Q1: ${ans1} | Q2: ${ans2}`;
    this.messages.push({ role: 'user', text: combo });
    this._rememberHash(`user|${combo}`);
    this.pendingUserTexts.add(combo);
    setTimeout(() => this.pendingUserTexts.delete(combo), 5000);

    this.startTyping('Sestavljam odgovore…');
    this.loading = true;

    const body = { sid: this.sid, industry: '', budget: '', experience: '', question1: ans1, question2: ans2 };

    this.http.post<ChatResponse>(`${this.backendUrl}/chat/survey`, body, { headers: this.headers(rid) })
      .subscribe({
        next: res => { this.surveySubmitting = false; this.consume(res); },
        error: err => { this.surveySubmitting = false; console.error('[FE] /chat/survey ERR', { rid, err }); this.loading = false; this.stopTyping('⚠️ Napaka pri pošiljanju ankete.'); }
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

    if (res.ui == null && res.chatMode === 'open') {
      res.ui = { inputType: 'single' };
    } else if (res.ui && res.chatMode === 'open' && !res.ui.inputType && res.ui.type !== 'choices') {
      res.ui = { ...(res.ui || {}), inputType: 'single' };
    }

    if (!this.humanMode && res.reply !== undefined) {
      this._rememberHash(`assistant|${res.reply}`);
      this.stopTyping(res.reply);
    } else {
      this.stopTyping();
    }

    if (this.humanMode) {
      this.chatMode = 'open';
      this.ui = { inputType: 'single' };
      return;
    }

    if (res.ui) this.ui = res.ui;
    else if (res.quickReplies) this.ui = { type: 'choices', buttons: res.quickReplies };
    else this.ui = null;

    this.chatMode = res.chatMode;
  }

  private startTyping(label?: string) {
    if (!this.isTypingActive()) this.messages.push({ role: 'assistant', typing: true });
    this.typingLabel = label ?? this.typingLabel ?? 'Razmišljam…';
  }

  private stopTyping(replaceWith?: string) {
    const last = this.messages[this.messages.length - 1];
    if (last && last.typing) {
      this.messages.pop();
      if (replaceWith !== undefined) this.messages.push({ role: 'assistant', text: replaceWith });
    }
    this.typingLabel = null;
  }

  private isTypingActive(): boolean {
    const last = this.messages[this.messages.length - 1];
    return !!(last && last.typing);
  }
}
