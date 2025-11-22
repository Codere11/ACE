import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SurveysService } from '../services/surveys.service';
import { Survey } from '../models/survey.model';

@Component({
  selector: 'app-survey-list',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="survey-list">
      <div class="header">
        <h1>Surveys</h1>
        <button class="btn-primary">+ Create Survey</button>
      </div>
      
      @if (loading) {
        <p>Loading surveys...</p>
      } @else if (surveys.length === 0) {
        <p>No surveys yet. Create your first survey!</p>
      } @else {
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (survey of surveys; track survey.id) {
              <tr>
                <td>{{survey.name}}</td>
                <td>{{survey.survey_type}}</td>
                <td>
                  <span class="status-badge" [class]="survey.status">
                    {{survey.status}}
                  </span>
                </td>
                <td>{{survey.created_at | date}}</td>
                <td>
                  <button (click)="viewStats(survey.id)">Stats</button>
                  @if (survey.status === 'draft') {
                    <button (click)="publish(survey.id)">Publish</button>
                  }
                  @if (survey.status === 'live') {
                    <button (click)="archive(survey.id)">Archive</button>
                  }
                </td>
              </tr>
            }
          </tbody>
        </table>
      }
    </div>
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

  constructor(private surveysService: SurveysService) {}

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

  viewStats(surveyId: number) {
    console.log('View stats for survey:', surveyId);
  }
}
