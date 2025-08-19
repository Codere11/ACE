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

  backendUrl = 'http://localhost:8000'; // 👈 replace with your backend IP

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.send('/start');
  }

  send(text: string) {
    if (!text.trim()) return;

    // Push user message
    this.messages.push({ role: 'user', text });

    // Show typing animation for bot
    this.startTyping();
    this.loading = true;

    // 🚀 Decide: stream or normal
    if (this.chatMode === 'open') {
      this.sendStream(text);
      return;
    }

    // Default: normal POST
    this.http.post<ChatResponse>(`${this.backendUrl}/chat`, { message: text, sid: this.sid })
      .subscribe({
        next: res => this.consume(res),
        error: err => {
          console.error(err);
          this.loading = false;
          this.stopTyping("⚠️ Error talking to server.");
        }
      });
  }

  async sendStream(text: string) {
    try {
      const response = await fetch(`${this.backendUrl}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, sid: this.sid })
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      let decoder = new TextDecoder();
      let buffer = "";

      // Replace typing with an empty assistant bubble
      this.messages.pop();
      this.messages.push({ role: 'assistant', text: "" });

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Update last assistant message with streamed text
        this.messages[this.messages.length - 1].text = buffer;
      }

      this.loading = false;
    } catch (err) {
      console.error(err);
      this.loading = false;
      this.stopTyping("⚠️ Error streaming from server.");
    }
  }

  sendDual(ans1: string, ans2: string) {
  if (!ans1.trim() && !ans2.trim()) return;

  // Combine both answers into a single message for backend
  const combined = `Kako pridobivate stranke: ${ans1} | Kdo odgovarja leadom: ${ans2}`;
  this.send(combined);
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
