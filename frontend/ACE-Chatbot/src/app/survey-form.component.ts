import { Component, OnInit, OnDestroy, OnChanges, SimpleChanges, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Subscription } from 'rxjs';

interface FlowNode {
  id: string;
  texts?: string[];
  text?: string;
  choices?: { title: string; next?: string; action?: string; payload?: any }[];
  openInput?: boolean;
  inputType?: 'single' | 'dual-contact' | 'contact' | 'email' | 'phone';
  action?: string;
  next?: string;
  terminal?: boolean;
}

interface SurveyFlow {
  nodes: FlowNode[];
  start?: string;
}

@Component({
  selector: 'app-survey-form',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="survey-container" *ngIf="!isCompleted">
      <!-- Progress Bar -->
      <div class="survey-progress">
        <div class="progress-bar">
          <div class="progress-fill" [style.width.%]="progressPercentage"></div>
        </div>
        <div class="progress-text">Vprašanje {{ currentIndex + 1 }} od {{ totalSteps }}</div>
      </div>

      <!-- Current Question -->
      <div class="survey-question" *ngIf="currentNode">
        <h3 class="question-title">{{ getQuestionText() }}</h3>

        <!-- Multiple Choice -->
        <div class="choices-container" *ngIf="currentNode.choices && currentNode.choices.length > 0">
          <button 
            *ngFor="let choice of currentNode.choices; let i = index"
            class="choice-button"
            [class.selected]="selectedChoice === i"
            (click)="selectChoice(i, choice)"
            type="button">
            {{ choice.title }}
          </button>
        </div>

        <!-- Open Input -->
        <div class="input-container" *ngIf="currentNode.openInput">
          <!-- Dual Contact -->
          <div *ngIf="currentNode.inputType === 'dual-contact'" class="dual-contact-form">
            <div class="form-group">
              <label for="contact-email">E-pošta</label>
              <input 
                id="contact-email"
                type="email" 
                [(ngModel)]="contactEmail" 
                placeholder="vas@email.com"
                class="form-input">
            </div>
            <div class="form-group">
              <label for="contact-phone">Telefon</label>
              <input 
                id="contact-phone"
                type="tel" 
                [(ngModel)]="contactPhone" 
                placeholder="+386 ..."
                class="form-input">
            </div>
            <p class="form-hint">Vnesite vsaj eno kontaktno informacijo</p>
          </div>

          <!-- Single Text Input -->
          <div *ngIf="currentNode.inputType === 'single'" class="single-input-form">
            <textarea 
              [(ngModel)]="textAnswer" 
              placeholder="Vnesite vaš odgovor..."
              rows="4"
              class="form-textarea"></textarea>
          </div>

          <!-- Email Input -->
          <div *ngIf="currentNode.inputType === 'email'" class="single-input-form">
            <input 
              type="email" 
              [(ngModel)]="textAnswer" 
              placeholder="vas@email.com"
              class="form-input">
          </div>

          <!-- Phone Input -->
          <div *ngIf="currentNode.inputType === 'phone'" class="single-input-form">
            <input 
              type="tel" 
              [(ngModel)]="textAnswer" 
              placeholder="+386 ..."
              class="form-input">
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <div class="survey-navigation">
        <button 
          *ngIf="currentIndex > 0"
          (click)="goBack()"
          class="nav-button nav-back"
          type="button">
          ← Nazaj
        </button>
        <button 
          (click)="goNext()"
          [disabled]="!canProceed()"
          class="nav-button nav-next"
          type="button">
          {{ isLastStep() ? 'Zaključi' : 'Naprej →' }}
        </button>
      </div>

      <!-- Error Message -->
      <div class="error-message" *ngIf="errorMessage">
        {{ errorMessage }}
      </div>
    </div>

    <!-- Completion Message -->
    <div class="survey-completed" *ngIf="isCompleted">
      <div class="completion-icon">✅</div>
      <h2>Hvala za sodelovanje!</h2>
      <p>Vaše odgovore smo prejeli. Kmalu se oglasimo.</p>
    </div>
  `,
  styles: [`
    .survey-container {
      max-width: 600px;
      margin: 0 auto;
      padding: 24px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    .survey-progress {
      margin-bottom: 32px;
    }

    .progress-bar {
      width: 100%;
      height: 8px;
      background: #e5e7eb;
      border-radius: 4px;
      overflow: hidden;
      margin-bottom: 8px;
    }

    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #3b82f6, #8b5cf6);
      transition: width 0.3s ease;
    }

    .progress-text {
      text-align: center;
      font-size: 14px;
      color: #6b7280;
    }

    .survey-question {
      margin-bottom: 32px;
    }

    .question-title {
      font-size: 20px;
      font-weight: 600;
      color: #111827;
      margin-bottom: 24px;
      line-height: 1.4;
    }

    .choices-container {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .choice-button {
      padding: 16px 20px;
      border: 2px solid #e5e7eb;
      border-radius: 8px;
      background: white;
      font-size: 16px;
      color: #374151;
      cursor: pointer;
      transition: all 0.2s;
      text-align: left;
    }

    .choice-button:hover {
      border-color: #3b82f6;
      background: #eff6ff;
    }

    .choice-button.selected {
      border-color: #3b82f6;
      background: #dbeafe;
      color: #1e40af;
    }

    .input-container {
      margin-top: 16px;
    }

    .dual-contact-form {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .form-group label {
      font-size: 14px;
      font-weight: 500;
      color: #374151;
    }

    .form-input {
      padding: 12px 16px;
      border: 2px solid #e5e7eb;
      border-radius: 8px;
      font-size: 16px;
      transition: border-color 0.2s;
    }

    .form-input:focus {
      outline: none;
      border-color: #3b82f6;
    }

    .form-textarea {
      padding: 12px 16px;
      border: 2px solid #e5e7eb;
      border-radius: 8px;
      font-size: 16px;
      font-family: inherit;
      resize: vertical;
      transition: border-color 0.2s;
    }

    .form-textarea:focus {
      outline: none;
      border-color: #3b82f6;
    }

    .form-hint {
      font-size: 13px;
      color: #6b7280;
      margin-top: 4px;
    }

    .survey-navigation {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-top: 32px;
    }

    .nav-button {
      padding: 12px 24px;
      border: none;
      border-radius: 8px;
      font-size: 16px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }

    .nav-back {
      background: #f3f4f6;
      color: #374151;
    }

    .nav-back:hover {
      background: #e5e7eb;
    }

    .nav-next {
      background: #3b82f6;
      color: white;
      flex: 1;
    }

    .nav-next:hover:not(:disabled) {
      background: #2563eb;
    }

    .nav-next:disabled {
      background: #9ca3af;
      cursor: not-allowed;
    }

    .error-message {
      margin-top: 16px;
      padding: 12px 16px;
      background: #fee2e2;
      color: #991b1b;
      border-radius: 8px;
      font-size: 14px;
    }

    .survey-completed {
      max-width: 500px;
      margin: 0 auto;
      padding: 48px 24px;
      text-align: center;
    }

    .completion-icon {
      font-size: 64px;
      margin-bottom: 24px;
    }

    .survey-completed h2 {
      font-size: 28px;
      font-weight: 600;
      color: #111827;
      margin-bottom: 16px;
    }

    .survey-completed p {
      font-size: 16px;
      color: #6b7280;
    }
  `]
})
export class SurveyFormComponent implements OnInit, OnDestroy, OnChanges {
  @Input() flow: SurveyFlow | null = null;
  @Input() sid: string = '';
  @Input() backendUrl: string = 'http://localhost:8000';
  @Output() completed = new EventEmitter<void>();
  @Output() paused = new EventEmitter<void>();

  currentIndex = 0;
  currentNode: FlowNode | null = null;
  answers: Map<string, any> = new Map();
  history: string[] = [];
  
  // Form fields
  selectedChoice: number = -1;
  textAnswer: string = '';
  contactEmail: string = '';
  contactPhone: string = '';
  
  isCompleted = false;
  errorMessage: string = '';
  
  private eventSub?: Subscription;

  constructor(private http: HttpClient) {}

  ngOnInit() {
    console.log('=== SURVEY FORM INIT ==>');
    this.initializeFlow();
  }
  
  ngOnChanges(changes: SimpleChanges) {
    console.log('=== SURVEY FORM CHANGES ==>', changes);
    if (changes['flow'] && changes['flow'].currentValue) {
      console.log('Flow changed! New value:', changes['flow'].currentValue);
      // Only reinitialize if survey hasn't started yet (no answers)
      if (this.answers.size === 0) {
        console.log('Survey not started yet, reinitializing with new flow');
        this.initializeFlow();
      } else {
        console.log('Survey in progress, keeping current state (user has', this.answers.size, 'answers)');
        // Update flow but don't reset progress
        // The user will see new flow on next survey start
      }
    }
  }
  
  private initializeFlow() {
    console.log('initializeFlow() called');
    console.log('Flow object:', this.flow);
    console.log('Flow exists?', !!this.flow);
    console.log('Flow.nodes exists?', !!this.flow?.nodes);
    console.log('Flow.nodes length:', this.flow?.nodes?.length);
    console.log('Flow.start:', this.flow?.start);
    
    if (!this.flow || !this.flow.nodes || this.flow.nodes.length === 0) {
      console.error('Flow validation failed!');
      this.errorMessage = 'Napaka: Ni definiranega vprašalnika';
      return;
    }
    
    console.log('Flow validation passed, loading first node...');
    this.errorMessage = ''; // Clear any previous error
    this.loadFirstNode();
    console.log('Current node after load:', this.currentNode);
  }

  ngOnDestroy() {
    this.eventSub?.unsubscribe();
  }

  get progressPercentage(): number {
    if (!this.flow || !this.flow.nodes.length) return 0;
    return Math.round((this.answers.size / this.flow.nodes.length) * 100);
  }

  get totalSteps(): number {
    return this.flow?.nodes.length || 0;
  }

  private loadFirstNode() {
    const startId = this.flow?.start || this.flow?.nodes[0]?.id;
    const startNode = this.flow?.nodes.find(n => n.id === startId) || this.flow?.nodes[0];
    
    if (startNode) {
      this.currentNode = startNode;
      this.history = [startNode.id];
    }
  }

  getQuestionText(): string {
    if (!this.currentNode) return '';
    
    if (this.currentNode.texts && this.currentNode.texts.length > 0) {
      return this.currentNode.texts[0];
    }
    if (this.currentNode.text) {
      return this.currentNode.text;
    }
    return '';
  }

  selectChoice(index: number, choice: any) {
    this.selectedChoice = index;
    this.errorMessage = '';
  }

  canProceed(): boolean {
    if (!this.currentNode) return false;

    if (this.currentNode.choices && this.currentNode.choices.length > 0) {
      return this.selectedChoice >= 0;
    }

    if (this.currentNode.openInput) {
      if (this.currentNode.inputType === 'dual-contact') {
        return !!(this.contactEmail.trim() || this.contactPhone.trim());
      }
      return !!this.textAnswer.trim();
    }

    return true;
  }

  async goNext() {
    if (!this.canProceed() || !this.currentNode) return;

    // Collect answer
    let answer: any;
    if (this.currentNode.choices && this.selectedChoice >= 0) {
      const choice = this.currentNode.choices[this.selectedChoice];
      answer = choice.title;
      
      // Store any payload from choice
      if (choice.payload) {
        this.answers.set(`${this.currentNode.id}_payload`, choice.payload);
      }
    } else if (this.currentNode.openInput) {
      if (this.currentNode.inputType === 'dual-contact') {
        answer = {
          email: this.contactEmail.trim(),
          phone: this.contactPhone.trim()
        };
      } else {
        answer = this.textAnswer.trim();
      }
    }

    // Store answer
    this.answers.set(this.currentNode.id, answer);

    // Submit to backend
    try {
      await this.submitAnswer(this.currentNode.id, answer);
    } catch (error) {
      console.error('Submit error:', error);
      this.errorMessage = 'Napaka pri shranjevanju odgovora';
      return;
    }

    // Check if terminal node
    if (this.currentNode.terminal || this.isLastStep()) {
      this.isCompleted = true;
      this.completed.emit();
      return;
    }

    // Find next node
    let nextNodeId: string | undefined;
    if (this.currentNode.choices && this.selectedChoice >= 0) {
      nextNodeId = this.currentNode.choices[this.selectedChoice].next;
    } else {
      nextNodeId = this.currentNode.next;
    }

    if (nextNodeId) {
      const nextNode = this.flow?.nodes.find(n => n.id === nextNodeId);
      if (nextNode) {
        this.currentNode = nextNode;
        this.history.push(nextNode.id);
        this.currentIndex = this.history.length - 1;
        this.resetFormFields();
      } else {
        this.isCompleted = true;
        this.completed.emit();
      }
    } else {
      this.isCompleted = true;
      this.completed.emit();
    }
  }

  goBack() {
    if (this.history.length <= 1) return;

    this.history.pop();
    const prevNodeId = this.history[this.history.length - 1];
    const prevNode = this.flow?.nodes.find(n => n.id === prevNodeId);
    
    if (prevNode) {
      this.currentNode = prevNode;
      this.currentIndex = this.history.length - 1;
      
      // Restore previous answer if exists
      const prevAnswer = this.answers.get(prevNodeId);
      if (prevAnswer !== undefined) {
        if (typeof prevAnswer === 'object' && 'email' in prevAnswer) {
          this.contactEmail = prevAnswer.email || '';
          this.contactPhone = prevAnswer.phone || '';
        } else if (typeof prevAnswer === 'string') {
          this.textAnswer = prevAnswer;
        }
      }
      
      this.resetFormFields();
    }
  }

  isLastStep(): boolean {
    return this.currentIndex >= this.totalSteps - 1;
  }

  private resetFormFields() {
    this.selectedChoice = -1;
    this.textAnswer = '';
    // Don't reset contact fields as they're typically collected once
  }

  private async submitAnswer(nodeId: string, answer: any): Promise<void> {
    const progress = Math.round((this.answers.size / this.totalSteps) * 100);
    
    const payload = {
      sid: this.sid,
      node_id: nodeId,
      answer: answer,
      progress: progress,
      all_answers: Object.fromEntries(this.answers)
    };

    const response = await this.http.post<any>(
      `${this.backendUrl}/chat/survey/submit`,
      payload
    ).toPromise();

    if (response?.paused) {
      this.paused.emit();
    }
  }
}
