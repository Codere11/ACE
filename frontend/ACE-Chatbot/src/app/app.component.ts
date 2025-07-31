import { Component, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService } from './services/chat.service';

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
  imports: [CommonModule, FormsModule],
})
export class AppComponent implements AfterViewInit {
  messages: ChatMessage[] = [];
  userInput: string = '';
  typingDots: string = '.';
  typingInterval: any;

  @ViewChild('chatWindow') chatWindow!: ElementRef;

  constructor(private chatService: ChatService) {}

  ngAfterViewInit(): void {
    this.addBotMessage(`Pozdravljeni! 👋 Vidimo, da vas zanima več o apartmaju v središču Ljubljane.\n\nČe vas zanimajo podrobnosti, kot so:\n\n💰 cena,\n📐 kvadratura,\n📍 lokacija ali\n👀 ali je še na voljo,\n\nme kar vprašajte — tukaj sem, da pomagam! 😊`);
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

      console.log('🟩 Backend returned:', res); // ✅ LOG THIS

      this.messages.push({
        sender: 'bot',
        text: res.reply,
        imageUrl: res.imageUrl // 👈 CHECK THIS
      });

      this.scrollToBottom();
    },
    error: (err) => {
      clearInterval(this.typingInterval);
      this.messages.pop();
      this.addBotMessage('Prišlo je do napake. Poskusite znova.');
      this.scrollToBottom();
    }
  });
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
