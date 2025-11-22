#!/bin/bash
# Quick Start Script for Manager Dashboard Frontend
# This creates all essential files for the Angular app

set -e

echo "🚀 Setting up Manager Dashboard Frontend..."
echo ""

APP_DIR="/home/maksich/Documents/ACE-RealEstate/frontend/manager-dashboard/src/app"

# Create directories
echo "Creating directories..."
mkdir -p "$APP_DIR/models"
mkdir -p "$APP_DIR/services"
mkdir -p "$APP_DIR/guards"
mkdir -p "$APP_DIR/interceptors"
mkdir -p "$APP_DIR/auth/login"
mkdir -p "$APP_DIR/users"
mkdir -p "$APP_DIR/surveys"
mkdir -p "$APP_DIR/responses"

echo "✅ Directories created"
echo ""

echo "📋 Creating model files..."

# user.model.ts
cat > "$APP_DIR/models/user.model.ts" << 'EOF'
export interface User {
  id: number;
  username: string;
  email: string;
  role: 'org_admin' | 'org_user';
  organization_id: number;
  organization_slug?: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  user: User;
}

export interface UserCreate {
  username: string;
  email: string;
  password: string;
  role: 'org_admin' | 'org_user';
  organization_id: number;
  is_active: boolean;
}

export interface UserUpdate {
  username?: string;
  email?: string;
  password?: string;
  role?: 'org_admin' | 'org_user';
  is_active?: boolean;
}
EOF

# survey.model.ts
cat > "$APP_DIR/models/survey.model.ts" << 'EOF'
export interface Survey {
  id: number;
  organization_id: number;
  name: string;
  slug: string;
  survey_type: 'regular' | 'ab_test';
  status: 'draft' | 'live' | 'archived';
  flow_json?: any;
  variant_a_flow?: any;
  variant_b_flow?: any;
  created_at: string;
  updated_at: string;
  published_at?: string;
}

export interface SurveyCreate {
  name: string;
  slug: string;
  survey_type: 'regular' | 'ab_test';
  status: 'draft' | 'live' | 'archived';
  organization_id: number;
  flow_json?: any;
  variant_a_flow?: any;
  variant_b_flow?: any;
}

export interface SurveyUpdate {
  name?: string;
  slug?: string;
  survey_type?: 'regular' | 'ab_test';
  status?: 'draft' | 'live' | 'archived';
  flow_json?: any;
  variant_a_flow?: any;
  variant_b_flow?: any;
}

export interface SurveyStats {
  survey_id: number;
  total_responses: number;
  completed_responses: number;
  avg_score: number;
  avg_completion_time_minutes?: number;
  variant_a_responses?: number;
  variant_b_responses?: number;
  variant_a_avg_score?: number;
  variant_b_avg_score?: number;
}
EOF

# response.model.ts
cat > "$APP_DIR/models/response.model.ts" << 'EOF'
export interface SurveyResponse {
  id: number;
  survey_id: number;
  organization_id: number;
  sid: string;
  variant?: 'a' | 'b';
  name: string;
  email: string;
  phone: string;
  survey_answers?: any;
  score: number;
  interest: 'Low' | 'Medium' | 'High';
  survey_started_at: string;
  survey_completed_at?: string;
  survey_progress: number;
  notes: string;
  created_at: string;
  updated_at: string;
}
EOF

echo "✅ Models created"
echo ""

echo "🔒 Creating auth service..."

# auth.service.ts
cat > "$APP_DIR/services/auth.service.ts" << 'EOF'
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { User, LoginRequest, LoginResponse } from '../models/user.model';
import { Router } from '@angular/router';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = 'http://localhost:8000/api/auth';
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(
    private http: HttpClient,
    private router: Router
  ) {
    // Load user from localStorage on init
    const token = this.getToken();
    if (token) {
      this.loadCurrentUser();
    }
  }

  login(username: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>(`${this.apiUrl}/login`, { username, password })
      .pipe(
        tap(response => {
          localStorage.setItem('token', response.token);
          localStorage.setItem('user', JSON.stringify(response.user));
          this.currentUserSubject.next(response.user);
        })
      );
  }

  logout(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    this.currentUserSubject.next(null);
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return localStorage.getItem('token');
  }

  getCurrentUser(): User | null {
    const userJson = localStorage.getItem('user');
    return userJson ? JSON.parse(userJson) : null;
  }

  loadCurrentUser(): void {
    const user = this.getCurrentUser();
    if (user) {
      this.currentUserSubject.next(user);
    }
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }

  isAdmin(): boolean {
    const user = this.getCurrentUser();
    return user?.role === 'org_admin';
  }
}
EOF

echo "✅ Auth service created"
echo ""

echo "🛡️ Creating interceptor and guards..."

# auth.interceptor.ts
cat > "$APP_DIR/interceptors/auth.interceptor.ts" << 'EOF'
import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth.service';
import { catchError, throwError } from 'rxjs';
import { Router } from '@angular/router';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const router = inject(Router);
  const token = authService.getToken();

  if (token) {
    req = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
  }

  return next(req).pipe(
    catchError((error) => {
      if (error.status === 401) {
        authService.logout();
        router.navigate(['/login']);
      }
      return throwError(() => error);
    })
  );
};
EOF

# auth.guard.ts
cat > "$APP_DIR/guards/auth.guard.ts" << 'EOF'
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const authGuard = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated()) {
    return true;
  }

  router.navigate(['/login']);
  return false;
};

export const adminGuard = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated() && authService.isAdmin()) {
    return true;
  }

  router.navigate(['/']);
  return false;
};
EOF

echo "✅ Interceptor and guards created"
echo ""

echo "📄 Creating login component..."

# login.component.ts
cat > "$APP_DIR/auth/login/login.component.ts" << 'EOF'
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="login-container">
      <div class="login-card">
        <h1>ACE Manager Dashboard</h1>
        <form (ngSubmit)="login()" #loginForm="ngForm">
          <div class="form-group">
            <label for="username">Username</label>
            <input 
              type="text" 
              id="username" 
              name="username"
              [(ngModel)]="credentials.username" 
              required
              class="form-control"
              placeholder="Enter username"
            />
          </div>
          <div class="form-group">
            <label for="password">Password</label>
            <input 
              type="password" 
              id="password" 
              name="password"
              [(ngModel)]="credentials.password" 
              required
              class="form-control"
              placeholder="Enter password"
            />
          </div>
          
          @if (error) {
            <div class="error-message">{{ error }}</div>
          }
          
          <button 
            type="submit" 
            class="btn-primary"
            [disabled]="loading || !loginForm.valid"
          >
            @if (loading) {
              <span>Logging in...</span>
            } @else {
              <span>Login</span>
            }
          </button>
        </form>
        
        <div class="test-credentials">
          <p><strong>Test Credentials:</strong></p>
          <p>Admin: admin / test123</p>
          <p>User: user1 / test123</p>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .login-container {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .login-card {
      background: white;
      border-radius: 12px;
      padding: 40px;
      box-shadow: 0 10px 40px rgba(0,0,0,0.2);
      width: 100%;
      max-width: 400px;
    }
    
    h1 {
      text-align: center;
      color: #333;
      margin-bottom: 30px;
      font-size: 24px;
    }
    
    .form-group {
      margin-bottom: 20px;
    }
    
    label {
      display: block;
      margin-bottom: 8px;
      color: #555;
      font-weight: 500;
    }
    
    .form-control {
      width: 100%;
      padding: 12px;
      border: 1px solid #ddd;
      border-radius: 6px;
      font-size: 14px;
      box-sizing: border-box;
    }
    
    .form-control:focus {
      outline: none;
      border-color: #667eea;
    }
    
    .btn-primary {
      width: 100%;
      padding: 12px;
      background: #667eea;
      color: white;
      border: none;
      border-radius: 6px;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.3s;
    }
    
    .btn-primary:hover:not(:disabled) {
      background: #5568d3;
    }
    
    .btn-primary:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    
    .error-message {
      background: #fee;
      color: #c33;
      padding: 10px;
      border-radius: 6px;
      margin-bottom: 15px;
      text-align: center;
    }
    
    .test-credentials {
      margin-top: 30px;
      padding-top: 20px;
      border-top: 1px solid #eee;
      font-size: 12px;
      color: #666;
      text-align: center;
    }
    
    .test-credentials p {
      margin: 5px 0;
    }
  `]
})
export class LoginComponent {
  credentials = {
    username: '',
    password: ''
  };
  
  loading = false;
  error = '';

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  login(): void {
    this.loading = true;
    this.error = '';

    this.authService.login(this.credentials.username, this.credentials.password)
      .subscribe({
        next: () => {
          this.router.navigate(['/']);
        },
        error: (err) => {
          this.loading = false;
          this.error = err.error?.detail || 'Login failed. Please check your credentials.';
        }
      });
  }
}
EOF

echo "✅ Login component created"
echo ""

echo "📋 Creating placeholder components..."

# Users service placeholder
cat > "$APP_DIR/services/users.service.ts" << 'EOF'
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
EOF

# Surveys service placeholder
cat > "$APP_DIR/services/surveys.service.ts" << 'EOF'
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Survey, SurveyCreate, SurveyUpdate, SurveyStats } from '../models/survey.model';
import { SurveyResponse } from '../models/response.model';
import { AuthService } from './auth.service';

@Injectable({
  providedIn: 'root'
})
export class SurveysService {
  private apiUrl = 'http://localhost:8000/api/organizations';

  constructor(
    private http: HttpClient,
    private authService: AuthService
  ) {}

  private getOrgId(): number {
    return this.authService.getCurrentUser()?.organization_id || 1;
  }

  listSurveys(status?: string): Observable<Survey[]> {
    const params = status ? { status } : {};
    return this.http.get<Survey[]>(`${this.apiUrl}/${this.getOrgId()}/surveys`, { params });
  }

  getSurvey(surveyId: number): Observable<Survey> {
    return this.http.get<Survey>(`${this.apiUrl}/${this.getOrgId()}/surveys/${surveyId}`);
  }

  createSurvey(survey: SurveyCreate): Observable<Survey> {
    return this.http.post<Survey>(`${this.apiUrl}/${this.getOrgId()}/surveys`, survey);
  }

  updateSurvey(surveyId: number, survey: SurveyUpdate): Observable<Survey> {
    return this.http.put<Survey>(`${this.apiUrl}/${this.getOrgId()}/surveys/${surveyId}`, survey);
  }

  publishSurvey(surveyId: number): Observable<Survey> {
    return this.http.post<Survey>(`${this.apiUrl}/${this.getOrgId()}/surveys/${surveyId}/publish`, {});
  }

  archiveSurvey(surveyId: number): Observable<Survey> {
    return this.http.post<Survey>(`${this.apiUrl}/${this.getOrgId()}/surveys/${surveyId}/archive`, {});
  }

  deleteSurvey(surveyId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${this.getOrgId()}/surveys/${surveyId}`);
  }

  getSurveyStats(surveyId: number): Observable<SurveyStats> {
    return this.http.get<SurveyStats>(`${this.apiUrl}/${this.getOrgId()}/surveys/${surveyId}/stats`);
  }

  getSurveyResponses(surveyId: number): Observable<SurveyResponse[]> {
    return this.http.get<SurveyResponse[]>(`${this.apiUrl}/${this.getOrgId()}/surveys/${surveyId}/responses`);
  }
}
EOF

echo "✅ Services created"
echo ""

echo "========================================="
echo "✅ Frontend setup complete!"
echo "========================================="
echo ""
echo "📝 Next steps:"
echo "1. Update app.config.ts to include interceptor"
echo "2. Update app.routes.ts with new routes"
echo "3. Update app.component for navigation"
echo "4. Create UI components for users/surveys/responses"
echo ""
echo "Run: cd /home/maksich/Documents/ACE-RealEstate/frontend/manager-dashboard && ng serve"
EOF

chmod +x /home/maksich/Documents/ACE-RealEstate/frontend/manager-dashboard/setup-frontend.sh

echo "✅ Frontend setup script created!"
echo ""
echo "Run it with:"
echo "bash /home/maksich/Documents/ACE-RealEstate/frontend/manager-dashboard/setup-frontend.sh"
