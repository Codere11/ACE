import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators, FormGroup } from '@angular/forms';
import { ChatService, ChatResponse, QuickReply, UIBlock, UIForm } from './services/chat.service';

type Msg = { role: 'user'|'assistant'; text: string; typing?: boolean; id?: string };

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {
  sid = `sid_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

  messages: Msg[] = [];
  ui: UIBlock = null;
  chatMode: 'guided'|'open' = 'guided';
  inputText = '';
  loading = false;

  surveyForm!: FormGroup;

  // typing indicator
  private typingId: string | null = null;
  private typingStartedAt = 0;
  private readonly MIN_TYPING_MS = 900;

  constructor(private fb: FormBuilder, private api: ChatService) {
    this.surveyForm = this.fb.group({
      industry: ['', Validators.required],
      budget: ['3k_10k', Validators.required],
      experience: ['', Validators.required],
    });
  }

  ngOnInit(): void {
    this.loading = true;
    this.api.chat(this.sid, '/start', true).subscribe({
      next: (res) => this.consume(res),
      error: () => (this.loading = false),
    });
  }

  private consume(res: ChatResponse) {
  this.loading = false;

  // append assistant reply for this turn
  if (res.reply) this.messages.push({ role: 'assistant', text: res.reply });

  // trust backend to tell us the UI block (choices or form)
  this.ui = res.ui ?? (res.quickReplies ? { type: 'choices', buttons: res.quickReplies } as any : null);
  
  // if backend says "openInput", force open mode
  if (this.ui && (this.ui as any).openInput) {
    this.chatMode = 'open';
  } else {
    this.chatMode = res.chatMode;
  }

  console.log("UI block received:", res.ui);
  console.log("Chat mode received:", this.chatMode);
}



  private startTyping() {
    this.stopTyping();
    this.typingId = `typing_${Date.now()}`;
    this.typingStartedAt = performance.now();
    this.messages.push({ role: 'assistant', text: '', typing: true, id: this.typingId });
  }

  private stopTyping(replaceWith?: string) {
    if (!this.typingId) return;
    const i = this.messages.findIndex(m => m.id === this.typingId);
    if (i > -1) {
      if (replaceWith !== undefined) {
        this.messages[i] = { role: 'assistant', text: replaceWith };
      } else {
        this.messages.splice(i, 1);
      }
    }
    this.typingId = null;
  }

  sendText() {
    if (!this.inputText.trim() || this.chatMode !== 'open' || this.loading) return;
    const msg = this.inputText.trim();
    this.messages.push({ role: 'user', text: msg });
    this.inputText = '';
    this.loading = true;
    this.api.chat(this.sid, msg).subscribe({
      next: (res) => this.consume(res),
      error: () => (this.loading = false),
    });
  }

  clickQuickReply(q: QuickReply) {
  if (this.loading) return;
  this.messages.push({ role: 'user', text: q.title });
  this.loading = true;
  this.api.chat(this.sid, q.payload).subscribe({
    next: (res) => this.consume(res),
    error: () => (this.loading = false),
  });
}

  submitSurvey() {
    if (this.loading) return;
    if (this.surveyForm.invalid) {
      this.surveyForm.markAllAsTouched();
      return;
    }
    const { industry, budget, experience } = this.surveyForm.value as any;
    this.messages.push({ role: 'user', text: `Submitted: ${industry} / ${budget} / ${experience}` });

    this.loading = true;
    this.startTyping();

    this.api.survey(this.sid, industry, budget, experience).subscribe({
      next: (res) => {
        const elapsed = performance.now() - this.typingStartedAt;
        const wait = Math.max(0, this.MIN_TYPING_MS - elapsed);
        setTimeout(() => {
          this.stopTyping(res.reply ?? '');
          // backend decides chatMode (guided/open) after DeepSeek
          this.ui = res.ui ?? null;
          this.chatMode = res.chatMode;
          this.loading = false;
        }, wait);
      },
      error: () => {
        const elapsed = performance.now() - this.typingStartedAt;
        const wait = Math.max(0, this.MIN_TYPING_MS - elapsed);
        setTimeout(() => {
          this.stopTyping('Sorry, something went wrong analyzing that.');
          this.loading = false;
        }, wait);
      },
    });
  }

  isForm(block: UIBlock): block is UIForm {
    return !!block && (block as any).type === 'form';
  }
}
