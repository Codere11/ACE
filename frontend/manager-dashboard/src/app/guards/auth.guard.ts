import { inject } from '@angular/core';
import { Router, CanActivateFn } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);
  
  const isAuth = authService.isAuthenticated();
  console.log('AUTH GUARD CHECK:', isAuth, 'token:', authService.getToken());

  if (isAuth) {
    return true;
  }

  console.log('NOT AUTHENTICATED - REDIRECTING TO LOGIN');
  router.navigate(['/login']);
  return false;
};
