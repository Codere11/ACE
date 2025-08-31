import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { BehaviorSubject, map, tap } from 'rxjs';
import { User } from '../../core/models/user';

type LoginRes = { token: string; user: { username:string; role:'admin'|'manager'; tenant_slug?:string|null } };

@Injectable({ providedIn: 'root' })
export class AuthService {
  private currentUserSub = new BehaviorSubject<User|null>(this.load());
  currentUser$ = this.currentUserSub.asObservable();

  constructor(private http: HttpClient) {}

  private load(): User|null {
    const raw = localStorage.getItem('ace_user');
    return raw ? JSON.parse(raw) as User : null;
  }
  private save(u: User|null) {
    if (u) localStorage.setItem('ace_user', JSON.stringify(u));
    else localStorage.removeItem('ace_user');
  }

  login(username: string, password: string) {
    return this.http.post<LoginRes>('/api/auth/login', { username, password })
      .pipe(
        map(res => ({ ...res.user, token: res.token } as User)),
        tap(u => { this.save(u); this.currentUserSub.next(u); })
      );
  }

  logout() { this.save(null); this.currentUserSub.next(null); }

  me() {
    const u = this.currentUserSub.value;
    if (!u) { this.logout(); return; }
    const headers = new HttpHeaders({ Authorization: `Bearer ${u.token}` });
    return this.http.get<{user:{username:string;role:'admin'|'manager';tenant_slug?:string|null}}>('/api/auth/me', { headers });
  }

  get token() { return this.currentUserSub.value?.token ?? null; }
  get user() { return this.currentUserSub.value; }
}
