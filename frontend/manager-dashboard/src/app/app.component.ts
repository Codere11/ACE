import { Component, OnInit, OnDestroy, Inject, PLATFORM_ID, ViewChild, ElementRef } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';

import { DashboardService, Lead, KPIs, Funnel, ChatLog } from './services/dashboard.service';
import { AuthService } from './services/auth.service';
import { NotesTableComponent } from './notes-table/notes-table.component';
import { LiveEventsService, ChatEvent } from './services/live-events.service';
import { Subscription } from 'rxjs';
import { Router } from '@angular/router';
// ✅ Flow Designer
import { SimpleSurveyBuilderComponent } from './simple-survey-builder/simple-survey-builder.component';
import { SurveyAnswersComponent } from './survey-answers/survey-answers.component';
import { SurveyListComponent } from './surveys/survey-list.component';

const SELECT_KEY = 'ace_notes_selected_lead_sid';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    HttpClientModule,
    FormsModule,
    RouterModule,
    NotesTableComponent,
    SurveyAnswersComponent,
    SurveyListComponent
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit, OnDestroy {
  private LOG = true; // flip to false to silence logs

  activeTab: 'leads' | 'notes' | 'flow' | 'chats' = 'leads';

  // --- Logos + menu ---
  clientLogoUrl = '/assets/client-logo.png';
  agentLogoUrl = '/assets/agent-avatar.png';
  agentMenuOpen = false;

  rankedLeads: Lead[] = [];
  displayedLeads: Lead[] = [];

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

  // live events
  private liveSub?: Subscription;
  private pollTimer?: any;

  // per-SID human mode: if true, suppress assistant messages on dashboard
  private humanMode: Record<string, boolean> = {};

  interestFilter: 'All' | 'High' | 'Medium' | 'Low' = 'All';
  minScore = 0;
  maxScore = 100;
  mustHavePhone = false;
  mustHaveEmail = false;
  dateFrom: string = '';
  dateTo: string = '';
  searchName: string = '';

  // ✅ NEW: local flow state for designer (no backend yet)
  flowData: any = null;
  private readonly LS_FLOW = 'ace_flow_designer_json';
  

  currentUser: any = null;
  uploadingAvatar = false;
  
  @ViewChild('avatarInput') avatarInput?: ElementRef<HTMLInputElement>;

  constructor(
    private dashboardService: DashboardService,
    private live: LiveEventsService,
    private authService: AuthService,
    private router: Router,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {
    if (isPlatformBrowser(this.platformId)) {
      this.selectedLeadSid = localStorage.getItem(SELECT_KEY) || '';
      // load last saved flow json for designer
      try {
        const raw = localStorage.getItem(this.LS_FLOW);
        if (raw) this.flowData = JSON.parse(raw);
      } catch { this.flowData = null; }
    }
  }

  ngOnInit() {
    if (!isPlatformBrowser(this.platformId)) return;

    // GLOBAL CLICK TEST
    if (isPlatformBrowser(this.platformId)) {
      window.addEventListener('click', (e: any) => {
        console.log('GLOBAL CLICK DETECTED:', e.target);
        if (e.target.classList?.contains('upload-btn')) {
          console.log('!!!!! UPLOAD BUTTON WAS CLICKED !!!!!');
        }
      });
    }

    // Subscribe to current user
    this.authService.currentUser$.subscribe(user => {
      this.currentUser = user;
    });

    // Initial fetches (canonical state on load)
    this.fetchLeads();
    this.fetchKPIs();
    this.fetchFunnel();
    this.fetchObjections();
    this.fetchChats();

    // NO periodic polling - rely entirely on live events for updates

    // Live long-poll: cross-SID lead + message events
    this.live.startAll();
    this.liveSub = this.live.events$.subscribe((evt: ChatEvent | null) => {
      if (!evt) return;
      this.handleLiveEvent(evt);
    });
  }

  ngOnDestroy() {
    if (!isPlatformBrowser(this.platformId)) return;
    this.liveSub?.unsubscribe();
    this.live.stop();
    if (this.pollTimer) clearInterval(this.pollTimer);
  }

  // -------- Logger --------
  private log(...args: any[]) {
    if (this.LOG) console.log('[ACE-DASH]', ...args);
  }

  // -------- Live events handler --------
  private handleLiveEvent(evt: ChatEvent) {
    try {
      const { type, sid, payload } = evt;

      // A) Lead row updates
      if (type === 'lead.touched') {
        const idx = this.rankedLeads.findIndex(l => l.id === sid);
        if (idx >= 0) {
          const lead = { ...this.rankedLeads[idx] };
          if (payload?.lastMessage != null) lead.lastMessage = payload.lastMessage;
          if (payload?.lastSeenSec != null) lead.lastSeenSec = payload.lastSeenSec;
          this.rankedLeads = [
            ...this.rankedLeads.slice(0, idx),
            lead,
            ...this.rankedLeads.slice(idx + 1),
          ];
          this.applyFilters();
          this.log('live: lead.touched applied', sid);
        } else {
          this.log('live: lead.touched for unknown sid -> refetch leads', sid);
          this.fetchLeads();
        }
      }

      if (type === 'lead.notes' || type === 'lead.ai_summary') {
        const idx = this.rankedLeads.findIndex(l => l.id === sid);
        if (idx >= 0) {
          const lead = { ...this.rankedLeads[idx] };
          if (type === 'lead.notes' && payload?.notes != null) {
            lead.notes = payload.notes;
          } else if (type === 'lead.ai_summary') {
            const pitch = payload?.pitch ?? '';
            if (pitch) {
              lead.notes = (lead.notes ? `${lead.notes} | ` : '') + `AI:${pitch}`;
            }
          }
          this.rankedLeads = [
            ...this.rankedLeads.slice(0, idx),
            lead,
            ...this.rankedLeads.slice(idx + 1),
          ];
          this.applyFilters();
          this.log('live:', type, 'applied', sid);
        } else {
          this.log('live:', type, 'for unknown sid -> refetch leads', sid);
          this.fetchLeads();
        }
      }

      // Survey progress updates - calculate score in real-time
      if (type === 'survey.progress' || type === 'survey.completed') {
        this.log('live: survey event', type, sid, payload);
        const idx = this.rankedLeads.findIndex(l => l.id === sid);
        if (idx >= 0) {
          const lead = { ...this.rankedLeads[idx] };
          // Update score from event payload
          if (payload?.score != null) {
            lead.score = payload.score;
          }
          if (payload?.interest != null) {
            lead.interest = payload.interest;
          }
          if (payload?.progress != null) {
            lead.survey_progress = payload.progress;
          }
          this.rankedLeads = [
            ...this.rankedLeads.slice(0, idx),
            lead,
            ...this.rankedLeads.slice(idx + 1),
          ];
          // Re-sort by score
          this.rankedLeads.sort((a, b) => b.score - a.score);
          this.applyFilters();
          this.log('live: survey score updated', sid, lead.score);
        } else {
          this.log('live: survey event for unknown sid -> refetch leads', sid);
          this.fetchLeads();
        }
        return;
      }

      // B) Message bubbles + update lead.lastMessage
      if (type === 'message.created') {
        const role = (payload?.role as ChatLog['role']) ?? 'assistant';
        const text = payload?.text ?? '';
        const timestamp = payload?.timestamp ?? Math.floor(Date.now() / 1000);

        if (role === 'staff') {
          this.humanMode[sid] = true;
          this.log('live: human mode ON for sid', sid);
        }

        if (role === 'assistant' && this.humanMode[sid]) {
          this.log('live: suppress assistant (human mode) sid', sid);
        } else {
          const existing = this.leadChats[sid];
          if (existing) {
            const append: ChatLog = { sid, role, text, timestamp };
            this.leadChats[sid] = [...existing, append];

            setTimeout(() => {
              if (this.takeoverOpen && this.takeoverLead?.id === sid) {
                const el = document.getElementById('takeover-body');
                if (el) el.scrollTop = el.scrollHeight;
              }
            }, 0);

            if (this.activeTab === 'chats') this.fetchChats();
            this.log('live: message.created appended', sid, role);
          } else {
            this.log('live: message.created (thread not loaded yet)', sid);
          }
        }

        const li = this.rankedLeads.findIndex(l => l.id === sid);
        if (li >= 0) {
          const lead = { ...this.rankedLeads[li] };
          lead.lastMessage = text;
          lead.lastSeenSec = timestamp;
          this.rankedLeads = [
            ...this.rankedLeads.slice(0, li),
            lead,
            ...this.rankedLeads.slice(li + 1),
          ];
          this.applyFilters();
          this.log('live: lead.lastMessage updated from message.created', sid);
        }
      }
    } catch (e) {
      this.log('live: handler error', e);
    }
  }


  // -------- Data fetchers --------
  fetchLeads() {
    this.loadingLeads = true;
    this.log('fetchLeads()');
    this.dashboardService.getLeads().subscribe({
      next: data => {
        const prevSel = this.selectedLeadSid;
        
        // Just use scores from backend directly
        this.rankedLeads = data.sort((a, b) => b.score - a.score);
        this.log('fetchLeads ok ->', this.rankedLeads.length);

        const exists = this.rankedLeads.some(l => l.id === prevSel);
        if (!exists) {
          this.selectedLeadSid = this.rankedLeads.length ? this.rankedLeads[0].id : '';
          if (this.selectedLeadSid) localStorage.setItem(SELECT_KEY, this.selectedLeadSid);
          else localStorage.removeItem(SELECT_KEY);
        } else {
          this.selectedLeadSid = prevSel;
        }

        this.loadingLeads = false;
        this.applyFilters();
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

  onMinScoreChange(val: number) {
    this.minScore = Math.max(0, Math.min(100, Number(val)));
    if (this.minScore > this.maxScore) this.maxScore = this.minScore;
  }

  onMaxScoreChange(val: number) {
    this.maxScore = Math.max(0, Math.min(100, Number(val)));
    if (this.maxScore < this.minScore) this.minScore = this.maxScore;
  }

  // -------- Visible thread for takeover --------
  getVisibleThread(sid: string): ChatLog[] {
    return this.leadChats[sid] || [];
  }


  // -------- UI helpers --------
  selectLeadSid(sid: string) {
    this.selectedLeadSid = sid || '';
    if (this.selectedLeadSid) localStorage.setItem(SELECT_KEY, this.selectedLeadSid);
    else localStorage.removeItem(SELECT_KEY);
    this.log('selectLeadSid', this.selectedLeadSid);
    if (this.selectedLeadSid) this.loadChatsForLead(this.selectedLeadSid, false);
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

    this.humanMode[sid] = true;

    const now = Math.floor(Date.now() / 1000);

    const optimistic: ChatLog = {
      sid,
      role: 'staff',
      text,
      timestamp: now,
    };
    this.leadChats[sid] = [...(this.leadChats[sid] || []), optimistic];

    const li = this.rankedLeads.findIndex(l => l.id === sid);
    if (li >= 0) {
      const lead = { ...this.rankedLeads[li] };
      lead.lastMessage = text;
      lead.lastSeenSec = now;
      this.rankedLeads = [
        ...this.rankedLeads.slice(0, li),
        lead,
        ...this.rankedLeads.slice(li + 1),
      ];
      this.applyFilters();
      this.log('optimistic: lead.lastMessage updated from staff send', sid);
    }

    this.dashboardService.sendStaffMessage(sid, text).subscribe({
      next: res => {
        this.log('sendStaffMessage ok', res);
        this.takeoverInput = '';
        this.takeoverSending = false;
        this.loadChatsForLead(sid, true);
        this.fetchChats();
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
  
  formatDate(dateStr: string | null): string {
    if (!dateStr) return '';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('sl-SI', { day: '2-digit', month: '2-digit', year: 'numeric' });
    } catch {
      return '';
    }
  }
  
  translateInterest(interest: string): string {
    const translations: Record<string, string> = {
      'High': 'Visok',
      'Medium': 'Srednji',
      'Low': 'Nizek'
    };
    return translations[interest] || interest;
  }

  // -------- FILTERING --------
  applyFilters() {
    let list = [...this.rankedLeads];

    if (this.interestFilter !== 'All') {
      list = list.filter(l => (l.interest || '') === this.interestFilter);
    }

    list = list.filter(l => {
      const s = l.score || 0;
      return s >= this.minScore && s <= this.maxScore;
    });

    if (this.mustHavePhone) list = list.filter(l => !!l.phone);
    if (this.mustHaveEmail) list = list.filter(l => !!l.email);

    if (this.dateFrom) {
      const from = Math.floor(new Date(this.dateFrom).getTime() / 1000);
      list = list.filter(l => (l.lastSeenSec || 0) >= from);
    }
    if (this.dateTo) {
      const to = Math.floor(new Date(this.dateTo).getTime() / 1000) + 86400; // inclusive
      list = list.filter(l => (l.lastSeenSec || 0) <= to);
    }

    if ((this.searchName || '').trim()) {
      const q = this.searchName.toLowerCase();
      list = list.filter(l => (l.name || '').toLowerCase().includes(q));
    }

    this.displayedLeads = list.sort((a, b) => b.score - a.score);
  }

  // -------- Logo fallbacks --------
  onClientLogoError(e: Event) {
    (e.target as HTMLImageElement).src =
      'data:image/svg+xml;charset=UTF-8,' +
      encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44"><rect width="44" height="44" rx="22" fill="#161b22"/><text x="50%" y="54%" text-anchor="middle" font-family="Arial" font-size="14" fill="#8b949e">Logo</text></svg>');
  }
  onAgentLogoError(e: Event) {
    (e.target as HTMLImageElement).src =
      'data:image/svg+xml;charset=UTF-8,' +
      encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="44" height="44"><rect width="44" height="44" rx="22" fill="#161b22"/><text x="50%" y="54%" text-anchor="middle" font-family="Arial" font-size="14" fill="#8b949e">Me</text></svg>');
  }
  onChangeAccount() { this.log('Change Account clicked'); }
  onLogout() {
    this.log('Logging out');
    this.authService.logout();
  }

  onClickChangeAvatar(event: Event): void {
    event.stopPropagation();
    event.preventDefault();
    this.log('Change Avatar button clicked');
    
    // Use ViewChild reference to trigger file input
    if (this.avatarInput?.nativeElement) {
      this.log('Opening file dialog via ViewChild...');
      this.avatarInput.nativeElement.click();
    } else {
      console.error('ERROR: avatarInput ViewChild not available!');
      alert('ERROR: Could not access file input element');
    }
  }

  onAvatarUpload(event: Event): void {
    this.log('onAvatarUpload triggered');
    const input = event.target as HTMLInputElement;
    
    if (!input.files || input.files.length === 0) {
      this.log('No files selected');
      return;
    }

    const file = input.files[0];
    this.log('File selected:', file.name, file.type, file.size);
    
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file');
      return;
    }

    this.uploadingAvatar = true;
    this.authService.uploadAvatar(file).subscribe({
      next: (response) => {
        this.log('Avatar uploaded successfully:', response);
        // Refresh current user to get new avatar_url
        this.authService.validateToken();
        this.uploadingAvatar = false;
        // Keep menu open after upload
        setTimeout(() => this.agentMenuOpen = true, 100);
      },
      error: (err) => {
        console.error('[ACE-DASH] Avatar upload failed:', err);
        alert('Failed to upload avatar: ' + (err.error?.detail || err.message));
        this.uploadingAvatar = false;
      }
    });

    // Reset input so the same file can be selected again
    input.value = '';
  }

  // ✅ Flow Designer change hook (for future backend integration)
  onFlowChange(newFlow: any) {
    try { localStorage.setItem(this.LS_FLOW, JSON.stringify(newFlow)); } catch {}
  }

  onFlowTabClick() {
    this.activeTab = 'flow';
    const orgSlug = this.currentUser?.organization_slug || 'demo-agency';
    this.router.navigate([`/${orgSlug}/surveys`]);
  }

  goToSurveys() {
    const orgSlug = this.currentUser?.organization_slug || 'demo-agency';
    this.router.navigate([`/${orgSlug}/surveys`]);
  }

  deleteLead(lead: Lead, event: Event) {
    event.stopPropagation();
    
    if (!confirm(`Ali ste prepričani, da želite izbrisati lead "${lead.name}"?`)) {
      return;
    }

    this.log('Deleting lead:', lead.id);
    this.dashboardService.deleteLead(lead.id).subscribe({
      next: (response) => {
        this.log('Lead deleted successfully:', response);
        // Remove from local arrays
        this.rankedLeads = this.rankedLeads.filter(l => l.id !== lead.id);
        this.applyFilters();
        // Refresh data
        this.fetchLeads();
        this.fetchKPIs();
      },
      error: (err) => {
        console.error('Failed to delete lead:', err);
        alert('Failed to delete lead: ' + (err.error?.message || err.message));
      }
    });
  }
}
