import { Component } from '@angular/core';
import { AppComponent } from './app.component';

@Component({
  selector: 'app-dashboard-wrapper',
  standalone: true,
  imports: [AppComponent],
  template: '<app-root></app-root>'
})
export class DashboardWrapperComponent {}
