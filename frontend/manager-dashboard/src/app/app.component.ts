import { Component, OnInit, OnDestroy, Inject, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { DashboardService, Lead, KPIs, Funnel, ChatLog } from './services/dashboard.service';
import { NotesTableComponent } from './notes-table/notes-table.component';
import { LiveEventsService, ChatEvent } from './services/live-events.service';
import { Subscription } from 'rxjs';

const SELECT_KEY = 'ace_notes_selected_lead_sid';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, HttpClientModule, FormsModule, NotesTableComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit, OnDestroy {
  private LOG = true; // flip to false to silence logs

  activeTab: 'leads' | 'notes' | 'flow' | 'chats' = 'leads';

  // --- Logos + menu (NEW) ---
  clientLogoUrl = '/assets/client-logo.png';
  agentLogoUrl = '/assets/agent-avatar.png';
  agentMenuOpen = false;

  rankedLeads: Lead[] = [];
  // list shown after filters/search (NEW)
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

  // ➕ NEW: per-SID "fresh takeover" window start (unix seconds)
  private takeoverSince: Record<string, number> = {};

  // ➕ NEW: per-SID toggle for showing full history in takeover
  showFullHistoryBySid: Record<string, boolean> = {};

  interestFilter: 'All' | 'High' | 'Medium' | 'Low' = 'All';
  minScore = 0;
  maxScore = 100;  // NEW
  mustHavePhone = false;
  mustHaveEmail = false;
  dateFrom: string = '';
  dateTo: string = '';
  searchName: string = '';

  // ------- TAGS state (NEW) -------
  aiTags: string[] = ['money', 'ready'];
  newTag = '';

  constructor(
    private dashboardService: DashboardService,
    private live: LiveEventsService,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {
    if (isPlatformBrowser(this.platformId)) {
      this.selectedLeadSid = localStorage.getItem(SELECT_KEY) || '';
    }
  }

  ngOnInit() {
    if (!isPlatformBrowser(this.platformId)) return;

    // Initial fetches (canonical state on load)
    this.fetchLeads();
    this.fetchKPIs();
    this.fetchFunnel();
    this.fetchObjections();
    this.fetchChats();

    // Periodic refresh (kept for safety / reconciliation)
    this.pollTimer = setInterval(() => {
      this.fetchLeads();
      this.fetchKPIs();
    }, 10000);

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

      // A) Lead row updates (fast path, no full refetch)
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
          this.applyFilters(); // keep displayed list in sync
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

      // B) Message bubbles + update lead.lastMessage for selected takeover lead
      if (type === 'message.created') {
        const role = (payload?.role as ChatLog['role']) ?? 'assistant';
        const text = payload?.text ?? '';
        const timestamp = payload?.timestamp ?? Math.floor(Date.now() / 1000);

        // If staff spoke (from any tab/agent), enter human mode for this SID
        if (role === 'staff') {
          this.humanMode[sid] = true;
          this.log('live: human mode ON for sid', sid);
        }

        // 🔕 Suppress assistant messages while human mode is on for this SID (UI only)
        if (role === 'assistant' && this.humanMode[sid]) {
          this.log('live: suppress assistant (human mode) sid', sid);
        } else {
          // Append only if we already have the thread in memory; otherwise load later on demand
          const existing = this.leadChats[sid];
          if (existing) {
            const append: ChatLog = { sid, role, text, timestamp };
            this.leadChats[sid] = [...existing, append];

            // auto-scroll if the takeover is open for this sid
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

        // ✅ ALWAYS update the lead row's "lastMessage" + seen time for ANY role
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
        this.applyFilters(); // ensure displayedLeads is set
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

  onMinScoreChange(val: number) {
    this.minScore = Math.max(0, Math.min(100, Number(val)));
    if (this.minScore > this.maxScore) this.maxScore = this.minScore;
  }

  onMaxScoreChange(val: number) {
    this.maxScore = Math.max(0, Math.min(100, Number(val)));
    if (this.maxScore < this.minScore) this.minScore = this.maxScore;
  }


  // -------- NEW: visible thread for takeover (filtered) --------
  getVisibleThread(sid: string): ChatLog[] {
    const all = this.leadChats[sid] || [];
    if (this.showFullHistoryBySid[sid]) return all;
    const since = this.takeoverSince[sid] || 0;
    if (!since) return all; // fallback if not set
    return all.filter(m => (m.timestamp || 0) >= since);
  }

  // -------- UI helpers --------
  selectLeadSid(sid: string) {
    this.selectedLeadSid = sid || '';
    if (this.selectedLeadSid) localStorage.setItem(SELECT_KEY, this.selectedLeadSid);
    else localStorage.removeItem(SELECT_KEY);
    this.log('selectLeadSid', this.selectedLeadSid);
    // Preload the selected thread for instant live appends
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

    // ➕ mark fresh takeover start (unix seconds) for this SID
    this.takeoverSince[lead.id] = Math.floor(Date.now() / 1000);
    // default to "fresh only" view
    this.showFullHistoryBySid[lead.id] = false;

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

    // Mark human mode immediately for this SID (suppresses bot live events)
    this.humanMode[sid] = true;

    const now = Math.floor(Date.now() / 1000);

    // Optimistic append to thread
    const optimistic: ChatLog = {
      sid,
      role: 'staff',
      text,
      timestamp: now,
    };
    this.leadChats[sid] = [...(this.leadChats[sid] || []), optimistic];

    // Optimistically update the lead row "lastMessage" + "lastSeenSec"
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

  // -------- NEW: toggle helpers --------
  showAllHistory() {
    if (!this.takeoverLead) return;
    this.showFullHistoryBySid[this.takeoverLead.id] = true;
    setTimeout(() => {
      const el = document.getElementById('takeover-body');
      if (el) el.scrollTop = el.scrollHeight;
    }, 0);
  }
  showOnlySinceTakeover() {
    if (!this.takeoverLead) return;
    this.showFullHistoryBySid[this.takeoverLead.id] = false;
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

  onHistoryToggle(checked: boolean) {
    if (!this.takeoverLead) return;
    this.showFullHistoryBySid[this.takeoverLead.id] = checked;
    // keep scroll at bottom after switching views
    setTimeout(() => {
      const el = document.getElementById('takeover-body');
      if (el) el.scrollTop = el.scrollHeight;
    }, 0);
  }

  // -------- FILTERING (NEW) --------
  applyFilters() {
  let list = [...this.rankedLeads];

  if (this.interestFilter !== 'All') {
    list = list.filter(l => (l.interest || '') === this.interestFilter);
  }

  // NEW: between minScore and maxScore (inclusive)
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


  // -------- TAGS controls (NEW) --------
  addTag() {
    const t = (this.newTag || '').trim();
    if (!t) return;
    if (!this.aiTags.includes(t)) this.aiTags = [...this.aiTags, t];
    this.newTag = '';
  }
  removeTag(i: number) {
    this.aiTags = this.aiTags.filter((_, idx) => idx !== i);
  }

  // -------- Logo fallbacks (NEW) --------
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
  onLogout() { this.log('Logout clicked'); }
}
