import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, from, map, switchMap, tap } from 'rxjs';
import { environment } from '../../../environments/environment';

export type User = {
  username: string;
  role: 'admin' | 'manager';
  tenant_slug?: string | null;
  token: string;
};

type LoginRes = {
  token: string;
  user: { username: string; role: 'admin' | 'manager'; tenant_slug?: string | null };
};

@Injectable({ providedIn: 'root' })
export class AuthService {
  private currentUserSub = new BehaviorSubject<User | null>(this.load());
  currentUser$ = this.currentUserSub.asObservable();

  // ----------------- storage helpers -----------------
  private load(): User | null {
    const raw = localStorage.getItem('ace_user');
    return raw ? (JSON.parse(raw) as User) : null;
  }
  private save(u: User | null) {
    if (u) localStorage.setItem('ace_user', JSON.stringify(u));
    else localStorage.removeItem('ace_user');
  }

  // ----------------- API helpers (fetch) -----------------
  private fetchJson<T>(url: string, init?: RequestInit): Observable<T> {
    return from(fetch(url, init)).pipe(
      switchMap(async (res) => {
        let data: any = null;
        try {
          data = await res.json();
        } catch {
          data = null;
        }
        if (!res.ok) {
          const err: any = {
            status: res.status,
            statusText: res.statusText,
            error: data ?? { detail: 'Request failed' },
            url,
          };
          throw err;
        }
        return data as T;
      })
    );
  }

  // ----------------- public API -----------------
  login(username: string, password: string): Observable<User> {
    const url = `${environment.apiBase}/api/auth/login`;
    return this.fetchJson<LoginRes>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }).pipe(
      tap((res) => console.log('[Auth] login OK', res)),
      map((res) => ({ ...res.user, token: res.token } as User)),
      tap((u) => {
        this.save(u);
        this.currentUserSub.next(u);
      })
    );
  }

  logout() {
    this.save(null);
    this.currentUserSub.next(null);
  }

  me(): Observable<{ user: { username: string; role: 'admin' | 'manager'; tenant_slug?: string | null } }> {
    const u = this.currentUserSub.value;
    if (!u) {
      this.logout();
      // Return an observable that completes immediately when no user
      return from(Promise.resolve({ user: { username: '', role: 'manager' as const } }));
    }
    const url = `${environment.apiBase}/api/auth/me`;
    return this.fetchJson(url, {
      method: 'GET',
      headers: { Authorization: `Bearer ${u.token}` },
    });
  }

  get token() {
    return this.currentUserSub.value?.token ?? null;
  }
  get user() {
    return this.currentUserSub.value;
  }
}
