import { Component, OnInit, OnDestroy, Inject, PLATFORM_ID, ElementRef, ViewChild, AfterViewInit, NgZone } from '@angular/core';
import { isPlatformBrowser, CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule, HttpHeaders } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { LiveEventsService, ChatEvent } from './services/live-events.service';
import { Subscription } from 'rxjs';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

type Role = 'user' | 'assistant' | 'staff';
type Channel = 'email'|'phone'|'whatsapp'|'sms';

interface Message {
  role: Role;
  text?: string;
  typing?: boolean;

  gallery?: string[];
  image?: { src: string; label?: string };
  map?: { address: string };

  _id?: string;
}

interface ChatResponse {
  reply?: string;
  quickReplies?: { title: string; payload?: string; next?: string }[];
  ui?: any;
  uiAction?: string;
  action?: string;
  payload?: any;
  images?: any;
  image?: any;
  address?: string;
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
export class AppComponent implements OnInit, OnDestroy, AfterViewInit {
  // ====== CONFIG ======
  private LOG_VERBOSITY = 3; // 0=silent, 1=warn, 2=info, 3=debug
  private FALLBACK_ASSETS = {
    gallery: ['/listings/vila-zelena.png'],
    floorplan: '/listings/tloris.png',
    map_address: 'Vič, Ljubljana'
  };

  // ====== Agent identity ======
  agentName = 'Matic';
  agentPhotoUrl = '/agents/matic.png';

  // ====== Chat state ======
  messages: Message[] = [];
  ui: any = null;
  chatMode: 'guided'|'open' = 'guided';
  loading = false;

  // ====== Infra ======
  sid = 'SSR_NO_SID';
  backendUrl = 'http://localhost:8000';

  private singleSubmitting = false;
  private surveySubmitting = false;
  private isBrowser = false;

  private liveSub?: Subscription;
  private pendingUserTexts = new Set<string>();
  private recentHashes: string[] = [];

  humanMode = false;
  typingLabel: string | null = null;

  contactPending = false;

  contact: { name: string; email: string; phone: string; channel: Channel } = {
    name: '', email: '', phone: '', channel: 'email'
  };

  @ViewChild('messagesRef') private messagesRef?: ElementRef<HTMLDivElement>;

  constructor(
    private http: HttpClient,
    private live: LiveEventsService,
    private zone: NgZone,
    private sanitizer: DomSanitizer,
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
      this.d('[SID] init(browser)', { sid: this.sid });
    } else {
      this.sid = 'SSR_NO_SID';
      this.d('[SID] init(ssr)');
    }
  }

  // ====== Logger helpers ======
  private d(...a: any[]) { if (this.LOG_VERBOSITY >= 3) console.debug('[ACE]', ...a); }
  private i(...a: any[]) { if (this.LOG_VERBOSITY >= 2) console.info('[ACE]', ...a); }
  private w(...a: any[]) { if (this.LOG_VERBOSITY >= 1) console.warn('[ACE]', ...a); }
  private e(...a: any[]) { console.error('[ACE]', ...a); }

  ngAfterViewInit() { this.scrollToBottomSoon(); }

  ngOnInit() {
    if (!this.isBrowser) return;

    this.d('ngOnInit → starting LiveEvents for SID', this.sid);
    this.live.start(this.sid);
    this.liveSub = this.live.events$.subscribe((evt: ChatEvent | null) => {
      if (!evt) return;
      this.d('LiveEvent received', evt);
      if (evt.type !== 'message.created') return;
      if (evt.sid !== this.sid) return;

      const role = (evt.payload?.role as Role) ?? 'assistant';
      const text = (evt.payload?.text as string) ?? '';

      if (role === 'staff') {
        this.i('Staff takeover detected → switching to humanMode');
        this.humanMode = true;
        this.chatMode = 'open';
        this.ui = { inputType: 'single' };
      }

      if (role === 'user' && this.pendingUserTexts.has(text)) {
        this.d('Skipping echoed user message from server', text);
        this.pendingUserTexts.delete(text);
        return;
      }

      if (this.humanMode && role === 'assistant') {
        this.d('Human mode: suppressing assistant message', { text });
        return;
      }

      const h = `${role}|${text}`;
      if (this.recentHashes.includes(h)) {
        this.d('Duplicate message suppressed by hash', h);
        return;
      }
      this._rememberHash(h);

      const m: Message = { role, text, _id: this.rid('MSG') };
      this.d('Pushing server message', m);
      this.messages.push(m);
      this._removeTrailingTypingIfNeeded();

      // Extract UI blocks from event payload (if BE ever sends them)
      this.extractAndRenderFromAny(evt.payload, 'event');

      // Heuristic fallback (in case BE only sends a plain sentence)
      if (role === 'assistant' && typeof text === 'string') this.tryHeuristics(text);

      this.scrollToBottomSoon();
    });

    if (!this.humanMode) {
      this.d('Initial /start');
      this.send('/start');
    }
  }

  ngOnDestroy() {
    if (!this.isBrowser) return;
    this.d('ngOnDestroy → stopping LiveEvents');
    this.liveSub?.unsubscribe();
    this.live.stop();
  }

  // ---------- Dual contact sender ----------
  sendContactDual(email: string, phone: string) {
    const e = (email || '').trim();
    const p = (phone || '').trim();
    this.i('sendContactDual()', { email: e, phone: p });

    if (!e && !p) {
      this.w('No contact provided');
      this.messages.push({ role: 'assistant', text: 'Dodaj vsaj e-pošto ali telefon, prosim. 🙏', _id: this.rid('MSG') });
      this.scrollToBottomSoon();
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
      next: (res) => { this.i('[HTTP /chat] contact dual OK', { rid, res }); this.loading = false; this.consume(res); },
      error: (err) => { this.e('[HTTP /chat] contact dual ERR', { rid, err }); this.loading = false; this.stopTyping('⚠️ Ni uspelo shraniti. Poskusi znova.'); }
    });
  }

  // ---------- Global Skip → human 1-on-1 ----------
  skipToHuman() {
    if (!this.isBrowser) return;
    const rid = this.rid('SKIP');

    this.i('skipToHuman()');

    this.humanMode = true;
       this.chatMode = 'open';
    this.ui = { inputType: 'single' };

    this.messages.push({ role: 'assistant', text: 'Povezujem te z agentom. Piši vprašanje kar tukaj 👇', _id: this.rid('MSG') });
    this.scrollToBottomSoon();

    fetch(`${this.backendUrl}/chat/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Req-Id': rid, 'X-Sid': this.sid },
      body: JSON.stringify({ sid: this.sid, message: '/skip_to_human' })
    }).catch(err => this.e('[FE] skip notify ERR', { rid, err }));
  }

  // ---------- Send paths ----------
  send(text: string) {
    if (!this.isBrowser) return;
    if (!text.trim()) return;
    const rid = this.rid('SEND');

    this.i('send()', { text, rid });

    this.messages.push({ role: 'user', text, _id: this.rid('MSG') });
    this._rememberHash(`user|${text}`);
    this.pendingUserTexts.add(text);
    setTimeout(() => this.pendingUserTexts.delete(text), 5000);

    this.startTyping('Razmišljam…');
    this.loading = true;

    const body = { message: text, sid: this.sid };

    this.http.post<ChatResponse>(`${this.backendUrl}/chat/`, body, { headers: this.headers(rid) })
      .subscribe({
        next: res => { this.i('[HTTP /chat] OK', { rid, res }); this.consume(res); },
        error: err => { this.e('[HTTP /chat] ERR', { rid, err }); this.loading = false; this.stopTyping('⚠️ Napaka pri komunikaciji s strežnikom.'); }
      });
  }

  async sendStream(text: string, ridOuter?: string) {
    if (!this.isBrowser) return;
    const rid = ridOuter || this.rid('STRM');

    if (this.humanMode) { this.i('sendStream: humanMode → fallback send'); this.send(text); return; }

    this.i('sendStream()', { text, rid });

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
      this.messages.push({ role: 'assistant', text: '', _id: this.rid('MSG') });
      this.scrollToBottomSoon();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        this.messages[this.messages.length - 1].text = buffer;
        this.scrollToBottomSoon();
      }

      this._rememberHash(`assistant|${buffer}`);
      this.loading = false;
      this.i('sendStream complete', { bufferLen: buffer.length });
    } catch (err) {
      this.e('[HTTP /chat/stream] ERR', { rid, err });
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
    this.i('sendSingle()', { answer, rid });

    this.messages.push({ role: 'user', text: answer, _id: this.rid('MSG') });
    this._rememberHash(`user|${answer}`);
    this.pendingUserTexts.add(answer);
    setTimeout(() => this.pendingUserTexts.delete(answer), 5000);

    this.startTyping();
    this.loading = true;

    const body = { sid: this.sid, message: answer };

    this.http.post<ChatResponse>(`${this.backendUrl}/chat/`, body, { headers: this.headers(rid) })
      .subscribe({
        next: res => { this.i('[HTTP /chat] single OK', { rid, res }); this.singleSubmitting = false; this.consume(res); },
        error: err => { this.e('[HTTP /chat] single ERR', { rid, err }); this.singleSubmitting = false; this.loading = false; this.stopTyping('⚠️ Napaka pri pošiljanju odgovora.'); }
      });
  }

  sendSurvey(ans1: string, ans2: string) {
    if (!this.isBrowser) return;
    if (!ans1.trim() && !ans2.trim()) return;
    if (this.surveySubmitting) return;
    this.surveySubmitting = true;

    const rid = this.rid('SURVEY');
    this.i('sendSurvey()', { ans1, ans2, rid });

    const combo = `Q1: ${ans1} | Q2: ${ans2}`;
    this.messages.push({ role: 'user', text: combo, _id: this.rid('MSG') });
    this._rememberHash(`user|${combo}`);
    this.pendingUserTexts.add(combo);
    setTimeout(() => this.pendingUserTexts.delete(combo), 5000);

    this.startTyping('Sestavljam odgovore…');
    this.loading = true;

    const body = { sid: this.sid, industry: '', budget: '', experience: '', question1: ans1, question2: ans2 };

    this.http.post<ChatResponse>(`${this.backendUrl}/chat/survey`, body, { headers: this.headers(rid) })
      .subscribe({
        next: res => { this.i('[HTTP /chat/survey] OK', { rid, res }); this.surveySubmitting = false; this.consume(res); },
        error: err => { this.e('[HTTP /chat/survey] ERR', { rid, err }); this.surveySubmitting = false; this.loading = false; this.stopTyping('⚠️ Napaka pri pošiljanju ankete.'); }
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

  // === QUICK REPLY ===
  clickQuickReply(q: any) {
    this.i('clickQuickReply()', q);

    // 1) Optimistic/local render if we know the intended node
    if (q?.next) this.tryLocalUiForNext(q.next);
    else if (q?.title) this.tryHeuristics(q.title);

    // 2) Still send to backend so flow/analytics progress
    this.send(q.title);
  }

  // ---------- Core consumer ----------
  private consume(res: ChatResponse) {
    this.i('consume() ⮕ RAW', res);
    this.loading = false;

    if (res.ui == null && res.chatMode === 'open') {
      this.d('consume() → inject default single input for open mode');
      res.ui = { inputType: 'single' };
    } else if (res.ui && res.chatMode === 'open' && !res.ui.inputType && res.ui.type !== 'choices') {
      this.d('consume() → add inputType=single to provided ui');
      res.ui = { ...(res.ui || {}), inputType: 'single' };
    }

    if (!this.humanMode && res.reply !== undefined) {
      this.d('consume() → set reply text', res.reply);
      this._rememberHash(`assistant|${res.reply}`);
      this.stopTyping(res.reply);
    } else {
      this.d('consume() → stopTyping (no reply or humanMode)');
      this.stopTyping();
    }

    // Extract content blocks from the HTTP response (if they ever arrive)
    this.extractAndRenderFromAny(res, 'response');

    if (res.imageUrl) {
      this.i('consume() → legacy imageUrl detected', res.imageUrl);
      this.messages.push({ role: 'assistant', image: { src: res.imageUrl }, _id: this.rid('MSG') });
    }

    if (this.humanMode) {
      this.i('consume() → humanMode active, forcing open/single input');
      this.chatMode = 'open';
      this.ui = { inputType: 'single' };
      this.scrollToBottomSoon();
      return;
    }

    if (res.quickReplies) {
      this.d('consume() → set quickReplies', res.quickReplies);
      this.ui = { type: 'choices', buttons: res.quickReplies };
    } else if (res.ui && (res.ui.type === 'choices' || res.ui.inputType)) {
      if (res.ui.type === 'choices') {
        this.d('consume() → use ui choices', res.ui);
        this.ui = { type: 'choices', buttons: res.ui.buttons ?? res.ui.items ?? res.quickReplies ?? [] };
      } else {
        this.d('consume() → use ui input meta', res.ui);
        this.ui = res.ui;
      }
    } else {
      this.d('consume() → no ui provided; keeping previous or null');
      this.ui = this.ui && this.ui.inputType ? this.ui : null;
    }

    this.chatMode = res.chatMode;
    this.scrollToBottomSoon();
  }

  // ---------- Local “next” renderer (instant UX) ----------
  private tryLocalUiForNext(next: string) {
    this.i('[LOCAL NEXT]', next);

    if (next === 'listing_gallery') {
      const imgs = this.FALLBACK_ASSETS.gallery;
      if (imgs?.length) {
        this.i('Render (local) GALLERY', imgs);
        this.messages.push({ role: 'assistant', gallery: imgs.slice(0, 12), _id: this.rid('MSG') });
      } else {
        this.w('No fallback gallery images configured.');
      }
      return;
    }

    if (next === 'floorplan') {
      const src = this.FALLBACK_ASSETS.floorplan;
      if (src) {
        this.i('Render (local) FLOORPLAN', src);
        this.messages.push({ role: 'assistant', image: { src, label: 'Tloris (predogled)' }, _id: this.rid('MSG') });
      } else {
        this.w('No fallback floorplan configured.');
      }
      return;
    }

    if (next === 'map') {
      const addr = this.FALLBACK_ASSETS.map_address;
      if (addr) {
        this.i('Render (local) MAP', addr);
        this.messages.push({ role: 'assistant', map: { address: addr }, _id: this.rid('MSG') });
      } else {
        this.w('No fallback map address configured.');
      }
      return;
    }
  }

  // ---------- Extractor that understands many shapes (response + event) ----------
  private extractAndRenderFromAny(src: any, origin: 'response'|'event') {
    if (!src || typeof src !== 'object') {
      this.d('extractAndRenderFromAny(): no usable src', { origin, src });
      return;
    }
    this.i('extractAndRenderFromAny()', { origin, src });

    const maybeUi = src.ui || src.data?.ui;
    const maybeAction = src.uiAction || src.action || src.data?.action;
    const maybePayload = src.payload || src.data?.payload;

    if (maybeUi) {
      this.i('extractAndRenderFromAny(): trying canonical ui', { origin, ui: maybeUi });
      this.renderUiBlockIntoMessages(maybeUi);
    }

    if (maybeAction) {
      const shaped = { type: undefined, action: maybeAction, payload: maybePayload };
      this.i('extractAndRenderFromAny(): trying action+payload', shaped);
      this.renderUiBlockIntoMessages(shaped);
    }

    const flat = { images: src.images, image: src.image, address: src.address, label: src.label };
    if (flat.images || flat.image || flat.address) {
      this.i('extractAndRenderFromAny(): trying flat fields', { origin, flat });
      const guess =
        flat.images ? { type: 'gallery', images: flat.images } :
        flat.image  ? { type: 'image',   image: flat.image, label: flat.label } :
        flat.address? { type: 'map',     address: flat.address } :
        null;
      if (guess) this.renderUiBlockIntoMessages(guess);
    }
  }

  /** If a content block is detected, push a message for it */
  private renderUiBlockIntoMessages(ui: any) {
    if (!ui || typeof ui !== 'object') { this.d('renderUiBlockIntoMessages(): no usable ui', ui); return; }

    const type = ui.type as string | undefined;
    const action = ui.action as string | undefined;
    const payload = ui.payload || {};

    this.i('renderUiBlockIntoMessages() ⮕', { type, action, ui });

    if (type === 'gallery' && this.coerceImages(ui.images)?.length) {
      const images = this.coerceImages(ui.images)!.slice(0, 12);
      this.i('Render GALLERY (type)', images);
      this.messages.push({ role: 'assistant', gallery: images, _id: this.rid('MSG') });
      this.scrollToBottomSoon();
      return;
    }
    if (type === 'image' && typeof ui.image === 'string' && ui.image) {
      this.i('Render IMAGE (type)', ui.image);
      this.messages.push({ role: 'assistant', image: { src: ui.image, label: ui.label }, _id: this.rid('MSG') });
      this.scrollToBottomSoon();
      return;
    }
    if (type === 'map' && typeof ui.address === 'string' && ui.address) {
      this.i('Render MAP (type)', ui.address);
      this.messages.push({ role: 'assistant', map: { address: ui.address }, _id: this.rid('MSG') });
      this.scrollToBottomSoon();
      return;
    }

    if (action === 'show_gallery') {
      const images = this.coerceImages(payload.images);
      if (images?.length) {
        this.i('Render GALLERY (action)', images);
        this.messages.push({ role: 'assistant', gallery: images.slice(0, 12), _id: this.rid('MSG') });
      } else {
        this.w('show_gallery: no resolvable images', payload);
      }
      this.scrollToBottomSoon();
      return;
    }
    if (action === 'show_image') {
      const img = this.coerceImage(payload.image);
      if (img) {
        this.i('Render IMAGE (action)', img);
        this.messages.push({ role: 'assistant', image: { src: img, label: payload.label }, _id: this.rid('MSG') });
      } else {
        this.w('show_image: no resolvable image', payload);
      }
      this.scrollToBottomSoon();
      return;
    }
    if (action === 'show_map') {
      const addr = typeof payload.address === 'string' ? payload.address : ui.address;
      if (addr) {
        this.i('Render MAP (action)', addr);
        this.messages.push({ role: 'assistant', map: { address: addr }, _id: this.rid('MSG') });
      } else {
        this.w('show_map: no address', { ui, payload });
      }
      this.scrollToBottomSoon();
      return;
    }

    const looseImages = this.coerceImages(ui.images);
    if (looseImages?.length) {
      this.i('Render GALLERY (loose)', looseImages);
      this.messages.push({ role: 'assistant', gallery: looseImages.slice(0, 12), _id: this.rid('MSG') });
      this.scrollToBottomSoon();
      return;
    }
    const looseImg = this.coerceImage(ui.image);
    if (looseImg) {
      this.i('Render IMAGE (loose)', looseImg);
      this.messages.push({ role: 'assistant', image: { src: looseImg, label: ui.label }, _id: this.rid('MSG') });
      this.scrollToBottomSoon();
      return;
    }

    this.d('renderUiBlockIntoMessages(): nothing to render from ui', ui);
  }

  private coerceImages(val: unknown): string[] | null {
    if (!val) { this.d('coerceImages: val empty', val); return null; }
    if (Array.isArray(val)) {
      const arr = val.filter((x): x is string => typeof x === 'string' && !!x);
      this.d('coerceImages: array →', arr);
      return arr;
    }
    if (typeof val === 'string') {
      const s = val.trim();
      if (!s) { this.d('coerceImages: empty string'); return null; }
      if (s.startsWith('[')) {
        try {
          const parsed = JSON.parse(s);
          if (Array.isArray(parsed)) {
            const arr = parsed.filter((x: any) => typeof x === 'string' && !!x);
            this.d('coerceImages: JSON string →', arr);
            return arr;
          }
        } catch (err) { this.w('coerceImages: JSON parse failed', { s, err }); }
      }
      if (s.startsWith('{{')) {
        this.w('coerceImages: unresolved template string (needs backend expansion)', s);
        return null;
      }
      this.d('coerceImages: single path string →', s);
      return [s];
    }
    this.d('coerceImages: unsupported type', typeof val, val);
    return null;
  }

  private coerceImage(val: unknown): string | null {
    const arr = this.coerceImages(val);
    const out = arr && arr.length ? arr[0] : null;
    this.d('coerceImage →', out);
    return out;
  }

  mapSrc(address: string): SafeResourceUrl {
    const q = encodeURIComponent(address);
    const url = `https://www.google.com/maps?q=${q}&output=embed`;
    this.d('mapSrc()', { address, url });
    return this.sanitizer.bypassSecurityTrustResourceUrl(url);
  }

  public onImgLoad(src: string) { this.i('IMG load ✅', src); }
  public onImgError(evt: Event, src: string) { this.e('IMG error ❌', { src, evt }); }

  // ---------- Heuristic fallback when server forgets the UI block ----------
  private tryHeuristics(text: string) {
    const t = text.toLowerCase();

    if (t.includes('galerija nepremičnine')) {
      const imgs = this.FALLBACK_ASSETS.gallery;
      this.i('[HEUR] Gallery fallback', imgs);
      if (imgs?.length) this.messages.push({ role: 'assistant', gallery: imgs.slice(0, 12), _id: this.rid('MSG') });
      return;
    }

    if (t.includes('tloris')) {
      const src = this.FALLBACK_ASSETS.floorplan;
      this.i('[HEUR] Floorplan fallback', src);
      if (src) this.messages.push({ role: 'assistant', image: { src, label: 'Tloris (predogled)' }, _id: this.rid('MSG') });
      return;
    }

    if (t.includes('okvirna lokacija')) {
      const addr = this.FALLBACK_ASSETS.map_address;
      this.i('[HEUR] Map fallback', addr);
      if (addr) this.messages.push({ role: 'assistant', map: { address: addr }, _id: this.rid('MSG') });
      return;
    }
  }

  // ===== Typing helpers =====
  private startTyping(label?: string) {
    if (!this.isTypingActive()) {
      this.messages.push({ role: 'assistant', typing: true, _id: this.rid('MSG') });
      this.scrollToBottomSoon();
    }
    this.typingLabel = label ?? this.typingLabel ?? 'Razmišljam…';
  }

  private stopTyping(replaceWith?: string) {
    const last = this.messages[this.messages.length - 1];
    if (last && (last as any).typing) {
      this.messages.pop();
      if (replaceWith !== undefined) {
        this.messages.push({ role: 'assistant', text: replaceWith, _id: this.rid('MSG') });
      }
    }
    this.typingLabel = null;
    this.scrollToBottomSoon();
  }

  private isTypingActive(): boolean {
    const last = this.messages[this.messages.length - 1];
    return !!(last && (last as any).typing);
  }

  // ---------- Misc ----------
  private rid(prefix: string) { return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2,8)}`; }
  private headers(rid: string) { return new HttpHeaders({ 'X-Req-Id': rid, 'X-Sid': this.sid, 'Content-Type': 'application/json' }); }
  private _rememberHash(h: string) { this.recentHashes.push(h); if (this.recentHashes.length > 100) this.recentHashes.shift(); }
  private _removeTrailingTypingIfNeeded() {
    const last = this.messages[this.messages.length - 1];
    const prev = this.messages[this.messages.length - 2];
    if (last && prev && prev.typing) this.messages.splice(this.messages.length - 2, 1);
  }
  private scrollToBottomSoon() {
    if (!this.isBrowser) return;
    this.zone.runOutsideAngular(() => {
      setTimeout(() => {
        const el = this.messagesRef?.nativeElement;
        if (!el) return;
        el.scrollTop = el.scrollHeight;
        this.d('scrollToBottomSoon() → scrolled', { scrollTop: el.scrollTop, scrollHeight: el.scrollHeight });
      }, 0);
    });
  }
}
