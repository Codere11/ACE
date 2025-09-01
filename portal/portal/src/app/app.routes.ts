import { Routes } from '@angular/router';
import { LoginComponent } from './auth/pages/login/login.component';
import { authGuard } from './auth/guards/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  {
    path: 'home',
    canActivate: [authGuard],
    loadComponent: () => import('./home.component').then(m => m.HomeComponent)
  },
  { path: '**', redirectTo: 'login' }
];
