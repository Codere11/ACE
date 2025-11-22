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
