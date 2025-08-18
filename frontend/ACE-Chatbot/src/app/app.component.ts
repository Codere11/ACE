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

    // Push user message
    this.messages.push({ role: 'user', text });

    // Immediately show assistant typing animation
    this.startTyping();

    this.loading = true;

    this.http.post<ChatResponse>('http://localhost:8000/chat', { message: text, sid: this.sid })
      .subscribe({
        next: res => this.consume(res),
        error: err => {
          console.error(err);
          this.loading = false;
          this.stopTyping("⚠️ Error talking to server.");
        }
      });
  }

  clickQuickReply(q: any) {
    this.send(q.title);
  }

  private consume(res: ChatResponse) {
    this.loading = false;

    // Replace typing with real reply
    if (res.reply) {
      this.stopTyping(res.reply);
    }

    // Handle UI blocks
    if (res.ui) {
      this.ui = res.ui;
    } else if (res.quickReplies) {
      this.ui = { type: 'choices', buttons: res.quickReplies };
    } else {
      this.ui = null;
    }

    // Always respect backend chatMode
    this.chatMode = res.chatMode;

    console.log("UI block received:", this.ui);
    console.log("Chat mode received:", this.chatMode);
  }

  private startTyping() {
    // Prevent duplicates
    if (!this.isTypingActive()) {
      this.messages.push({ role: 'assistant', typing: true });
    }
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

  private isTypingActive(): boolean {
    const last = this.messages[this.messages.length - 1];
    return !!(last && last.typing);
  }
}
