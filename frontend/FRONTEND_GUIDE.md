# ACE Manager Dashboard - Frontend Implementation Guide

## ✅ What's Already Done

### 1. Dependencies Installed
- Angular Material 19
- ng2-charts (Chart.js wrapper)
- All required Angular dependencies

### 2. Core Files Created
- **Models**: user.model.ts, survey.model.ts, response.model.ts
- **Services**: auth.service.ts, users.service.ts, surveys.service.ts
- **Guards**: auth.guard.ts, adminGuard
- **Interceptor**: auth.interceptor.ts (JWT auth)
- **Login Component**: Fully styled login page

### 3. Directory Structure
```
src/app/
├── models/           ✅ Created
├── services/         ✅ Created
├── guards/           ✅ Created
├── interceptors/     ✅ Created
├── auth/login/       ✅ Created
├── users/            ✅ Empty (needs components)
├── surveys/          ✅ Empty (needs components)
└── responses/        ✅ Empty (needs components)
```

---

## 🔧 Configuration Updates Needed

### 1. Update `src/app/app.config.ts`

Add HTTP interceptor and providers:

```typescript
import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';

import { routes } from './app.routes';
import { authInterceptor } from './interceptors/auth.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideHttpClient(
      withInterceptors([authInterceptor])
    ),
    provideAnimationsAsync()
  ]
};
```

### 2. Update `src/app/app.routes.ts`

Replace with:

```typescript
import { Routes } from '@angular/router';
import { LoginComponent } from './auth/login/login.component';
import { authGuard, adminGuard } from './guards/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    component: LoginComponent
  },
  {
    path: '',
    canActivate: [authGuard],
    children: [
      {
        path: '',
        redirectTo: 'dashboard',
        pathMatch: 'full'
      },
      {
        path: 'dashboard',
        loadComponent: () => import('./dashboard/dashboard.component').then(m => m.DashboardComponent)
      },
      {
        path: 'users',
        canActivate: [adminGuard],
        loadComponent: () => import('./users/user-list.component').then(m => m.UserListComponent)
      },
      {
        path: 'surveys',
        loadComponent: () => import('./surveys/survey-list.component').then(m => m.SurveyListComponent)
      },
      {
        path: 'responses',
        loadComponent: () => import('./responses/response-list.component').then(m => m.ResponseListComponent)
      }
    ]
  }
];
```

### 3. Update `src/app/app.component.ts`

Replace with navigation layout:

```typescript
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from './services/auth.service';
import { User } from './models/user.model';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    @if (currentUser) {
      <div class="app-container">
        <!-- Sidebar -->
        <nav class="sidebar">
          <div class="sidebar-header">
            <h2>ACE Manager</h2>
          </div>
          
          <ul class="nav-menu">
            <li>
              <a routerLink="/dashboard" routerLinkActive="active">
                📊 Dashboard
              </a>
            </li>
            <li>
              <a routerLink="/surveys" routerLinkActive="active">
                📋 Surveys
              </a>
            </li>
            <li>
              <a routerLink="/responses" routerLinkActive="active">
                💬 Responses
              </a>
            </li>
            @if (isAdmin) {
              <li>
                <a routerLink="/users" routerLinkActive="active">
                  👥 Users
                </a>
              </li>
            }
          </ul>
          
          <div class="user-menu">
            <div class="user-info">
              <strong>{{currentUser.username}}</strong>
              <span class="role-badge">{{currentUser.role}}</span>
            </div>
            <button (click)="logout()" class="logout-btn">
              🚪 Logout
            </button>
          </div>
        </nav>
        
        <!-- Main Content -->
        <main class="main-content">
          <router-outlet></router-outlet>
        </main>
      </div>
    } @else {
      <router-outlet></router-outlet>
    }
  `,
  styles: [`
    .app-container {
      display: flex;
      height: 100vh;
    }
    
    .sidebar {
      width: 250px;
      background: #2c3e50;
      color: white;
      display: flex;
      flex-direction: column;
    }
    
    .sidebar-header {
      padding: 20px;
      border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    
    .sidebar-header h2 {
      margin: 0;
      font-size: 20px;
    }
    
    .nav-menu {
      flex: 1;
      list-style: none;
      padding: 0;
      margin: 20px 0;
    }
    
    .nav-menu li a {
      display: block;
      padding: 12px 20px;
      color: white;
      text-decoration: none;
      transition: background 0.3s;
    }
    
    .nav-menu li a:hover {
      background: rgba(255,255,255,0.1);
    }
    
    .nav-menu li a.active {
      background: rgba(255,255,255,0.2);
      border-left: 3px solid #3498db;
    }
    
    .user-menu {
      padding: 20px;
      border-top: 1px solid rgba(255,255,255,0.1);
    }
    
    .user-info {
      margin-bottom: 10px;
    }
    
    .role-badge {
      display: block;
      font-size: 12px;
      color: #95a5a6;
    }
    
    .logout-btn {
      width: 100%;
      padding: 10px;
      background: #e74c3c;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
    }
    
    .logout-btn:hover {
      background: #c0392b;
    }
    
    .main-content {
      flex: 1;
      overflow-y: auto;
      background: #ecf0f1;
      padding: 20px;
    }
  `]
})
export class AppComponent implements OnInit {
  currentUser: User | null = null;
  isAdmin = false;

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit() {
    this.authService.currentUser$.subscribe(user => {
      this.currentUser = user;
      this.isAdmin = this.authService.isAdmin();
    });
  }

  logout() {
    this.authService.logout();
  }
}
```

---

## 🚀 Quick Start Commands

### Start Backend (in one terminal)
```bash
cd /home/maksich/Documents/ACE-RealEstate
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Start Frontend (in another terminal)
```bash
cd /home/maksich/Documents/ACE-RealEstate/frontend/manager-dashboard
ng serve --port 4400
```

**Access:**
- Frontend: http://localhost:4400
- Login: admin / test123

---

## 📋 Creating Remaining Components

### Dashboard Component (Simple Version)

Create `src/app/dashboard/dashboard.component.ts`:

```typescript
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../services/auth.service';
import { User } from '../models/user.model';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="dashboard">
      <h1>Welcome, {{user?.username}}!</h1>
      <p>Organization: {{user?.organization_slug}}</p>
      <p>Role: <strong>{{user?.role}}</strong></p>
      
      <div class="quick-links">
        <a href="#/surveys" class="card">
          <h3>📋 Surveys</h3>
          <p>Manage your surveys</p>
        </a>
        <a href="#/responses" class="card">
          <h3>💬 Responses</h3>
          <p>View survey responses</p>
        </a>
        @if (isAdmin) {
          <a href="#/users" class="card">
            <h3>👥 Users</h3>
            <p>Manage team members</p>
          </a>
        }
      </div>
    </div>
  `,
  styles: [`
    .dashboard {
      max-width: 1200px;
      margin: 0 auto;
    }
    
    h1 {
      font-size: 32px;
      color: #2c3e50;
      margin-bottom: 10px;
    }
    
    .quick-links {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 20px;
      margin-top: 40px;
    }
    
    .card {
      background: white;
      padding: 30px;
      border-radius: 8px;
      text-decoration: none;
      color: inherit;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
      transition: transform 0.3s, box-shadow 0.3s;
    }
    
    .card:hover {
      transform: translateY(-5px);
      box-shadow: 0 5px 20px rgba(0,0,0,0.15);
    }
    
    .card h3 {
      margin: 0 0 10px 0;
      font-size: 20px;
    }
    
    .card p {
      margin: 0;
      color: #7f8c8d;
    }
  `]
})
export class DashboardComponent implements OnInit {
  user: User | null = null;
  isAdmin = false;

  constructor(private authService: AuthService) {}

  ngOnInit() {
    this.user = this.authService.getCurrentUser();
    this.isAdmin = this.authService.isAdmin();
  }
}
```

### User List Component

Create `src/app/users/user-list.component.ts`:

```typescript
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UsersService } from '../services/users.service';
import { User } from '../models/user.model';

@Component({
  selector: 'app-user-list',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="user-list">
      <h1>Team Members</h1>
      
      @if (loading) {
        <p>Loading users...</p>
      } @else {
        <table>
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (user of users; track user.id) {
              <tr>
                <td>{{user.username}}</td>
                <td>{{user.email}}</td>
                <td>
                  <span class="badge" [class.admin]="user.role === 'org_admin'">
                    {{user.role}}
                  </span>
                </td>
                <td>
                  <span [class.active]="user.is_active" [class.inactive]="!user.is_active">
                    {{user.is_active ? 'Active' : 'Inactive'}}
                  </span>
                </td>
                <td>
                  <button>Edit</button>
                  <button>Delete</button>
                </td>
              </tr>
            }
          </tbody>
        </table>
      }
    </div>
  `,
  styles: [`
    .user-list {
      background: white;
      padding: 30px;
      border-radius: 8px;
    }
    
    table {
      width: 100%;
      border-collapse: collapse;
    }
    
    th, td {
      padding: 12px;
      text-align: left;
      border-bottom: 1px solid #ddd;
    }
    
    .badge {
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
      background: #3498db;
      color: white;
    }
    
    .badge.admin {
      background: #e74c3c;
    }
    
    .active {
      color: green;
    }
    
    .inactive {
      color: red;
    }
  `]
})
export class UserListComponent implements OnInit {
  users: User[] = [];
  loading = true;

  constructor(private usersService: UsersService) {}

  ngOnInit() {
    this.loadUsers();
  }

  loadUsers() {
    this.usersService.listUsers().subscribe({
      next: (users) => {
        this.users = users;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading users:', err);
        this.loading = false;
      }
    });
  }
}
```

### Survey List Component

Create `src/app/surveys/survey-list.component.ts`:

```typescript
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SurveysService } from '../services/surveys.service';
import { Survey } from '../models/survey.model';

@Component({
  selector: 'app-survey-list',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="survey-list">
      <div class="header">
        <h1>Surveys</h1>
        <button class="btn-primary">+ Create Survey</button>
      </div>
      
      @if (loading) {
        <p>Loading surveys...</p>
      } @else if (surveys.length === 0) {
        <p>No surveys yet. Create your first survey!</p>
      } @else {
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (survey of surveys; track survey.id) {
              <tr>
                <td>{{survey.name}}</td>
                <td>{{survey.survey_type}}</td>
                <td>
                  <span class="status-badge" [class]="survey.status">
                    {{survey.status}}
                  </span>
                </td>
                <td>{{survey.created_at | date}}</td>
                <td>
                  <button (click)="viewStats(survey.id)">Stats</button>
                  @if (survey.status === 'draft') {
                    <button (click)="publish(survey.id)">Publish</button>
                  }
                  @if (survey.status === 'live') {
                    <button (click)="archive(survey.id)">Archive</button>
                  }
                </td>
              </tr>
            }
          </tbody>
        </table>
      }
    </div>
  `,
  styles: [`
    .survey-list {
      background: white;
      padding: 30px;
      border-radius: 8px;
    }
    
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }
    
    .btn-primary {
      padding: 10px 20px;
      background: #3498db;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
    }
    
    table {
      width: 100%;
      border-collapse: collapse;
    }
    
    th, td {
      padding: 12px;
      text-align: left;
      border-bottom: 1px solid #ddd;
    }
    
    .status-badge {
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
    }
    
    .status-badge.draft {
      background: #f39c12;
      color: white;
    }
    
    .status-badge.live {
      background: #27ae60;
      color: white;
    }
    
    .status-badge.archived {
      background: #95a5a6;
      color: white;
    }
  `]
})
export class SurveyListComponent implements OnInit {
  surveys: Survey[] = [];
  loading = true;

  constructor(private surveysService: SurveysService) {}

  ngOnInit() {
    this.loadSurveys();
  }

  loadSurveys() {
    this.surveysService.listSurveys().subscribe({
      next: (surveys) => {
        this.surveys = surveys;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading surveys:', err);
        this.loading = false;
      }
    });
  }

  publish(surveyId: number) {
    this.surveysService.publishSurvey(surveyId).subscribe({
      next: () => this.loadSurveys()
    });
  }

  archive(surveyId: number) {
    this.surveysService.archiveSurvey(surveyId).subscribe({
      next: () => this.loadSurveys()
    });
  }

  viewStats(surveyId: number) {
    console.log('View stats for survey:', surveyId);
  }
}
```

### Response List Component

Create `src/app/responses/response-list.component.ts`:

```typescript
import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-response-list',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="response-list">
      <h1>Survey Responses</h1>
      <p>Response viewer coming soon...</p>
    </div>
  `,
  styles: [`
    .response-list {
      background: white;
      padding: 30px;
      border-radius: 8px;
    }
  `]
})
export class ResponseListComponent {}
```

---

## 🎯 Testing the App

1. **Start Backend:**
   ```bash
   cd /home/maksich/Documents/ACE-RealEstate
   ./run_backend.sh
   ```

2. **Start Frontend:**
   ```bash
   cd frontend/manager-dashboard
   ng serve --port 4400
   ```

3. **Open Browser:**
   - Navigate to http://localhost:4400
   - Login with: admin / test123
   - You should see the dashboard!

---

## ✅ What Works Now

- ✅ Login page
- ✅ JWT authentication
- ✅ Protected routes
- ✅ Navigation sidebar
- ✅ User list
- ✅ Survey list
- ✅ Logout

## 🚧 What's Left (Optional Enhancements)

- Create/Edit user modals
- Survey builder UI
- Response details viewer
- Charts for statistics
- Real-time updates (SSE)
- Export to CSV

---

## 📚 Additional Resources

- **Backend API Docs:** http://localhost:8000/docs
- **Operations Guide:** `OPERATIONS.md`
- **Frontend Plan:** See plan document

**You now have a functional Angular dashboard connected to your backend!** 🎉
