// ✅ app.component.ts
import { Component, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService } from './services/chat.service';
import { MarkdownModule } from 'ngx-markdown';

interface ChatMessage {
  sender: 'user' | 'bot';
  text: string;
  imageUrl?: string;
  loading?: boolean;
}

@Component({
  selector: 'app-root',
  standalone: true,
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  imports: [CommonModule, FormsModule, MarkdownModule],
})
export class AppComponent implements AfterViewInit {
  messages: ChatMessage[] = [];
  userInput: string = '';
  typingDots: string = '.';
  typingInterval: any;

  @ViewChild('chatWindow') chatWindow!: ElementRef;

  constructor(private chatService: ChatService) {}

  ngAfterViewInit(): void {
    this.addBotMessage(`Pozdravljeni! Jaz sem Omsoft Ace, chatbot ki prodaja samega sebe! S cim se pa ti ukvarjas?`);
  }

  sendMessage(): void {
    const text = this.userInput.trim();
    if (!text) return;

    this.addUserMessage(text);
    this.userInput = '';
    this.scrollToBottom();

    const placeholder: ChatMessage = { sender: 'bot', text: '.', loading: true };
    this.messages.push(placeholder);
    this.scrollToBottom();

    this.typingDots = '.';
    this.typingInterval = setInterval(() => {
      this.typingDots = this.typingDots.length < 3 ? this.typingDots + '.' : '.';
      placeholder.text = this.typingDots;
    }, 400);

    this.chatService.sendMessage(text).subscribe({
      next: (res) => {
        clearInterval(this.typingInterval);
        this.messages.pop();
        this.simulateTyping(res.reply, res.imageUrl);
      },
      error: (err) => {
        clearInterval(this.typingInterval);
        this.messages.pop();
        this.addBotMessage('Prišlo je do napake. Poskusite znova.');
        this.scrollToBottom();
      }
    });
  }

  private simulateTyping(fullText: string, imageUrl?: string): void {
    const botMessage: ChatMessage = { sender: 'bot', text: '', imageUrl };
    this.messages.push(botMessage);
    this.scrollToBottom();

    let index = 0;
    const interval = setInterval(() => {
      botMessage.text = fullText.slice(0, index);
      index++;
      if (index > fullText.length) {
        clearInterval(interval);
        this.scrollToBottom();
      }
    }, 15);
  }

  private addUserMessage(text: string): void {
    this.messages.push({ sender: 'user', text });
  }

  private addBotMessage(text: string, imageUrl?: string): void {
    this.messages.push({ sender: 'bot', text, imageUrl });
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      this.chatWindow.nativeElement.scrollTop = this.chatWindow.nativeElement.scrollHeight;
    }, 100);
  }
}
