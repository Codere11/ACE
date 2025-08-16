import { Component, OnInit } from '@angular/core';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

interface Message {
  role: 'user' | 'assistant';
  text?: string;
  typing?: boolean;
}

interface ChatResponse {
  reply?: string;
  quickReplies?: { title: string; payload: string }[];
  ui?: any;
  chatMode: 'guided' | 'open';
  storyComplete?: boolean;
  imageUrl?: string | null;
}

@Component({
  selector: 'app-root',
  standalone: true,
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  imports: [
    CommonModule,
    FormsModule,
    HttpClientModule
  ]
})
export class AppComponent implements OnInit {
  messages: Message[] = [];
  ui: any = null;
  chatMode: 'guided' | 'open' = 'guided';
  loading = false;
  sid = Math.random().toString(36).substring(2);

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.send('/start');
  }

  send(text: string) {
    if (!text.trim()) return;

    this.messages.push({ role: 'user', text });
    this.loading = true;

    this.http.post<ChatResponse>('http://localhost:8000/chat', { message: text, sid: this.sid })
      .subscribe({
        next: res => this.consume(res),
        error: err => {
          console.error(err);
          this.loading = false;
        }
      });
  }

  clickQuickReply(q: any) {
    this.send(q.payload);
  }

  private consume(res: ChatResponse) {
    this.loading = false;

    // 🔥 If DeepSeek should answer, show typing first
    if (res.storyComplete && res.reply) {
      this.startTyping();
      const wait = Math.max(900, res.reply.length * 30);
      setTimeout(() => {
        this.stopTyping(res.reply);
        this.ui = res.ui ?? null;
        this.chatMode = 'open'; // unlock typing after DeepSeek
      }, wait);
      return;
    }

    // Normal assistant reply
    if (res.reply) this.messages.push({ role: 'assistant', text: res.reply });

    // Handle UI blocks
    this.ui = res.ui ?? (res.quickReplies ? { type: 'choices', buttons: res.quickReplies } : null);

    // Unlock input only if Rasa explicitly asked for free text
    if (this.ui && this.ui.openInput) {
      this.chatMode = 'open';
    } else {
      this.chatMode = res.chatMode;
    }

    console.log("UI block received:", res.ui);
    console.log("Chat mode received:", this.chatMode);
  }

  private startTyping() {
    this.messages.push({ role: 'assistant', typing: true });
  }

  private stopTyping(replaceWith?: string) {
    const last = this.messages[this.messages.length - 1];
    if (last && last.typing) {
      this.messages.pop();
      if (replaceWith) {
        this.messages.push({ role: 'assistant', text: replaceWith });
      }
    }
  }
}
