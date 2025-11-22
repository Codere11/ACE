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
