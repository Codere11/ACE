import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';

import { HttpClientModule, provideHttpClient, withInterceptors } from '@angular/common/http';
import { importProvidersFrom } from '@angular/core';

import { AppComponent } from './app/app.component';
import { routes } from './app/app.routes';
import { authTokenInterceptor } from './app/auth/interceptors/auth-token.interceptor';

bootstrapApplication(AppComponent, {
  providers: [
    provideHttpClient(withInterceptors([authTokenInterceptor])),
    importProvidersFrom(HttpClientModule),
    provideRouter(routes),
  ]
}).catch(err => console.error(err));
