import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';

type Lead = {
  name: string;
  industry: string;
  score: number;
  stage: string;
  compatibility: boolean;
  interest: 'High' | 'Medium' | 'Low';
  phone: boolean;
  email: boolean;
  adsExp: boolean;
  lastMessage: string;
  lastSeenSec: number;
  notes: string;
};

type KPIs = {
  visitors: number;
  interactions: number;
  contacts: number;
  avgResponseSec: number;
  activeLeads: number;
};

type Funnel = {
  awareness: number;
  interest: number;
  meeting: number;
  close: number;
};

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, HttpClientModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {
  activeTab: 'leads' | 'notes' | 'flow' = 'leads';

  // Data containers
  rankedLeads: Lead[] = [];
  kpis: KPIs | null = null;
  funnel: Funnel | null = null;
  objections: string[] = [];

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.fetchLeads();
    this.fetchKPIs();
    this.fetchFunnel();
    this.fetchObjections();

    // optional: refresh data every 10s
    setInterval(() => {
      this.fetchLeads();
      this.fetchKPIs();
    }, 10000);
  }

  fetchLeads() {
    this.http.get<Lead[]>('http://localhost:8000/leads')
      .subscribe(data => {
        // sort descending by score
        this.rankedLeads = data.sort((a, b) => b.score - a.score);
      });
  }

  fetchKPIs() {
    this.http.get<KPIs>('http://localhost:8000/kpis')
      .subscribe(data => this.kpis = data);
  }

  fetchFunnel() {
    this.http.get<Funnel>('http://localhost:8000/funnel')
      .subscribe(data => this.funnel = data);
  }

  fetchObjections() {
    this.http.get<string[]>('http://localhost:8000/objections')
      .subscribe(data => this.objections = data);
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
