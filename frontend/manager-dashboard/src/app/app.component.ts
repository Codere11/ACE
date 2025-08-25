import { Component, OnInit, Inject, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { DashboardService, Lead, KPIs, Funnel, ChatLog } from './services/dashboard.service';
import { NotesTableComponent } from './notes-table/notes-table.component';

const SELECT_KEY = 'ace_notes_selected_lead_sid';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, HttpClientModule, FormsModule, NotesTableComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {
  activeTab: 'leads' | 'notes' | 'flow' | 'chats' = 'leads';

  rankedLeads: Lead[] = [];
  kpis: KPIs | null = null;
  funnel: Funnel | null = null;
  objections: string[] = [];
  chats: ChatLog[] = [];

  hoveredLead: string | null = null;
  leadChats: { [sid: string]: ChatLog[] } = {};

  loadingLeads = true;
  loadingKPIs = true;
  loadingFunnel = true;
  loadingObjections = true;
  loadingChats = true;

  selectedLeadSid: string = '';

  takeoverOpen = false;
  takeoverLead: Lead | null = null;
  takeoverLoading = false;

  takeoverInput = '';

  constructor(
    private dashboardService: DashboardService,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {
    if (isPlatformBrowser(this.platformId)) {
      this.selectedLeadSid = localStorage.getItem(SELECT_KEY) || '';
    }
  }

  ngOnInit() {
    if (isPlatformBrowser(this.platformId)) {
      this.fetchLeads();
      this.fetchKPIs();
      this.fetchFunnel();
      this.fetchObjections();
      this.fetchChats();

      setInterval(() => {
        this.fetchLeads();
        this.fetchKPIs();
      }, 10000);
    }
  }

  // ---------- data ----------
  fetchLeads() {
    this.loadingLeads = true;
    this.dashboardService.getLeads().subscribe({
      next: data => {
        this.rankedLeads = data.sort((a, b) => b.score - a.score);
        const exists = this.rankedLeads.some(l => l.id === this.selectedLeadSid);
        if (!exists) {
          this.selectedLeadSid = this.rankedLeads.length ? this.rankedLeads[0].id : '';
          if (this.selectedLeadSid) localStorage.setItem(SELECT_KEY, this.selectedLeadSid);
          else localStorage.removeItem(SELECT_KEY);
        }
        this.loadingLeads = false;
      },
      error: () => (this.loadingLeads = false),
    });
  }

  fetchKPIs() {
    this.loadingKPIs = true;
    this.dashboardService.getKPIs().subscribe({
      next: data => { this.kpis = data; this.loadingKPIs = false; },
      error: () => (this.loadingKPIs = false),
    });
  }

  fetchFunnel() {
    this.loadingFunnel = true;
    this.dashboardService.getFunnel().subscribe({
      next: data => { this.funnel = data; this.loadingFunnel = false; },
      error: () => (this.loadingFunnel = false),
    });
  }

  fetchObjections() {
    this.loadingObjections = true;
    this.dashboardService.getObjections().subscribe({
      next: data => { this.objections = data; this.loadingObjections = false; },
      error: () => (this.loadingObjections = false),
    });
  }

  fetchChats() {
    this.loadingChats = true;
    this.dashboardService.getChats().subscribe({
      next: data => { this.chats = data; this.loadingChats = false; },
      error: () => (this.loadingChats = false),
    });
  }

  loadChatsForLead(sid: string) {
    if (!this.leadChats[sid]) {
      this.dashboardService.getChatsForLead(sid).subscribe({
        next: data => { this.leadChats[sid] = data; },
        error: () => {},
      });
    }
  }

  // ---------- ui ----------
  selectLeadSid(sid: string) {
    this.selectedLeadSid = sid || '';
    if (this.selectedLeadSid) localStorage.setItem(SELECT_KEY, this.selectedLeadSid);
    else localStorage.removeItem(SELECT_KEY);
  }

  takeOver(lead: Lead) {
    this.takeoverLead = lead;
    this.takeoverOpen = true;

    if (!this.leadChats[lead.id]) {
      this.takeoverLoading = true;
      this.dashboardService.getChatsForLead(lead.id).subscribe({
        next: data => {
          this.leadChats[lead.id] = data;
          this.takeoverLoading = false;
          this.scrollTakeoverToBottomSoon();
        },
        error: () => { this.takeoverLoading = false; }
      });
    } else {
      this.scrollTakeoverToBottomSoon();
    }
  }

  closeTakeover() {
    this.takeoverOpen = false;
  }

  /** Append locally + force a new array ref so Angular always re-renders. */
  sendInlineMessage() {
    const text = (this.takeoverInput || '').trim();
    if (!text || !this.takeoverLead) return;

    const sid = this.takeoverLead.id;
    const existing = this.leadChats[sid] || [];
    const appended: ChatLog[] = [
      ...existing,
      { sid, role: 'user', text, timestamp: Math.floor(Date.now() / 1000) }
    ];

    // immutable bump ensures change detection
    this.leadChats = { ...this.leadChats, [sid]: appended };

    // reflect on card immediately
    this.takeoverLead = { ...this.takeoverLead, lastMessage: text, lastSeenSec: Math.floor(Date.now() / 1000) };

    this.takeoverInput = '';
    this.scrollTakeoverToBottomSoon();
  }

  handleInlineKeydown(ev: KeyboardEvent) {
    if (ev.key === 'Enter' && !ev.shiftKey) {
      ev.preventDefault();
      this.sendInlineMessage();
    }
  }

  trackByIdx(i: number, _m: ChatLog) { return i; }

  private scrollTakeoverToBottomSoon() {
    if (!isPlatformBrowser(this.platformId)) return;
    setTimeout(() => {
      const el = document.getElementById('takeover-body');
      if (el) el.scrollTop = el.scrollHeight;
    }, 0);
  }

  formatAgo(timestamp: number): string {
    const seconds = Math.floor(Date.now() / 1000) - timestamp;
    if (seconds < 60) return `pred ${seconds}s`;
    const m = Math.floor(seconds / 60);
    return m === 1 ? 'pred 1 min' : `pred ${m} min`;
  }
}
