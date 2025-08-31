import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { AuthService } from './auth/services/auth.service';

@Component({
  standalone: true,
  selector: 'app-home',
  imports: [CommonModule],
  template: `
  <div class="list" *ngIf="role==='admin'">
    <h2>Stranke</h2>
    <div class="item flex" *ngFor="let c of customers">
      <div>
        <div><b>{{c.display_name}}</b> <small style="opacity:.7">({{c.slug}})</small></div>
        <div style="opacity:.7">Zadnje plačilo: {{c.last_paid || '—'}}</div>
        <div style="opacity:.8">
          Kontakt: {{c.contact?.name || '—'}} · {{c.contact?.email || '—'}} · {{c.contact?.phone || '—'}}
        </div>
      </div>
      <div>
        <a [href]="c.chatbot_url" target="_blank">Odpri chatbot</a>
      </div>
    </div>
  </div>

  <div class="card" *ngIf="role==='manager'">
    <h2>Menedžerska nadzorna plošča</h2>
    <p>Instanca: <b>{{my?.display_name}}</b> <small style="opacity:.7">({{my?.slug}})</small></p>
    <p><a [href]="my?.chatbot_url" target="_blank">Odpri chatbot</a></p>
    <p style="opacity:.8">Urejanje obrazcev in analitika bosta tu (naslednji koraki).</p>
  </div>
  `
})
export class HomeComponent implements OnInit {
  role: 'admin'|'manager' = 'manager';
  customers: any[] = [];
  my: any;

  constructor(private http: HttpClient, private auth: AuthService) {}

  ngOnInit() {
    const u = this.auth.user!;
    this.role = u.role;
    if (u.role === 'admin') {
      this.http.get<{customers:any[]}>('/api/admin/customers').subscribe(r => this.customers = r.customers);
    } else {
      this.http.get<any>('/api/manager/my-instance').subscribe(r => this.my = r);
    }
  }
}
