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
  // 🔥 Use the human-readable title (what backend expects now)
  this.send(q.title);
}

  private consume(res: ChatResponse) {
    this.loading = false;

    // ✅ DeepSeek final step: show typing
    if (res.storyComplete && res.reply) {
      this.startTyping();
      const wait = Math.max(900, res.reply.length * 30);
      setTimeout(() => {
        this.stopTyping(res.reply);
        this.ui = res.ui ?? null;
        this.chatMode = 'open';
      }, wait);
      return;
    }

    // Normal reply
    if (res.reply) this.messages.push({ role: 'assistant', text: res.reply });

    // Handle UI blocks
    if (res.ui) {
      this.ui = res.ui;
    } else if (res.quickReplies) {
      this.ui = { type: 'choices', buttons: res.quickReplies };
    } else {
      this.ui = null;
    }

    // ✅ Respect backend chatMode always
    this.chatMode = res.chatMode;

    console.log("UI block received:", this.ui);
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
