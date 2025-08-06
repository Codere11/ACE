import { bootstrapApplication } from '@angular/platform-browser';
import { RootComponent } from './app/root.component';
import { AppComponent } from './app/app.component';
import { appConfig } from './app/app.config';
import { MarkdownModule } from 'ngx-markdown';
import { importProvidersFrom } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';

bootstrapApplication(AppComponent, {
  providers: [
    provideHttpClient(),
    importProvidersFrom(MarkdownModule.forRoot())
  ]
});