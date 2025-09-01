import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  // Inline template so you ALWAYS see something even if routes fail
  template: `
    <div style="max-width:1080px;margin:0 auto;padding:12px 0">
      <header style="display:flex;align-items:center;gap:10px;padding:6px 12px;border-radius:12px;background:#151515;border:1px solid #2a2a2a">
        <div style="font-weight:700">ACE Portal</div>
        <div style="opacity:.7;font-size:.9rem">/login → /home</div>
      </header>
    </div>
    <router-outlet></router-outlet>
  `
})
export class AppComponent {}
