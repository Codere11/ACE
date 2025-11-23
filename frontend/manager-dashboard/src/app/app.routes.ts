import { Routes } from '@angular/router';
import { LoginComponent } from './auth/login.component';
import { authGuard } from './guards/auth.guard';
import { SurveyListComponent } from './surveys/survey-list.component';
import { SurveyFormComponent } from './surveys/survey-form.component';
import { SimpleSurveyBuilderComponent } from './simple-survey-builder/simple-survey-builder.component';

export const routes: Routes = [
  {
    path: 'login',
    component: LoginComponent
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./dashboard-wrapper.component').then(m => m.DashboardWrapperComponent)
  },
  {
    path: 'surveys',
    canActivate: [authGuard],
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
];
