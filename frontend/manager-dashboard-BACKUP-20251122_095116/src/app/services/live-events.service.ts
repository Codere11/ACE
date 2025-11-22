import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, Subscription, timer } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { HttpClient } from '@angular/common/http';

export type ChatEvent = { type: string; sid: string; ts: number; payload: any; _seq?: number };

@Injectable({ providedIn: 'root' })
export class LiveEventsService implements OnDestroy {
  private base = 'http://localhost:8000/chat-events';
  private sub?: Subscription;
  private nextSeq = 0;
  private topic = '*';

  /** Stream of all events (message.created, lead.touched, lead.notes, lead.ai_summary, ...) */
  readonly events$ = new BehaviorSubject<ChatEvent | null>(null);

  constructor(private http: HttpClient) {}

  /** Start listening to cross-SID lead updates (and messages). */
  startAll() {
    this.stop();
    this.topic = '*';
    this.nextSeq = 0;

    this.sub = timer(0, 200).pipe(
      switchMap(() =>
        this.http.get<{ ok: boolean; events: ChatEvent[]; next: number }>(
          `${this.base}/poll?sid=${encodeURIComponent(this.topic)}&since=${this.nextSeq}&timeout=20`
        )
      )
    ).subscribe({
      next: (res) => {
        if (!res?.ok) return;
        for (const e of res.events) {
          this.events$.next(e);
          if (e._seq && e._seq > this.nextSeq) this.nextSeq = e._seq;
        }
      },
      error: () => {
        // transient errors are fine; next tick retries
      }
    });
  }

  /** Stop polling. */
  stop() {
    this.sub?.unsubscribe();
    this.sub = undefined;
  }

  ngOnDestroy() { this.stop(); }
}
