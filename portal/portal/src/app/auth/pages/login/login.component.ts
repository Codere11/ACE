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
    <div class="card">
      <h1>Prijava v ACE</h1>
      <p style="opacity:.8;margin:0 0 12px">Vnesite podatke za dostop.</p>

      <input [(ngModel)]="username" placeholder="Uporabniško ime" autofocus />
      <div style="height:8px"></div>
      <input [(ngModel)]="password" placeholder="Geslo" type="password" />

      <button (click)="submit()" [disabled]="loading">
        {{ loading ? 'Prijava...' : 'Prijava' }}
      </button>

      <div *ngIf="error" style="color:#ff7777;margin-top:10px">{{ error }}</div>

      <div style="opacity:.6;font-size:.85rem;margin-top:12px">
        Namig: <code>admin / admin123</code> ali <code>demo / demo123</code>
      </div>
    </div>
  `
})
export class LoginComponent {
  username = '';
  password = '';
  loading = false;
  error = '';

  constructor(private auth: AuthService, private router: Router) {}

  submit() {
    this.error = '';
    this.loading = true;
    this.auth.login(this.username, this.password).subscribe({
      next: () => this.router.navigateByUrl('/home'),
      error: (e) => { this.error = e?.error?.detail || 'Napaka pri prijavi'; this.loading = false; }
    });
  }
}
