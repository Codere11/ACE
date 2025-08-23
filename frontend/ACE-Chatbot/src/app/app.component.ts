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
  imports: [CommonModule, FormsModule, HttpClientModule]
})
export class AppComponent implements OnInit {
  messages: Message[] = [];
  ui: any = null;
  chatMode: 'guided' | 'open' = 'guided';
  loading = false;
  sid = Math.random().toString(36).substring(2);

  // ✅ Keep it consistent everywhere
  backendUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.send('/start');
  }

  send(text: string) {
    if (!text.trim()) return;

    this.messages.push({ role: 'user', text });
    this.startTyping();
    this.loading = true;

    const isOpenInput = !!(this.ui && (this.ui.openInput === true));

    // ✅ Keep streaming for true open-chat (no openInput UI visible)
    if (this.chatMode === 'open' && !isOpenInput) {
      this.sendStream(text);
      return;
    }

    // ✅ CRITICAL: use /chat/ (trailing slash) to avoid 307 double-hit
    this.http.post<ChatResponse>(`${this.backendUrl}/chat/`, { message: text, sid: this.sid })
      .subscribe({
        next: res => this.consume(res),
        error: err => {
          console.error(err);
          this.loading = false;
          this.stopTyping("⚠️ Napaka pri komunikaciji s strežnikom.");
        }
      });
  }

  async sendStream(text: string) {
    try {
      // ✅ Streaming endpoint already has trailing slash — keep it
      const response = await fetch(`${this.backendUrl}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, sid: this.sid })
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      let decoder = new TextDecoder();
      let buffer = "";

      this.messages.pop();
      this.messages.push({ role: 'assistant', text: "" });

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        this.messages[this.messages.length - 1].text = buffer;
      }

      this.loading = false;
    } catch (err) {
      console.error(err);
      this.loading = false;
      this.stopTyping("⚠️ Napaka pri pretakanju odgovora.");
    }
  }

  // Single open input posts to /chat/ (NOT streamed)
  sendSingle(answer: string) {
    if (!answer.trim()) return;
    this.messages.push({ role: 'user', text: answer });
    this.startTyping();
    this.loading = true;

    // ✅ Trailing slash
    this.http.post<ChatResponse>(`${this.backendUrl}/chat/`, {
      sid: this.sid,
      message: answer
    }).subscribe({
      next: res => this.consume(res),
      error: err => {
        console.error(err);
        this.loading = false;
        this.stopTyping("⚠️ Napaka pri pošiljanju odgovora.");
      }
    });
  }

  // Dual open input → survey endpoint (no streaming)
  sendSurvey(ans1: string, ans2: string) {
    if (!ans1.trim() && !ans2.trim()) return;

    this.messages.push({ role: 'user', text: `Q1: ${ans1} | Q2: ${ans2}` });
    this.startTyping();
    this.loading = true;

    // You defined /chat/survey (no trailing slash in route), keep as-is if your backend is that way.
    // If your backend route is '/chat/survey' (no slash), do NOT add one here.
    this.http.post<ChatResponse>(`${this.backendUrl}/chat/survey`, {
      sid: this.sid,
      industry: '',
      budget: '',
      experience: '',
      question1: ans1,
      question2: ans2
    }).subscribe({
      next: res => this.consume(res),
      error: err => {
        console.error(err);
        this.loading = false;
        this.stopTyping("⚠️ Napaka pri pošiljanju ankete.");
      }
    });
  }

  onSubmitSingle(input: HTMLInputElement) {
    const v = input.value;
    if (!v.trim()) return;
    input.value = '';
    this.sendSingle(v);
  }

  onSubmitSurvey(i1: HTMLInputElement, i2: HTMLInputElement) {
    const a1 = i1.value;
    const a2 = i2.value;
    if (!a1.trim() && !a2.trim()) return;
    i1.value = ''; i2.value = '';
    this.sendSurvey(a1, a2);
  }

  clickQuickReply(q: any) {
    this.send(q.title);
  }

  private consume(res: ChatResponse) {
    this.loading = false;
    if (res.reply !== undefined) this.stopTyping(res.reply);

    if (res.ui) {
      this.ui = res.ui;
    } else if (res.quickReplies) {
      this.ui = { type: 'choices', buttons: res.quickReplies };
    } else {
      this.ui = null;
    }

    this.chatMode = res.chatMode;
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
      if (replaceWith !== undefined) {
        this.messages.push({ role: 'assistant', text: replaceWith });
      }
    }
  }

  private isTypingActive(): boolean {
    const last = this.messages[this.messages.length - 1];
    return !!(last && last.typing);
  }
}
