import { ApplicationConfig, importProvidersFrom } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { provideMarkdown } from 'ngx-markdown';

// your existing routes file
import { routes } from './app.routes';

// make template-driven + reactive forms and common directives available app-wide
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

export const appConfig: ApplicationConfig = {
  providers: [
    // framework
    provideHttpClient(),
    provideAnimations(),
    provideRouter(routes),

    // libraries
    provideMarkdown(),           // ✅ Markdown preserved

    // classic NgModules for standalone apps
    importProvidersFrom(
      CommonModule,              // ✅ *ngIf, *ngFor
      FormsModule,               // ✅ [(ngModel)]
      ReactiveFormsModule        // ✅ FormBuilder / reactive forms
    ),
  ],
};
