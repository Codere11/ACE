import { Routes } from '@angular/router';
import { LoginComponent } from './auth/login.component';
import { authGuard } from './guards/auth.guard';
import { SurveyListComponent } from './surveys/survey-list.component';
import { SurveyFormComponent } from './surveys/survey-form.component';
import { SimpleSurveyBuilderComponent } from './simple-survey-builder/simple-survey-builder.component';

export const routes: Routes = [
  // Universal login route (no org slug required)
  {
    path: 'login',
    component: LoginComponent
  },
  // Org-specific login (backward compatibility)
  {
    path: ':org_slug/login',
    component: LoginComponent
  },
  {
    path: ':org_slug',
    canActivate: [authGuard],
    children: [
      {
        path: '',
        loadComponent: () => import('./dashboard-wrapper.component').then(m => m.DashboardWrapperComponent)
      },
      {
        path: 'surveys',
        children: [
          {
            path: '',
            component: SurveyListComponent
          },
          {
            path: 'new',
            component: SurveyFormComponent
          },
          {
            path: ':id/edit',
            component: SimpleSurveyBuilderComponent
          },
          {
            path: ':id/metadata',
            component: SurveyFormComponent
          }
        ]
      }
    ]
  },
  // Fallback redirect
  {
    path: '',
    redirectTo: '/login',
    pathMatch: 'full'
  }
];
