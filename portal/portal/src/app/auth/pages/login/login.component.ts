import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent {
  username = '';
  password = '';
  loading = false;
  error = '';

  constructor(private auth: AuthService, private router: Router) {}

  submit() {
    this.error = ''; this.loading = true;
    this.auth.login(this.username, this.password).subscribe({
      next: () => this.router.navigateByUrl('/'),
      error: (e) => { this.error = e?.error?.detail || 'Napaka pri prijavi'; this.loading = false; }
    });
  }
}
