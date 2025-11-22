import { Routes } from '@angular/router';
import { LoginComponent } from './auth/login.component';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    component: LoginComponent
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./dashboard-wrapper.component').then(m => m.DashboardWrapperComponent)
  }
];
