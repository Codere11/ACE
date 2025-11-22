import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { User, UserCreate, UserUpdate } from '../models/user.model';
import { AuthService } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class UsersService {
  private apiUrl = 'http://localhost:8000/api/organizations';

  constructor(
    private http: HttpClient,
    private authService: AuthService
  ) {}

  private getOrgId(): number {
    return this.authService.getCurrentUser()?.organization_id || 1;
  }

  listUsers(): Observable<User[]> {
    return this.http.get<User[]>(`${this.apiUrl}/${this.getOrgId()}/users`);
  }

  createUser(user: UserCreate): Observable<User> {
    return this.http.post<User>(`${this.apiUrl}/${this.getOrgId()}/users`, user);
  }

  updateUser(userId: number, user: UserUpdate): Observable<User> {
    return this.http.put<User>(`${this.apiUrl}/${this.getOrgId()}/users/${userId}`, user);
  }

  deleteUser(userId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${this.getOrgId()}/users/${userId}`);
  }
}
