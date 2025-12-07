import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { SurveysService } from '../services/surveys.service';
import { Survey } from '../models/survey.model';
import { SurveyFormComponent } from './survey-form.component';
import { SimpleSurveyBuilderComponent } from '../simple-survey-builder/simple-survey-builder.component';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-survey-list',
  standalone: true,
  imports: [CommonModule, SurveyFormComponent, SimpleSurveyBuilderComponent],
  template: `
    <div class="survey-list" *ngIf="!showingForm && !showingBuilder">
      <div class="header">
        <h1>Ankete</h1>
        <button class="btn-primary" (click)="createSurvey()">+ Ustvari anketo</button>
      </div>
      
      @if (loading) {
        <p>Nalagam ankete...</p>
      } @else if (surveys.length === 0) {
        <p>Še ni anket. Ustvarite svojo prvo anketo!</p>
      } @else {
        <table>
          <thead>
            <tr>
              <th>Ime</th>
              <th>Status</th>
              <th>Ustvarjeno</th>
              <th>Akcije</th>
            </tr>
          </thead>
          <tbody>
            @for (survey of surveys; track survey.id) {
              <tr>
                <td>
                  <a class="survey-link" (click)="editSurvey(survey.id)">{{survey.name}}</a>
                  <div class="survey-url">{{getPublicUrl(survey.slug)}}</div>
                </td>
                <td>
                  <span class="status-badge" [class]="survey.status">
                    {{translateStatus(survey.status)}}
                  </span>
                </td>
                <td>{{survey.created_at | date}}</td>
                <td class="actions">
                  <button class="btn-edit" (click)="editSurvey(survey.id)">Uredi tok</button>
                  @if (survey.status === 'draft') {
                    <button class="btn-publish" (click)="publish(survey.id)">Objavi</button>
                  }
                  @if (survey.status === 'live') {
                    <button class="btn-archive" (click)="archive(survey.id)">Arhiviraj</button>
                  }
                  <button class="btn-delete" (click)="deleteSurvey(survey.id, survey.name)">Izbriši</button>
                </td>
              </tr>
            }
          </tbody>
        </table>
      }
    </div>

    <!-- Inline Survey Form -->
    <app-survey-form 
      *ngIf="showingForm" 
      [inlineMode]="true"
      (created)="onSurveyCreated($event)"
      (cancelled)="onFormCancel()"
    ></app-survey-form>

    <!-- Inline Survey Builder -->
    <app-simple-survey-builder
      *ngIf="showingBuilder && editingSurveyId"
      [surveyId]="editingSurveyId"
      [inlineMode]="true"
      (closed)="onBuilderClose()"
    ></app-simple-survey-builder>
  `,
  styles: [`
    .survey-list {
      background: white;
      padding: 30px;
      border-radius: 8px;
    }
    
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }
    
    .btn-primary {
      padding: 10px 20px;
      background: #3498db;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
    }
    
    table {
      width: 100%;
      border-collapse: collapse;
    }
    
    th, td {
      padding: 12px;
      text-align: left;
      border-bottom: 1px solid #ddd;
    }

    th {
      background: #f8f9fa;
      font-weight: 600;
      color: #555;
    }

    .survey-link {
      color: #3498db;
      cursor: pointer;
      font-weight: 500;
    }

    .survey-link:hover {
      text-decoration: underline;
    }

    .survey-url {
      font-size: 11px;
      color: #999;
      margin-top: 4px;
    }

    .actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .actions button {
      padding: 6px 12px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
      transition: all 0.2s;
    }

    .btn-edit {
      background: #3498db;
      color: white;
    }

    .btn-edit:hover {
      background: #2980b9;
    }

    .btn-publish {
      background: #27ae60;
      color: white;
    }

    .btn-publish:hover {
      background: #229954;
    }

    .btn-archive {
      background: #95a5a6;
      color: white;
    }

    .btn-archive:hover {
      background: #7f8c8d;
    }

    .btn-delete {
      background: #e74c3c;
      color: white;
    }

    .btn-delete:hover {
      background: #c0392b;
    }
    
    .status-badge {
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
    }
    
    .status-badge.draft {
      background: #f39c12;
      color: white;
    }
    
    .status-badge.live {
      background: #27ae60;
      color: white;
    }
    
    .status-badge.archived {
      background: #95a5a6;
      color: white;
    }
  `]
})
export class SurveyListComponent implements OnInit {
  surveys: Survey[] = [];
  loading = true;

  constructor(
    private surveysService: SurveysService,
    private router: Router,
    private authService: AuthService
  ) {}

  ngOnInit() {
    this.loadSurveys();
  }

  loadSurveys() {
    this.surveysService.listSurveys().subscribe({
      next: (surveys) => {
        this.surveys = surveys;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading surveys:', err);
        this.loading = false;
      }
    });
  }

  publish(surveyId: number) {
    this.surveysService.publishSurvey(surveyId).subscribe({
      next: () => this.loadSurveys()
    });
  }

  archive(surveyId: number) {
    this.surveysService.archiveSurvey(surveyId).subscribe({
      next: () => this.loadSurveys()
    });
  }

  showingForm = false;
  showingBuilder = false;
  editingSurveyId: number | null = null;

  createSurvey() {
    this.editingSurveyId = null;
    this.showingForm = true;
  }

  editSurvey(surveyId: number) {
    this.editingSurveyId = surveyId;
    this.showingBuilder = true;
  }

  onSurveyCreated(surveyId: number) {
    this.showingForm = false;
    this.editingSurveyId = surveyId;
    this.showingBuilder = true;
  }

  onFormCancel() {
    this.showingForm = false;
    this.editingSurveyId = null;
  }

  onBuilderClose() {
    this.showingBuilder = false;
    this.editingSurveyId = null;
    this.loadSurveys();
  }

  deleteSurvey(surveyId: number, surveyName: string) {
    if (confirm(`Ali ste prepričani, da želite izbrisati "${surveyName}"? Tega ne morete razveljaviti.`)) {
      this.surveysService.deleteSurvey(surveyId).subscribe({
        next: () => {
          this.loadSurveys();
        },
        error: (err) => {
          console.error('Error deleting survey:', err);
          alert('Napaka pri brisanju ankete');
        }
      });
    }
  }

  getPublicUrl(slug: string): string {
    const user = this.authService.getCurrentUser();
    const orgSlug = user?.organization_slug || 'default';
    return `http://localhost:4200/${orgSlug}/${slug}`;
  }

  viewStats(surveyId: number) {
    console.log('View stats for survey:', surveyId);
    // TODO: Navigate to stats page
  }
  
  translateStatus(status: string): string {
    const translations: Record<string, string> = {
      'draft': 'Osnutek',
      'live': 'Objavljeno',
      'archived': 'Arhivirano'
    };
    return translations[status] || status;
  }
}
