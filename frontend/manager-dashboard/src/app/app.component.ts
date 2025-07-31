import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

type Lead = {
  name: string;
  score: number;            // 0–100
  summary: string;          // one-liner e.g. "(do 380.000 €, ima psa)"
  lastMessage: string;      // latest user message
  budget: number;           // numeric, e.g. 380000
  location: string;         // e.g. "Ljubljana - Bežigrad"
  hasPet?: boolean;         // true if mentioned a dog/cat
  email?: boolean;          // provided email
  phone?: boolean;          // provided phone
  lastSeenSec: number;      // seconds ago
};

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {
  // KPIs
  visitors = 1875;
  interactions = 732;
  contacts = 223;
  viewings = 91;
  sales = 24;

  // CTRs
  googleCTR = 38.1;
  facebookCTR = 25.4;
  instagramCTR = 14.7;

  // Ranked leads (top to bottom)
  rankedLeads: Lead[] = [
    {
      name: 'Mateja K.',
      score: 95,
      summary: '(do 520.000 €; Ljubljana center)',
      lastMessage: 'Možen ogled že jutri popoldne?',
      budget: 520000,
      location: 'Ljubljana - Center',
      hasPet: false,
      email: true,
      phone: true,
      lastSeenSec: 25
    },
    {
      name: 'Denis L.',
      score: 89,
      summary: '(do 380.000 €; ima psa)',
      lastMessage: 'Iščem 2-sobno stanovanje z balkonom.',
      budget: 380000,
      location: 'Šiška',
      hasPet: true,
      email: false,
      phone: true,
      lastSeenSec: 55
    },
    {
      name: 'Tina B.',
      score: 84,
      summary: '(do 300.000 €; blizu OŠ)',
      lastMessage: 'Kakšni so mesečni stroški?',
      budget: 300000,
      location: 'Bežigrad',
      hasPet: false,
      email: true,
      phone: false,
      lastSeenSec: 120
    }
  ];

  

  ngOnInit() {
    // Simulate a new HOT lead appearing after 2 seconds
    setTimeout(() => {
      const newLead: Lead = {
        name: 'Urban C.',
        score: 98,
        summary: '(do 650.000 €; mirna lokacija)',
        lastMessage: 'Zanima me vila z večjim vrtom in bazenom.',
        budget: 650000,
        location: 'Rožna dolina',
        hasPet: false,
        email: true,
        phone: true,
        lastSeenSec: 8
      };
      this.addLead(newLead);
    }, 4000);

    // Simulate another strong lead after 5 seconds
    setTimeout(() => {
      const newLead: Lead = {
        name: 'Nika Z.',
        score: 97,
        summary: '(do 450.000 €; parkirno mesto)',
        lastMessage: 'Ali je apartma še na voljo? Želim ogled.',
        budget: 450000,
        location: 'Ljubljana - Prule',
        hasPet: false,
        email: true,
        phone: false,
        lastSeenSec: 6
      };
      this.addLead(newLead);
    }, 8000);
  }

  addLead(lead: Lead) {
    // Insert and keep list sorted by score desc
    this.rankedLeads.unshift(lead);
    this.rankedLeads.sort((a, b) => b.score - a.score);

    // Bump KPIs to simulate live growth
    this.visitors += Math.floor(3 + Math.random() * 7);
    this.interactions += 1;
    if (lead.email || lead.phone) this.contacts += 1;
  }

  takeOver(lead: Lead) {
    // Demo action: replace with real navigation or modal open
    alert(`Prevzem pogovora z: ${lead.name} (${lead.location})`);
  }

  formatAgo(seconds: number): string {
    if (seconds < 60) return `pred ${seconds}s`;
    const m = Math.floor(seconds / 60);
    return m === 1 ? 'pred 1 min' : `pred ${m} min`;
  }
}
