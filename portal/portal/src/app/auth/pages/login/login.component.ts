import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, NgForm } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpClientModule } from '@angular/common/http'; // optional, harmless
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  // Keeping HttpClientModule in imports is fine (it won’t hurt); the real provider is at root.
  imports: [CommonModule, FormsModule, HttpClientModule],
  template: `
    <div class="card">
      <h1>Prijava v ACE</h1>
      <p style="opacity:.8;margin:0 0 12px">Vnesite podatke za dostop.</p>

      <form (ngSubmit)="submit(form)" #form="ngForm" novalidate>
        <input name="username" [(ngModel)]="username" placeholder="Uporabniško ime" required autofocus />
        <div style="height:8px"></div>
        <input name="password" [(ngModel)]="password" placeholder="Geslo" type="password" required />

        <button type="submit" [disabled]="loading || form.invalid">
          {{ loading ? 'Prijava...' : 'Prijava' }}
        </button>
      </form>

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

  submit(form: NgForm) {
    if (form.invalid) return;
    this.error = '';
    this.loading = true;

    this.auth.login(this.username.trim(), this.password.trim()).subscribe({
      next: () => queueMicrotask(() => this.router.navigateByUrl('/home')),
      error: (e) => {
        console.error('[LoginComponent] error', e);
        this.error = e?.error?.detail || e?.message || 'Napaka pri prijavi';
        this.loading = false;
      }
    });
  }
}
