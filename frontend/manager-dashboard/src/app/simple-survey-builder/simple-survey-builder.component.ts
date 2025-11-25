import { Component, OnInit, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CdkDragDrop, DragDropModule, moveItemInArray } from '@angular/cdk/drag-drop';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router } from '@angular/router';
import { SurveysService } from '../services/surveys.service';
import { Survey } from '../models/survey.model';
import { AuthService } from '../services/auth.service';

interface Question {
  id: string;
  type: 'choice' | 'text' | 'email' | 'phone' | 'contact';
  question: string;
  choices?: string[];
  scores?: number[];  // Score for each choice (parallel array)
  baseScore?: number;  // Score for open-ended/contact questions
}

@Component({
  selector: 'app-simple-survey-builder',
  standalone: true,
  imports: [CommonModule, FormsModule, DragDropModule],
  template: `
    <div class="builder-container">
      <div class="builder-header">
        <div class="header-left">
          <button class="btn-back" (click)="goBack()">← Back to Surveys</button>
          <div class="survey-info" *ngIf="survey">
            <h2>📋 {{ survey.name }}</h2>
            <span class="survey-status" [class]="survey.status">{{ survey.status }}</span>
          </div>
        </div>
        <div class="actions">
          <button class="btn-secondary" (click)="openPreview()" *ngIf="survey" [disabled]="loading">🚀 Test Live</button>
          <button class="btn-primary" (click)="saveSurvey()" [disabled]="loading">💾 Save Flow</button>
        </div>
      </div>

      <div class="builder-main">
        <!-- Question Types Palette -->
        <aside class="palette">
          <h3>Add Questions</h3>
          <div class="question-types">
            <button class="type-btn" (click)="addQuestion('contact')">
              <span class="icon">📧</span>
              Contact Info
            </button>
            <button class="type-btn" (click)="addQuestion('choice')">
              <span class="icon">☑️</span>
              Multiple Choice
            </button>
            <button class="type-btn" (click)="addQuestion('text')">
              <span class="icon">📝</span>
              Text Answer
            </button>
            <button class="type-btn" (click)="addQuestion('email')">
              <span class="icon">✉️</span>
              Email Only
            </button>
            <button class="type-btn" (click)="addQuestion('phone')">
              <span class="icon">📱</span>
              Phone Only
            </button>
          </div>
        </aside>

        <!-- Questions List (Drag & Drop) -->
        <main class="questions-area">
          <div class="empty-state" *ngIf="questions.length === 0">
            <p>👈 Click a question type to start building your survey</p>
          </div>

          <div 
            cdkDropList 
            (cdkDropListDropped)="drop($event)"
            class="questions-list">
            
            <div 
              *ngFor="let q of questions; let i = index" 
              cdkDrag
              class="question-card">
              
              <div class="question-header">
                <span class="drag-handle" cdkDragHandle>⋮⋮</span>
                <span class="question-number">Question {{ i + 1 }}</span>
                <span class="question-type-badge">{{ getTypeLabel(q.type) }}</span>
                <button class="btn-delete" (click)="deleteQuestion(i)">🗑️</button>
              </div>

              <div class="question-body">
                <!-- Question Text -->
                <div class="form-group">
                  <label>Question:</label>
                  <input 
                    type="text" 
                    [(ngModel)]="q.question"
                    placeholder="Enter your question here..."
                    class="input-large">
                </div>

                <!-- Choices (for choice type) -->
                <div *ngIf="q.type === 'choice'" class="choices-editor">
                  <label>Answer Choices (with Score):</label>
                  <div class="choice-list">
                    <div *ngFor="let choice of q.choices; let ci = index; trackBy: trackByIndex" class="choice-item">
                      <input 
                        type="text" 
                        [(ngModel)]="q.choices![ci]"
                        placeholder="Choice {{ ci + 1 }}"
                        class="input-medium">
                      <input 
                        type="number" 
                        [(ngModel)]="q.scores![ci]"
                        placeholder="Score"
                        class="input-score"
                        title="Positive = good lead, Negative = bad lead">
                      <button class="btn-small" (click)="removeChoice(i, ci)">✕</button>
                    </div>
                  </div>
                  <button class="btn-add-choice" (click)="addChoice(i)">+ Add Choice</button>
                  <div class="score-info">
                    💡 <strong>Score Guide:</strong> Positive numbers (1-100) = good/interested lead, Negative numbers (-100 to 0) = bad/uninterested lead
                  </div>
                </div>

                <!-- Score for non-choice questions -->
                <div *ngIf="q.type !== 'choice'" class="form-group score-group">
                  <label>Score for providing this info:</label>
                  <input 
                    type="number" 
                    [(ngModel)]="q.baseScore"
                    placeholder="0"
                    class="input-score-large"
                    title="Points awarded for completing this question">
                  <small class="score-help">💡 Award points for providing contact info (e.g., +10 for email, +20 for phone)</small>
                </div>
                
                <!-- Info for special types -->
                <div *ngIf="q.type === 'contact'" class="info-box">
                  ℹ️ This will ask for both email and phone (at least one required)
                </div>
                <div *ngIf="q.type === 'email'" class="info-box">
                  ℹ️ This will validate email format
                </div>
                <div *ngIf="q.type === 'phone'" class="info-box">
                  ℹ️ This will ask for phone number
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>

      <!-- Preview Button -->
      <div class="builder-footer">
        <button class="btn-preview" (click)="togglePreview()">
          {{ showPreview ? '✏️ Edit Mode' : '👁️ Preview Survey' }}
        </button>
      </div>

      <!-- Preview Modal -->
      <div class="preview-modal" *ngIf="showPreview" (click)="togglePreview()">
        <div class="preview-content" (click)="$event.stopPropagation()">
          <div class="preview-header">
            <h3>Survey Preview</h3>
            <button class="btn-close" (click)="togglePreview()">✕</button>
          </div>
          <div class="preview-body">
            <div *ngFor="let q of questions; let i = index" class="preview-question">
              <p class="preview-question-text">{{ i + 1 }}. {{ q.question }}</p>
              
              <div *ngIf="q.type === 'choice'" class="preview-choices">
                <button *ngFor="let choice of q.choices" class="preview-choice-btn">
                  {{ choice }}
                </button>
              </div>
              
              <div *ngIf="q.type === 'text'" class="preview-input">
                <textarea placeholder="Your answer..." disabled></textarea>
              </div>
              
              <div *ngIf="q.type === 'email'" class="preview-input">
                <input type="email" placeholder="your@email.com" disabled>
              </div>
              
              <div *ngIf="q.type === 'phone'" class="preview-input">
                <input type="tel" placeholder="+386..." disabled>
              </div>
              
              <div *ngIf="q.type === 'contact'" class="preview-contact">
                <input type="email" placeholder="Email" disabled>
                <input type="tel" placeholder="Phone" disabled>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Success Message -->
      <div class="toast" *ngIf="showToast">
        {{ toastMessage }}
      </div>
    </div>
  `,
  styles: [`
    .builder-container {
      height: 100%;
      display: flex;
      flex-direction: column;
      background: #f5f5f5;
    }

    .builder-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 20px 30px;
      background: white;
      border-bottom: 2px solid #e0e0e0;
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 20px;
    }

    .btn-back {
      padding: 8px 16px;
      background: #f0f0f0;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
      color: #333;
    }

    .btn-back:hover {
      background: #e0e0e0;
    }

    .survey-info {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .survey-info h2 {
      margin: 0;
      font-size: 20px;
      color: #333;
    }

    .survey-status {
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
    }

    .survey-status.draft {
      background: #f39c12;
      color: white;
    }

    .survey-status.live {
      background: #27ae60;
      color: white;
    }

    .actions {
      display: flex;
      gap: 12px;
    }

    .btn-primary, .btn-secondary {
      padding: 10px 20px;
      border: none;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }

    .btn-primary {
      background: #4CAF50;
      color: white;
    }

    .btn-primary:hover {
      background: #45a049;
    }

    .btn-secondary {
      background: #f0f0f0;
      color: #333;
    }

    .btn-secondary:hover {
      background: #e0e0e0;
    }

    .builder-main {
      flex: 1;
      display: flex;
      overflow: hidden;
    }

    .palette {
      width: 250px;
      background: white;
      padding: 20px;
      border-right: 2px solid #e0e0e0;
      overflow-y: auto;
    }

    .palette h3 {
      margin: 0 0 16px 0;
      font-size: 16px;
      color: #666;
    }

    .question-types {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .type-btn {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      background: #f8f9fa;
      border: 2px solid #e0e0e0;
      border-radius: 8px;
      cursor: pointer;
      font-size: 14px;
      transition: all 0.2s;
      text-align: left;
    }

    .type-btn:hover {
      background: #e3f2fd;
      border-color: #2196F3;
      transform: translateY(-2px);
    }

    .type-btn .icon {
      font-size: 20px;
    }

    .questions-area {
      flex: 1;
      padding: 30px;
      overflow-y: auto;
    }

    .empty-state {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: #999;
      font-size: 18px;
    }

    .questions-list {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .question-card {
      background: white;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      transition: box-shadow 0.2s;
    }

    .question-card:hover {
      box-shadow: 0 4px 16px rgba(0,0,0,0.15);
    }

    .question-header {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px 20px;
      background: #f8f9fa;
      border-bottom: 1px solid #e0e0e0;
      border-radius: 12px 12px 0 0;
    }

    .drag-handle {
      cursor: grab;
      font-size: 18px;
      color: #999;
    }

    .drag-handle:active {
      cursor: grabbing;
    }

    .question-number {
      font-weight: 600;
      color: #333;
    }

    .question-type-badge {
      padding: 4px 12px;
      background: #e3f2fd;
      color: #1976D2;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
    }

    .btn-delete {
      margin-left: auto;
      padding: 6px 12px;
      background: #ffebee;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      transition: background 0.2s;
    }

    .btn-delete:hover {
      background: #ef5350;
    }

    .question-body {
      padding: 20px;
    }

    .form-group {
      margin-bottom: 16px;
    }

    .form-group label {
      display: block;
      margin-bottom: 8px;
      font-weight: 600;
      color: #555;
      font-size: 14px;
    }

    .input-large, .input-medium {
      width: 100%;
      padding: 12px;
      border: 2px solid #e0e0e0;
      border-radius: 6px;
      font-size: 14px;
      transition: border-color 0.2s;
    }

    .input-large:focus, .input-medium:focus {
      outline: none;
      border-color: #2196F3;
    }

    .choices-editor label {
      display: block;
      margin-bottom: 12px;
      font-weight: 600;
      color: #555;
      font-size: 14px;
    }

    .choice-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 12px;
    }

    .choice-item {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .input-medium {
      flex: 1;
    }

    .input-score {
      width: 80px;
      padding: 8px;
      border: 2px solid #e0e0e0;
      border-radius: 6px;
      font-size: 14px;
      text-align: center;
      font-weight: 600;
      transition: border-color 0.2s;
    }

    .input-score:focus {
      outline: none;
      border-color: #4CAF50;
    }

    .input-score[value^="-"] {
      color: #f44336;
    }

    .score-info {
      margin-top: 12px;
      padding: 10px 12px;
      background: #e8f5e9;
      border-left: 4px solid #4CAF50;
      border-radius: 4px;
      font-size: 12px;
      color: #2e7d32;
      line-height: 1.5;
    }

    .score-group {
      margin-top: 16px;
      padding: 12px;
      background: #f0f8ff;
      border-radius: 8px;
      border: 2px solid #2196F3;
    }

    .input-score-large {
      width: 120px;
      padding: 10px;
      border: 2px solid #2196F3;
      border-radius: 6px;
      font-size: 16px;
      text-align: center;
      font-weight: 700;
      transition: border-color 0.2s;
    }

    .input-score-large:focus {
      outline: none;
      border-color: #1976D2;
      box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.2);
    }

    .score-help {
      display: block;
      margin-top: 8px;
      color: #1565C0;
      font-size: 12px;
      font-weight: 500;
    }

    .btn-small {
      padding: 8px 12px;
      background: #ffebee;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-weight: 600;
    }

    .btn-add-choice {
      padding: 8px 16px;
      background: #e3f2fd;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 600;
      color: #1976D2;
    }

    .btn-add-choice:hover {
      background: #bbdefb;
    }

    .info-box {
      margin-top: 12px;
      padding: 12px;
      background: #fff3cd;
      border-left: 4px solid #ffc107;
      border-radius: 4px;
      font-size: 13px;
      color: #856404;
    }

    .builder-footer {
      padding: 20px 30px;
      background: white;
      border-top: 2px solid #e0e0e0;
      text-align: center;
    }

    .btn-preview {
      padding: 12px 32px;
      background: #9C27B0;
      color: white;
      border: none;
      border-radius: 6px;
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
    }

    .btn-preview:hover {
      background: #7B1FA2;
    }

    .preview-modal {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0,0,0,0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }

    .preview-content {
      background: white;
      border-radius: 12px;
      width: 90%;
      max-width: 600px;
      max-height: 80vh;
      display: flex;
      flex-direction: column;
    }

    .preview-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 20px;
      border-bottom: 2px solid #e0e0e0;
    }

    .preview-header h3 {
      margin: 0;
    }

    .btn-close {
      padding: 8px 12px;
      background: #f0f0f0;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 18px;
    }

    .preview-body {
      flex: 1;
      padding: 30px;
      overflow-y: auto;
    }

    .preview-question {
      margin-bottom: 30px;
    }

    .preview-question-text {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 16px;
      color: #333;
    }

    .preview-choices {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .preview-choice-btn {
      padding: 14px 18px;
      background: #f8f9fa;
      border: 2px solid #e0e0e0;
      border-radius: 8px;
      text-align: left;
      cursor: not-allowed;
    }

    .preview-input input, .preview-input textarea {
      width: 100%;
      padding: 12px;
      border: 2px solid #e0e0e0;
      border-radius: 6px;
      font-size: 14px;
    }

    .preview-input textarea {
      min-height: 80px;
      resize: vertical;
    }

    .preview-contact {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .preview-contact input {
      padding: 12px;
      border: 2px solid #e0e0e0;
      border-radius: 6px;
      font-size: 14px;
    }

    .toast {
      position: fixed;
      bottom: 30px;
      right: 30px;
      background: #4CAF50;
      color: white;
      padding: 16px 24px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      z-index: 2000;
      animation: slideIn 0.3s ease;
    }

    @keyframes slideIn {
      from {
        transform: translateY(100px);
        opacity: 0;
      }
      to {
        transform: translateY(0);
        opacity: 1;
      }
    }

    .cdk-drag-preview {
      box-shadow: 0 8px 24px rgba(0,0,0,0.2);
      opacity: 0.9;
    }

    .cdk-drag-animating {
      transition: transform 250ms cubic-bezier(0, 0, 0.2, 1);
    }
  `]
})
export class SimpleSurveyBuilderComponent implements OnInit {
  @Input() surveyId?: number;
  @Input() inlineMode = false;
  @Output() closed = new EventEmitter<void>();

  questions: Question[] = [];
  showPreview = false;
  showToast = false;
  toastMessage = '';
  survey?: Survey;
  loading = false;

  constructor(
    private http: HttpClient,
    private route: ActivatedRoute,
    private router: Router,
    private surveysService: SurveysService,
    private authService: AuthService
  ) {}

  ngOnInit() {
    // Get survey ID from route params or input
    if (!this.surveyId) {
      const id = this.route.snapshot.paramMap.get('id');
      if (id) {
        this.surveyId = parseInt(id);
      }
    }
    
    if (this.surveyId) {
      this.loadSurvey();
    } else {
      console.warn('No survey ID provided');
    }
  }

  addQuestion(type: Question['type']) {
    const id = `q${Date.now()}`;
    const question: Question = {
      id,
      type,
      question: '',
      choices: type === 'choice' ? ['', '', ''] : undefined,
      scores: type === 'choice' ? [0, 0, 0] : undefined,  // Initialize scores with 0
      baseScore: type !== 'choice' ? 0 : undefined  // Base score for non-choice questions
    };
    this.questions.push(question);
  }

  deleteQuestion(index: number) {
    if (confirm('Delete this question?')) {
      this.questions.splice(index, 1);
    }
  }

  addChoice(questionIndex: number) {
    if (!this.questions[questionIndex].choices) {
      this.questions[questionIndex].choices = [];
    }
    if (!this.questions[questionIndex].scores) {
      this.questions[questionIndex].scores = [];
    }
    this.questions[questionIndex].choices!.push('');
    this.questions[questionIndex].scores!.push(0);  // Default score is 0
  }

  removeChoice(questionIndex: number, choiceIndex: number) {
    this.questions[questionIndex].choices!.splice(choiceIndex, 1);
    this.questions[questionIndex].scores!.splice(choiceIndex, 1);  // Remove corresponding score
  }

  trackByIndex(index: number): number {
    return index;
  }

  drop(event: CdkDragDrop<Question[]>) {
    moveItemInArray(this.questions, event.previousIndex, event.currentIndex);
  }

  getTypeLabel(type: string): string {
    const labels: Record<string, string> = {
      'contact': 'Contact',
      'choice': 'Multiple Choice',
      'text': 'Text',
      'email': 'Email',
      'phone': 'Phone'
    };
    return labels[type] || type;
  }

  togglePreview() {
    this.showPreview = !this.showPreview;
  }

  saveSurvey() {
    if (!this.surveyId) {
      this.showToastMessage('⚠️ No survey selected');
      return;
    }

    // Validate questions
    const validQuestions = this.questions.filter(q => q.question && q.question.trim());
    if (validQuestions.length === 0) {
      this.showToastMessage('⚠️ Please add at least one question!');
      return;
    }
    
    // Warn about empty questions
    const emptyQuestions = this.questions.filter(q => !q.question || !q.question.trim());
    if (emptyQuestions.length > 0) {
      if (!confirm(`${emptyQuestions.length} empty questions will be skipped. Continue?`)) {
        return;
      }
    }
    
    // Convert to flow format
    const flow = this.convertToFlow();
    
    // Save to backend via surveys API
    this.loading = true;
    this.surveysService.updateSurvey(this.surveyId, {
      flow_json: flow
    }).subscribe({
      next: () => {
        this.loading = false;
        const user = this.authService.getCurrentUser();
        const orgSlug = user?.organization_slug || 'demo-agency';
        const url = this.survey?.slug ? `http://localhost:4200/${orgSlug}/${this.survey.slug}?t=${Date.now()}` : '';
        this.showToastMessage(`✅ Saved! Test at: ${url}`);
      },
      error: (err) => {
        console.error('Save error:', err);
        this.loading = false;
        this.showToastMessage('⚠️ Failed to save: ' + (err.error?.detail || 'Unknown error'));
      }
    });
  }

  loadSurvey() {
    if (!this.surveyId) return;

    this.loading = true;
    this.surveysService.getSurvey(this.surveyId).subscribe({
      next: (survey) => {
        this.survey = survey;
        this.loading = false;
        
        // Load flow if it exists
        if (survey.flow_json) {
          this.questions = this.convertFromFlow(survey.flow_json);
        } else {
          // Empty survey - start fresh
          this.questions = [];
        }
      },
      error: (err) => {
        console.error('Load error:', err);
        this.loading = false;
        this.showToastMessage('⚠️ Failed to load survey');
      }
    });
  }

  private convertToFlow() {
    // Filter out empty questions
    const validQuestions = this.questions.filter(q => q.question && q.question.trim());
    
    if (validQuestions.length === 0) {
      console.warn('No valid questions to save');
      return {
        version: '1.0.0',
        start: 'default',
        nodes: [
          {
            id: 'default',
            texts: ['Hvala za obisk! Prosimo izpolnite kontakt.'],
            openInput: true,
            inputType: 'dual-contact'
          }
        ]
      };
    }
    
    const nodes = validQuestions.map((q, i) => {
      const node: any = {
        id: q.id,
        texts: [q.question]
      };

      if (q.type === 'choice') {
        const validChoices = q.choices?.filter(c => c && c.trim()) || [];
        // Map choices with their scores
        node.choices = validChoices.map((c, idx) => {
          const originalIdx = q.choices!.indexOf(c);
          return {
            title: c,
            score: q.scores?.[originalIdx] ?? 0,  // Include score in flow
            next: i < validQuestions.length - 1 ? validQuestions[i + 1].id : undefined
          };
        });
      } else {
        node.openInput = true;
        node.inputType = q.type === 'contact' ? 'dual-contact' : q.type;
        node.score = q.baseScore ?? 0;  // Include base score for open questions
        node.next = i < validQuestions.length - 1 ? validQuestions[i + 1].id : undefined;
      }

      return node;
    });

    return {
      version: '1.0.0',
      start: validQuestions[0]?.id,
      nodes
    };
  }

  private convertFromFlow(flow: any): Question[] {
    if (!flow.nodes) return [];
    
    return flow.nodes.map((node: any) => ({
      id: node.id,
      type: node.choices ? 'choice' : (node.inputType === 'dual-contact' ? 'contact' : node.inputType || 'text'),
      question: node.texts?.[0] || '',
      choices: node.choices?.map((c: any) => c.title),
      scores: node.choices?.map((c: any) => c.score ?? 0),  // Load scores from flow
      baseScore: node.score ?? 0  // Load base score for non-choice questions
    }));
  }

  private showToastMessage(message: string) {
    this.toastMessage = message;
    this.showToast = true;
    setTimeout(() => this.showToast = false, 3000);
  }

  openPreview() {
    if (!this.survey) return;
    const user = this.authService.getCurrentUser();
    const orgSlug = user?.organization_slug || 'demo-agency';
    const url = `http://localhost:4200/${orgSlug}/${this.survey.slug}?t=${Date.now()}`;
    window.open(url, 'ace_chatbot_preview');
    this.showToastMessage('👀 Opening chatbot preview...');
  }

  goBack() {
    if (this.inlineMode) {
      this.closed.emit();
    } else {
      const user = this.authService.getCurrentUser();
      const orgSlug = user?.organization_slug || 'demo-agency';
      this.router.navigate([`/${orgSlug}/surveys`]);
    }
  }
}
