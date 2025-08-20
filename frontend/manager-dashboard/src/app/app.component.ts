import { Component, OnInit, Inject, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import { DashboardService, Lead, KPIs, Funnel } from './services/dashboard.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, HttpClientModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {
  activeTab: 'leads' | 'notes' | 'flow' = 'leads';

  rankedLeads: Lead[] = [];
  kpis: KPIs | null = null;
  funnel: Funnel | null = null;
  objections: string[] = [];

  // loading flags
  loadingLeads = true;
  loadingKPIs = true;
  loadingFunnel = true;
  loadingObjections = true;

  constructor(
    private dashboardService: DashboardService,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}

  ngOnInit() {
    // ✅ Only run HTTP calls in browser, not during SSR
    if (isPlatformBrowser(this.platformId)) {
      this.fetchLeads();
      this.fetchKPIs();
      this.fetchFunnel();
      this.fetchObjections();

      setInterval(() => {
        this.fetchLeads();
        this.fetchKPIs();
      }, 10000);
    }
  }

  fetchLeads() {
    this.loadingLeads = true;
    this.dashboardService.getLeads().subscribe({
      next: data => {
        this.rankedLeads = data.sort((a, b) => b.score - a.score);
        this.loadingLeads = false;
      },
      error: () => this.loadingLeads = false
    });
  }

  fetchKPIs() {
    this.loadingKPIs = true;
    this.dashboardService.getKPIs().subscribe({
      next: data => {
        this.kpis = data;
        this.loadingKPIs = false;
      },
      error: () => this.loadingKPIs = false
    });
  }

  fetchFunnel() {
    this.loadingFunnel = true;
    this.dashboardService.getFunnel().subscribe({
      next: data => {
        this.funnel = data;
        this.loadingFunnel = false;
      },
      error: () => this.loadingFunnel = false
    });
  }

  fetchObjections() {
    this.loadingObjections = true;
    this.dashboardService.getObjections().subscribe({
      next: data => {
        this.objections = data;
        this.loadingObjections = false;
      },
      error: () => this.loadingObjections = false
    });
  }

  takeOver(lead: Lead) {
    alert(`Prevzem pogovora z: ${lead.name} (${lead.industry})`);
  }

  formatAgo(seconds: number): string {
    if (seconds < 60) return `pred ${seconds}s`;
    const m = Math.floor(seconds / 60);
    return m === 1 ? 'pred 1 min' : `pred ${m} min`;
  }
}
