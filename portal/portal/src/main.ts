import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';

import { provideHttpClient, withInterceptors, withFetch } from '@angular/common/http';

import { AppComponent } from './app/app.component';
import { routes } from './app/app.routes';
import { authTokenInterceptor } from './app/auth/interceptors/auth-token.interceptor';

bootstrapApplication(AppComponent, {
  providers: [
    // Root HttpClient (correct place for EnvironmentProviders)
    provideHttpClient(
      withInterceptors([authTokenInterceptor]),
      withFetch()
    ),
    provideRouter(routes),
  ]
}).catch(err => console.error(err));
