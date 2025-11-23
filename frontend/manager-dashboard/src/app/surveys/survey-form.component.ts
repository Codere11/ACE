import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { SurveysService } from '../services/surveys.service';
import { Survey, SurveyCreate } from '../models/survey.model';

@Component({
  selector: 'app-survey-form',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="survey-form-container">
      <div class="form-header">
        <h2>{{ isEditing ? 'Edit Survey' : 'Create New Survey' }}</h2>
        <button class="btn-close" (click)="goBack()">✕</button>
      </div>

      <div class="form-body">
        <div class="form-group">
          <label for="name">Survey Name *</label>
          <input 
            id="name"
            type="text" 
            [(ngModel)]="surveyName" 
            placeholder="e.g., Customer Satisfaction Survey"
            [disabled]="loading"
            (ngModelChange)="generateSlug()"
          />
          <small>This is the internal name shown in your dashboard</small>
        </div>

        <div class="form-group">
          <label for="slug">URL Slug *</label>
          <input 
            id="slug"
            type="text" 
            [(ngModel)]="surveySlug" 
            placeholder="e.g., customer-satisfaction"
            [disabled]="loading"
          />
          <small>Public URL: <strong>{{ getPublicUrl() }}</strong></small>
        </div>

        <div class="form-group">
          <label for="type">Survey Type *</label>
          <select id="type" [(ngModel)]="surveyType" [disabled]="loading || isEditing">
            <option value="regular">Regular Survey</option>
            <option value="ab_test">A/B Test (2 Variants)</option>
          </select>
          <small *ngIf="surveyType === 'ab_test'">
            💡 A/B testing allows you to create two versions of your survey to compare performance
          </small>
        </div>

        <div class="form-actions">
          <button class="btn-secondary" (click)="goBack()" [disabled]="loading">
            Cancel
          </button>
          <button 
            class="btn-primary" 
            (click)="save()" 
            [disabled]="loading || !isValid()"
          >
            {{ loading ? 'Saving...' : (isEditing ? 'Save & Edit Flow' : 'Create & Build Flow') }}
          </button>
        </div>

        <div class="error-message" *ngIf="errorMessage">
          ⚠️ {{ errorMessage }}
        </div>
      </div>
    </div>
  `,
  styles: [`
    .survey-form-container {
      max-width: 600px;
      margin: 40px auto;
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      overflow: hidden;
    }

    .form-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 20px 30px;
      background: #f8f9fa;
      border-bottom: 2px solid #e0e0e0;
    }

    .form-header h2 {
      margin: 0;
      font-size: 24px;
      color: #333;
    }

    .btn-close {
      padding: 8px 12px;
      background: transparent;
      border: none;
      font-size: 24px;
      cursor: pointer;
      color: #666;
      transition: color 0.2s;
    }

    .btn-close:hover {
      color: #333;
    }

    .form-body {
      padding: 30px;
    }

    .form-group {
      margin-bottom: 24px;
    }

    .form-group label {
      display: block;
      margin-bottom: 8px;
      font-weight: 600;
      color: #333;
      font-size: 14px;
    }

    .form-group input,
    .form-group select {
      width: 100%;
      padding: 12px;
      border: 2px solid #e0e0e0;
      border-radius: 6px;
      font-size: 14px;
      transition: border-color 0.2s;
    }

    .form-group input:focus,
    .form-group select:focus {
      outline: none;
      border-color: #3498db;
    }

    .form-group input:disabled,
    .form-group select:disabled {
      background: #f5f5f5;
      cursor: not-allowed;
    }

    .form-group small {
      display: block;
      margin-top: 6px;
      color: #666;
      font-size: 12px;
    }

    .form-group small strong {
      color: #3498db;
    }

    .form-actions {
      display: flex;
      gap: 12px;
      justify-content: flex-end;
      margin-top: 32px;
      padding-top: 24px;
      border-top: 1px solid #e0e0e0;
    }

    .btn-primary,
    .btn-secondary {
      padding: 12px 24px;
      border: none;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }

    .btn-primary {
      background: #3498db;
      color: white;
    }

    .btn-primary:hover:not(:disabled) {
      background: #2980b9;
    }

    .btn-primary:disabled {
      background: #bdc3c7;
      cursor: not-allowed;
    }

    .btn-secondary {
      background: #ecf0f1;
      color: #333;
    }

    .btn-secondary:hover:not(:disabled) {
      background: #d5d8dc;
    }

    .error-message {
      margin-top: 16px;
      padding: 12px;
      background: #ffebee;
      border-left: 4px solid #e74c3c;
      border-radius: 4px;
      color: #c0392b;
      font-size: 14px;
    }
  `]
})
export class SurveyFormComponent implements OnInit {
  @Input() inlineMode = false;
  @Output() created = new EventEmitter<number>();
  @Output() cancelled = new EventEmitter<void>();

  surveyName = '';
  surveySlug = '';
  surveyType: 'regular' | 'ab_test' = 'regular';
  loading = false;
  errorMessage = '';
  isEditing = false;
  surveyId?: number;
  existingSurvey?: Survey;

  constructor(
    private surveysService: SurveysService,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit() {
    // Check if editing
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEditing = true;
      this.surveyId = parseInt(id);
      this.loadSurvey();
    }
  }

  loadSurvey() {
    if (!this.surveyId) return;
    
    this.loading = true;
    this.surveysService.getSurvey(this.surveyId).subscribe({
      next: (survey) => {
        this.existingSurvey = survey;
        this.surveyName = survey.name;
        this.surveySlug = survey.slug;
        this.surveyType = survey.survey_type;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading survey:', err);
        this.errorMessage = 'Failed to load survey';
        this.loading = false;
      }
    });
  }

  generateSlug() {
    // Auto-generate slug from name if not manually edited
    if (!this.isEditing) {
      this.surveySlug = this.surveyName
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '');
    }
  }

  getPublicUrl(): string {
    if (!this.surveySlug) return 'Enter a slug to see URL';
    return `${window.location.origin}/s/${this.surveySlug}`;
  }

  isValid(): boolean {
    return !!(this.surveyName.trim() && this.surveySlug.trim());
  }

  save() {
    if (!this.isValid()) return;

    this.loading = true;
    this.errorMessage = '';

    if (this.isEditing && this.surveyId) {
      // Update existing
      this.surveysService.updateSurvey(this.surveyId, {
        name: this.surveyName,
        slug: this.surveySlug,
        survey_type: this.surveyType
      }).subscribe({
        next: (survey) => {
          this.loading = false;
          // Navigate to builder
          this.router.navigate(['/surveys', survey.id, 'edit']);
        },
        error: (err) => {
          console.error('Error updating survey:', err);
          this.errorMessage = err.error?.detail || 'Failed to update survey';
          this.loading = false;
        }
      });
    } else {
      // Create new
      const newSurvey: SurveyCreate = {
        name: this.surveyName,
        slug: this.surveySlug,
        survey_type: this.surveyType,
        status: 'draft',
        organization_id: this.surveysService['getOrgId']() // Access via service
      };

      this.surveysService.createSurvey(newSurvey).subscribe({
        next: (survey) => {
          this.loading = false;
          if (this.inlineMode) {
            this.created.emit(survey.id);
          } else {
            this.router.navigate(['/surveys', survey.id, 'edit']);
          }
        },
        error: (err) => {
          console.error('Error creating survey:', err);
          this.errorMessage = err.error?.detail || 'Failed to create survey';
          this.loading = false;
        }
      });
    }
  }

  goBack() {
    if (this.inlineMode) {
      this.cancelled.emit();
    } else {
      this.router.navigate(['/surveys']);
    }
  }
}
