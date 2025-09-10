import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, Subscription, timer } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { HttpClient } from '@angular/common/http';

export type ChatEvent = {
  type: string;            // "message.created", ...
  sid: string;
  ts: number;
  payload: { role?: string; text?: string; timestamp?: number } | any;
  _seq?: number;
};

@Injectable({ providedIn: 'root' })
export class LiveEventsService implements OnDestroy {
  private base = 'http://localhost:8000/chat-events';
  private sub?: Subscription;
  private nextSeq = 0;
  private topic = '';

  /** Streams events for the active SID */
  readonly events$ = new BehaviorSubject<ChatEvent | null>(null);

  constructor(private http: HttpClient) {
    console.debug('[LiveEvents] init', { base: this.base });
  }

  start(sid: string) {
    this.stop();
    this.topic = sid;
    this.nextSeq = 0;

    console.debug('[LiveEvents] start()', { sid });

    this.sub = timer(0, 200).pipe(
      switchMap(() =>
        this.http.get<{ ok: boolean; events: ChatEvent[]; next: number }>(
          `${this.base}/poll?sid=${encodeURIComponent(this.topic)}&since=${this.nextSeq}&timeout=20`
        )
      )
    ).subscribe({
      next: res => {
        if (!res?.ok) {
          console.warn('[LiveEvents] poll not ok', res);
          return;
        }
        for (const e of res.events) {
          console.debug('[LiveEvents] event', e);
          this.events$.next(e);
          if (e._seq && e._seq > this.nextSeq) this.nextSeq = e._seq;
        }
      },
      error: err => {
        console.warn('[LiveEvents] poll error, will retry', err);
      }
    });
  }

  stop() {
    console.debug('[LiveEvents] stop()');
    this.sub?.unsubscribe();
    this.sub = undefined;
  }

  ngOnDestroy() { this.stop(); }
}
