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
