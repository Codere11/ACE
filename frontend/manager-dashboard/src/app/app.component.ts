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
  private LOG = true; // flip to false to silence logs

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

  // -------- Logger --------
  private log(...args: any[]) {
    if (this.LOG) console.log('[ACE-DASH]', ...args);
  }

  // -------- Data fetchers --------
  fetchLeads() {
    this.loadingLeads = true;
    this.log('fetchLeads()');
    this.dashboardService.getLeads().subscribe({
      next: data => {
        this.rankedLeads = data.sort((a, b) => b.score - a.score);
        this.log('fetchLeads ok ->', this.rankedLeads.length);

        const exists = this.rankedLeads.some(l => l.id === this.selectedLeadSid);
        if (!exists) {
          this.selectedLeadSid = this.rankedLeads.length ? this.rankedLeads[0].id : '';
          if (this.selectedLeadSid) localStorage.setItem(SELECT_KEY, this.selectedLeadSid);
          else localStorage.removeItem(SELECT_KEY);
        }

        this.loadingLeads = false;
      },
      error: (e) => { this.loadingLeads = false; this.log('fetchLeads err', e); },
    });
  }

  fetchKPIs() {
    this.loadingKPIs = true;
    this.log('fetchKPIs()');
    this.dashboardService.getKPIs().subscribe({
      next: data => { this.kpis = data; this.loadingKPIs = false; this.log('fetchKPIs ok', data); },
      error: (e) => { this.loadingKPIs = false; this.log('fetchKPIs err', e); },
    });
  }

  fetchFunnel() {
    this.loadingFunnel = true;
    this.log('fetchFunnel()');
    this.dashboardService.getFunnel().subscribe({
      next: data => { this.funnel = data; this.loadingFunnel = false; this.log('fetchFunnel ok', data); },
      error: (e) => { this.loadingFunnel = false; this.log('fetchFunnel err', e); },
    });
  }

  fetchObjections() {
    this.loadingObjections = true;
    this.log('fetchObjections()');
    this.dashboardService.getObjections().subscribe({
      next: data => { this.objections = data; this.loadingObjections = false; this.log('fetchObjections ok', data.length); },
      error: (e) => { this.loadingObjections = false; this.log('fetchObjections err', e); },
    });
  }

  fetchChats() {
    this.loadingChats = true;
    this.log('fetchChats()');
    this.dashboardService.getChats().subscribe({
      next: data => { this.chats = data; this.loadingChats = false; this.log('fetchChats ok', data.length); },
      error: (e) => { this.loadingChats = false; this.log('fetchChats err', e); },
    });
  }

  loadChatsForLead(sid: string, force = false) {
    if (!force && this.leadChats[sid]) return;
    this.log('loadChatsForLead()', sid, 'force=', force);
    this.dashboardService.getChatsForLead(sid).subscribe({
      next: data => {
        this.leadChats[sid] = data;
        this.log('loadChatsForLead ok', sid, 'count=', data.length);
        // Auto-scroll if takeover open for this sid
        setTimeout(() => {
          if (this.takeoverOpen && this.takeoverLead?.id === sid) {
            const el = document.getElementById('takeover-body');
            if (el) el.scrollTop = el.scrollHeight;
          }
        }, 0);
      },
      error: (e) => { this.log('loadChatsForLead err', sid, e); },
    });
  }

  // -------- UI helpers --------
  selectLeadSid(sid: string) {
    this.selectedLeadSid = sid || '';
    if (this.selectedLeadSid) localStorage.setItem(SELECT_KEY, this.selectedLeadSid);
    else localStorage.removeItem(SELECT_KEY);
    this.log('selectLeadSid', this.selectedLeadSid);
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
    this.log('openTakeover', lead.id);
    this.loadChatsForLead(lead.id, true);
    setTimeout(() => (this.takeoverLoading = false), 150);
  }

  closeTakeover() {
    this.log('closeTakeover');
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
    this.log('sendStaffMessage -> optimistic append', { sid, text });

    // Optimistic append
    const optimistic: ChatLog = {
      sid,
      role: 'staff',
      text,
      timestamp: Math.floor(Date.now() / 1000),
    };
    this.leadChats[sid] = [...(this.leadChats[sid] || []), optimistic];

    this.dashboardService.sendStaffMessage(sid, text).subscribe({
      next: res => {
        this.log('sendStaffMessage ok', res);
        this.takeoverInput = '';
        this.takeoverSending = false;
        // Force-refresh from server to stay canonical
        this.loadChatsForLead(sid, true);
        // Refresh global chats tab too (optional but helpful)
        this.fetchChats();
        // Scroll to bottom
        setTimeout(() => {
          const el = document.getElementById('takeover-body');
          if (el) el.scrollTop = el.scrollHeight;
        }, 0);
      },
      error: err => {
        this.log('sendStaffMessage err', err);
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
