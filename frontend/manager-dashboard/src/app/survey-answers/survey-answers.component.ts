import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-survey-answers',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="survey-answers" *ngIf="answers && hasAnswers()">
      <div class="answers-header">
        <h4>📋 Survey Odgovori</h4>
        <div class="progress-badge" *ngIf="progress !== undefined">
          <div class="progress-bar-mini">
            <div class="progress-fill-mini" [style.width.%]="progress"></div>
          </div>
          <span class="progress-text">{{ progress }}%</span>
        </div>
      </div>

      <div class="answers-list">
        <div class="answer-item" *ngFor="let item of getAnswersList()">
          <div class="answer-question">{{ formatQuestionId(item.key) }}</div>
          <div class="answer-value">{{ formatAnswer(item.value) }}</div>
        </div>
      </div>

      <div class="survey-meta" *ngIf="startedAt || completedAt">
        <div class="meta-item" *ngIf="startedAt">
          <span class="meta-label">Začeto:</span>
          <span class="meta-value">{{ formatDate(startedAt) }}</span>
        </div>
        <div class="meta-item" *ngIf="completedAt">
          <span class="meta-label">Zaključeno:</span>
          <span class="meta-value">{{ formatDate(completedAt) }}</span>
        </div>
      </div>
    </div>

    <div class="survey-empty" *ngIf="!answers || !hasAnswers()">
      <span class="empty-icon">📝</span>
      <p>Ni izpolnjene ankete</p>
    </div>
  `,
  styles: [`
    .survey-answers {
      padding: 16px;
      background: #f9fafb;
      border-radius: 8px;
      margin: 12px 0;
    }

    .answers-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 2px solid #e5e7eb;
    }

    .answers-header h4 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
      color: #111827;
    }

    .progress-badge {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .progress-bar-mini {
      width: 60px;
      height: 6px;
      background: #e5e7eb;
      border-radius: 3px;
      overflow: hidden;
    }

    .progress-fill-mini {
      height: 100%;
      background: linear-gradient(90deg, #3b82f6, #8b5cf6);
      transition: width 0.3s ease;
    }

    .progress-text {
      font-size: 12px;
      font-weight: 600;
      color: #6b7280;
    }

    .answers-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .answer-item {
      background: white;
      padding: 12px;
      border-radius: 6px;
      border: 1px solid #e5e7eb;
    }

    .answer-question {
      font-size: 13px;
      font-weight: 600;
      color: #6b7280;
      margin-bottom: 4px;
    }

    .answer-value {
      font-size: 14px;
      color: #111827;
      word-break: break-word;
    }

    .survey-meta {
      margin-top: 16px;
      padding-top: 12px;
      border-top: 1px solid #e5e7eb;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .meta-item {
      display: flex;
      justify-content: space-between;
      font-size: 13px;
    }

    .meta-label {
      color: #6b7280;
      font-weight: 500;
    }

    .meta-value {
      color: #111827;
    }

    .survey-empty {
      padding: 32px;
      text-align: center;
      background: #f9fafb;
      border-radius: 8px;
      margin: 12px 0;
    }

    .empty-icon {
      font-size: 48px;
      display: block;
      margin-bottom: 12px;
      opacity: 0.5;
    }

    .survey-empty p {
      margin: 0;
      color: #6b7280;
      font-size: 14px;
    }
  `]
})
export class SurveyAnswersComponent {
  @Input() answers: Record<string, any> | null = null;
  @Input() progress: number | undefined;
  @Input() startedAt: string | null = null;
  @Input() completedAt: string | null = null;
  @Input() showOnlyLast: boolean = true;

  hasAnswers(): boolean {
    return !!(this.answers && Object.keys(this.answers).length > 0);
  }

  getAnswersList(): { key: string; value: any }[] {
    if (!this.answers) return [];
    const allAnswers = Object.entries(this.answers).map(([key, value]) => ({ key, value }));
    if (this.showOnlyLast && allAnswers.length > 0) {
      return [allAnswers[allAnswers.length - 1]];
    }
    return allAnswers;
  }

  formatQuestionId(id: string): string {
    // Convert node IDs to readable labels
    const labels: Record<string, string> = {
      'welcome': 'Kontakt',
      'intent': 'Namen',
      'property_type': 'Tip nepremičnine',
      'location': 'Lokacija',
      'budget': 'Proračun',
      'timing': 'Časovni okvir',
      'financing': 'Financiranje',
      'history': 'Pretekli ogledi',
      'notes': 'Dodatne želje'
    };
    return labels[id] || id.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  formatAnswer(value: any): string {
    if (value === null || value === undefined) return '-';
    
    if (typeof value === 'object') {
      // Extract text from {text, score} objects
      if (value.text !== undefined) {
        return String(value.text);
      }
      // Handle contact objects
      if (value.email && value.phone) {
        return `${value.email} | ${value.phone}`;
      }
      if (value.email) return value.email;
      if (value.phone) return value.phone;
      // Fallback for other objects
      return JSON.stringify(value, null, 2);
    }
    
    return String(value);
  }

  formatDate(dateStr: string | null): string {
    if (!dateStr) return '-';
    try {
      const date = new Date(dateStr);
      return date.toLocaleString('sl-SI', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  }
}
