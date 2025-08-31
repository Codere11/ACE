import { Routes } from '@angular/router';
import { LoginComponent } from './auth/pages/login/login.component';
import { authGuard } from './auth/guards/auth.guard';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./home.component').then(m => m.HomeComponent)
  },
  { path: '**', redirectTo: '' }
];
