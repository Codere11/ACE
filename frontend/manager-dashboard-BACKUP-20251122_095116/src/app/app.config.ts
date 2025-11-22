// app.config.ts
import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideCharts } from 'ng2-charts';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter([]),
    provideHttpClient(),
    provideAnimations(),
    provideCharts() // ✅ Required for ng2-charts
  ]
};
