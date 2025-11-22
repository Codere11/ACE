import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="login-container">
      <div class="login-box">
        <h1>ACE Manager Login</h1>
        
        @if (error) {
          <div class="error">{{error}}</div>
        }
        
        <form (ngSubmit)="onSubmit()">
          <div class="form-group">
            <label>Username</label>
            <input 
              type="text" 
              [(ngModel)]="username" 
              name="username"
              required
            >
          </div>
          
          <div class="form-group">
            <label>Password</label>
            <input 
              type="password" 
              [(ngModel)]="password" 
              name="password"
              required
            >
          </div>
          
          <button type="submit" [disabled]="loading">
            {{loading ? 'Logging in...' : 'Login'}}
          </button>
        </form>
      </div>
    </div>
  `,
  styles: [`
    .login-container {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .login-box {
      background: white;
      padding: 40px;
      border-radius: 10px;
      box-shadow: 0 10px 40px rgba(0,0,0,0.2);
      width: 100%;
      max-width: 400px;
    }
    
    h1 {
      margin: 0 0 30px 0;
      color: #333;
      text-align: center;
    }
    
    .error {
      background: #fee;
      color: #c33;
      padding: 10px;
      border-radius: 4px;
      margin-bottom: 20px;
    }
    
    .form-group {
      margin-bottom: 20px;
    }
    
    label {
      display: block;
      margin-bottom: 5px;
      color: #555;
      font-weight: 500;
    }
    
    input {
      width: 100%;
      padding: 12px;
      border: 1px solid #ddd;
      border-radius: 6px;
      font-size: 14px;
      box-sizing: border-box;
    }
    
    button {
      width: 100%;
      padding: 12px;
      background: #667eea;
      color: white;
      border: none;
      border-radius: 6px;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
    }
    
    button:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  `]
})
export class LoginComponent {
  username = '';
  password = '';
  loading = false;
  error = '';

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  onSubmit() {
    this.error = '';
    this.loading = true;

    this.authService.login(this.username, this.password).subscribe({
      next: () => {
        this.router.navigate(['/']);
      },
      error: (err) => {
        this.error = 'Login failed';
        this.loading = false;
      }
    });
  }
}
