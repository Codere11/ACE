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
  private hoverTimer: any = null;

  leadChats: { [sid: string]: ChatLog[] } = {};
  takeoverOpen = false;
  takeoverLead: Lead | null = null;
  takeoverLoading = false;
  takeoverInput = '';
  takeoverSending = false;

  loadingLeads = true;
  loadingKPIs = true;
  loadingFunnel = true;
  loadingObjections = true;
  loadingChats = true;

  selectedLeadSid: string = '';

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

  // -------- Data fetchers --------
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

  loadChatsForLead(sid: string, force = false) {
    if (!force && this.leadChats[sid]) return;
    this.dashboardService.getChatsForLead(sid).subscribe({
      next: data => { this.leadChats[sid] = data; },
      error: () => {},
    });
  }

  // -------- UI helpers --------
  selectLeadSid(sid: string) {
    this.selectedLeadSid = sid || '';
    if (this.selectedLeadSid) localStorage.setItem(SELECT_KEY, this.selectedLeadSid);
    else localStorage.removeItem(SELECT_KEY);
  }

  onLeadHover(sid: string) {
    this.hoveredLead = sid;
    clearTimeout(this.hoverTimer);
    this.hoverTimer = setTimeout(() => this.loadChatsForLead(sid, false), 150);
  }
  onLeadLeave() {
    clearTimeout(this.hoverTimer);
    this.hoveredLead = null;
  }

  openTakeover(lead: Lead) {
    this.takeoverLead = lead;
    this.takeoverOpen = true;
    this.takeoverLoading = true;
    this.loadChatsForLead(lead.id, true);
    // light delay just for spinner feel
    setTimeout(() => (this.takeoverLoading = false), 150);
  }

  closeTakeover() {
    this.takeoverOpen = false;
    this.takeoverLead = null;
    this.takeoverInput = '';
    this.takeoverSending = false;
  }

  // -------- Staff send (dashboard) --------
  sendStaffMessage() {
    if (!this.takeoverLead) return;
    const sid = this.takeoverLead.id;
    const text = (this.takeoverInput || '').trim();
    if (!text) return;

    this.takeoverSending = true;

    // Optimistic append so it appears instantly
    const optimistic: ChatLog = {
      sid,
      role: 'staff',
      text,
      timestamp: Math.floor(Date.now() / 1000),
    };
    this.leadChats[sid] = [...(this.leadChats[sid] || []), optimistic];

    this.dashboardService.sendStaffMessage(sid, text).subscribe({
      next: _ => {
        this.takeoverInput = '';
        this.takeoverSending = false;
        // Force-refresh from server to stay canonical
        this.loadChatsForLead(sid, true);
        // scroll takeover body to bottom
        setTimeout(() => {
          const el = document.getElementById('takeover-body');
          if (el) el.scrollTop = el.scrollHeight;
        }, 0);
      },
      error: _ => {
        // On error, remove optimistic or mark failed (minimal: just keep it)
        this.takeoverSending = false;
      }
    });
  }

  formatAgo(timestamp: number): string {
    const seconds = Math.floor(Date.now() / 1000) - timestamp;
    if (seconds < 60) return `pred ${seconds}s`;
    const m = Math.floor(seconds / 60);
    return m === 1 ? 'pred 1 min' : `pred ${m} min`;
  }
}
