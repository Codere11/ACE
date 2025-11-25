import { Routes } from '@angular/router';
import { AppComponent } from './app.component';

export const routes: Routes = [
  { path: ':org_slug/:survey_slug', component: AppComponent },
  { path: '', component: AppComponent },
];
