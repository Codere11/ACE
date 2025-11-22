import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient } from '@angular/common/http';   // <-- add this
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';
import { provideCharts, withDefaultRegisterables } from 'ng2-charts';
import { withFetch } from '@angular/common/http';

bootstrapApplication(AppComponent, {
  providers: [
    provideCharts(withDefaultRegisterables()),
    provideHttpClient(withFetch())
  ],
}).catch(err => console.error(err));
