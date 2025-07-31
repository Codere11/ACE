import { Routes } from '@angular/router';
import { FacebookAdComponent } from './facebook-ad.component';
import { AppComponent } from './app.component';

export const routes: Routes = [
  { path: '', component: FacebookAdComponent },
  { path: 'chat', component: AppComponent },
  { path: '**', redirectTo: '' },
];
