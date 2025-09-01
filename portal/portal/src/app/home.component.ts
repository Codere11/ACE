import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService, User } from './auth/services/auth.service';
import { environment } from '../environments/environment';
import { FormsModule } from '@angular/forms';

type Customer = {
  slug: string;
  display_name?: string;
  last_paid?: string | null;
  contact?: { name?: string; email?: string; phone?: string };
  users?: string[];
  chatbot_url: string;
};

type ListedUser = { username: string; role: 'admin'|'manager'; tenant_slug?: string|null };

@Component({
  standalone: true,
  selector: 'app-home',
  imports: [CommonModule, FormsModule],
  template: `
  <div class="list" *ngIf="role() === 'admin'">
    <h2>Stranke</h2>

    <div class="item" *ngFor="let c of customers()">
      <div class="flex">
        <div>
          <div><b>{{c.display_name || c.slug}}</b> <small style="opacity:.7">({{c.slug}})</small></div>
          <div style="opacity:.7">Zadnje plačilo: {{c.last_paid || '—'}}</div>
          <div style="opacity:.8">Uporabniki: {{ (c.users || []).join(', ') || '—' }}</div>
          <div><a [href]="c.chatbot_url" target="_blank">Odpri chatbot</a></div>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;margin-top:10px">
        <label>Poslovno ime
          <input [value]="editCache()[c.slug]?.display_name ?? c.display_name ?? ''"
                 (input)="onCache(c.slug,'display_name',$any($event.target).value)">
        </label>
        <label>Kontakt ime
          <input [value]="editCache()[c.slug]?.contact?.name ?? c.contact?.name ?? ''"
                 (input)="onCacheContact(c.slug,'name',$any($event.target).value)">
        </label>
        <label>Email
          <input [value]="editCache()[c.slug]?.contact?.email ?? c.contact?.email ?? ''"
                 (input)="onCacheContact(c.slug,'email',$any($event.target).value)">
        </label>
        <label>Telefon
          <input [value]="editCache()[c.slug]?.contact?.phone ?? c.contact?.phone ?? ''"
                 (input)="onCacheContact(c.slug,'phone',$any($event.target).value)">
        </label>
        <label>Zadnje plačilo (YYYY-MM-DD)
          <input [value]="editCache()[c.slug]?.last_paid ?? c.last_paid ?? ''"
                 (input)="onCache(c.slug,'last_paid',$any($event.target).value)">
        </label>
      </div>
      <div style="margin-top:8px;display:flex;gap:8px">
        <button (click)="saveProfile(c.slug)">Shrani profil</button>
        <button (click)="resetProfile(c.slug)">Prekliči</button>
      </div>
    </div>

    <h2 style="margin-top:24px">Uporabniški računi</h2>
    <div class="item">
      <h3 style="margin-top:0">Dodaj novega</h3>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px">
        <input placeholder="username" [(ngModel)]="newUser.username">
        <input placeholder="password" [(ngModel)]="newUser.password" type="password">
        <select [(ngModel)]="newUser.role">
          <option value="manager">manager</option>
          <option value="admin">admin</option>
        </select>
        <select [(ngModel)]="newUser.tenant_slug">
          <option [ngValue]="null">— brez —</option>
          <option *ngFor="let c of customers()" [ngValue]="c.slug">{{c.slug}}</option>
        </select>
        <button (click)="createUser()">Ustvari</button>
      </div>
    </div>

    <div class="item" *ngFor="let u of users()">
      <div class="flex">
        <div><b>{{u.username}}</b> <small style="opacity:.7">({{u.role}})</small></div>
        <div *ngIf="u.username!=='admin'">
          <button (click)="deleteUser(u.username)">Izbriši</button>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px;margin-top:8px">
        <input placeholder="new password (optional)" [(ngModel)]="userEdits[u.username].password">
        <select [(ngModel)]="userEdits[u.username].role">
          <option value="manager">manager</option>
          <option value="admin">admin</option>
        </select>
        <select [(ngModel)]="userEdits[u.username].tenant_slug">
          <option [ngValue]="null">— brez —</option>
          <option *ngFor="let c of customers()" [ngValue]="c.slug">{{c.slug}}</option>
        </select>
        <button (click)="updateUser(u.username)">Posodobi</button>
      </div>
    </div>
  </div>

  <div class="card" *ngIf="role() === 'manager'">
    <h2>Menedžerska nadzorna plošča</h2>
    <p>Ta pogled je namenjen adminu. Trenutno vloga: <b>manager</b>.</p>
  </div>
  `,
  styles: [`
    input, select, button { width:100%; padding:10px; border-radius:10px; border:1px solid #333; background:#1d1d1d; color:#eee }
    button { border:0; background:#4f46e5; cursor:pointer }
    h3 { margin: 0 0 10px 0 }
  `]
})
export class HomeComponent implements OnInit {
  role = signal<'admin'|'manager'>('manager');
  customers = signal<Customer[]>([]);
  users = signal<ListedUser[]>([]);
  editCache = signal<Record<string, any>>({});
  userEdits: Record<string, { password?: string; role: 'admin'|'manager'; tenant_slug: string|null }> = {};
  newUser: { username: string; password: string; role: 'admin'|'manager'; tenant_slug: string|null } = {
    username: '', password: '', role: 'manager', tenant_slug: null
  };

  private get token() { return this.auth.user?.token ?? ''; }
  private get headers() {
    return { 'Authorization': `Bearer ${this.token}`, 'Content-Type': 'application/json' };
  }

  constructor(private auth: AuthService) {}

  ngOnInit() {
    const u = this.auth.user as User | null;
    if (!u) return;
    this.role.set(u.role);
    if (u.role === 'admin') {
      this.loadAll();
    } else {
      // manager view later
    }
  }

  // ------------ data loading
  private async loadAll() {
    await Promise.all([this.loadCustomers(), this.loadUsers()]);
    // Init userEdits
    const map: Record<string, { password?: string; role: 'admin'|'manager'; tenant_slug: string|null }> = {};
    this.users().forEach(u => { map[u.username] = { role: u.role, tenant_slug: (u.tenant_slug ?? null) }; });
    this.userEdits = map;
  }

  private async loadCustomers() {
    const r = await fetch(`${environment.apiBase}/api/admin/customers`, { headers: { 'Authorization': `Bearer ${this.token}` } });
    if (!r.ok) return;
    const j = await r.json();
    this.customers.set(j.customers || []);
  }

  private async loadUsers() {
    const r = await fetch(`${environment.apiBase}/api/admin/users`, { headers: { 'Authorization': `Bearer ${this.token}` } });
    if (!r.ok) return;
    const j = await r.json();
    this.users.set(j.users || []);
  }

  // ------------ profile editing cache
  onCache(slug: string, key: string, value: any) {
    const copy = { ...this.editCache() };
    copy[slug] = { ...(copy[slug] || {}), [key]: value };
    this.editCache.set(copy);
  }
  onCacheContact(slug: string, key: 'name'|'email'|'phone', value: any) {
    const copy = { ...this.editCache() };
    const cur = copy[slug] || {};
    copy[slug] = { ...cur, contact: { ...(cur.contact || {}), [key]: value } };
    this.editCache.set(copy);
  }
  resetProfile(slug: string) {
    const copy = { ...this.editCache() }; delete copy[slug]; this.editCache.set(copy);
  }
  async saveProfile(slug: string) {
    const patch = this.editCache()[slug];
    if (!patch) return;
    const r = await fetch(`${environment.apiBase}/api/admin/customers/${slug}/profile`, {
      method: 'PATCH',
      headers: this.headers,
      body: JSON.stringify(patch)
    });
    if (r.ok) {
      await this.loadCustomers();
      this.resetProfile(slug);
    } else {
      console.error('Save profile failed', await r.text());
    }
  }

  // ------------ users CRUD
  async createUser() {
    const body = { ...this.newUser };
    const r = await fetch(`${environment.apiBase}/api/admin/users`, {
      method: 'POST', headers: this.headers, body: JSON.stringify(body)
    });
    if (r.ok) {
      this.newUser = { username: '', password: '', role: 'manager', tenant_slug: null };
      await this.loadUsers();
      await this.loadCustomers();
    } else {
      const t = await r.text();
      alert('Create failed: ' + t);
    }
  }

  async updateUser(username: string) {
    const body = this.userEdits[username];
    if (!body) return;
    const r = await fetch(`${environment.apiBase}/api/admin/users/${encodeURIComponent(username)}`, {
      method: 'PATCH', headers: this.headers, body: JSON.stringify(body)
    });
    if (r.ok) {
      // Clear password field after update
      this.userEdits[username].password = '';
      await this.loadUsers();
      await this.loadCustomers();
    } else {
      const t = await r.text();
      alert('Update failed: ' + t);
    }
  }

  async deleteUser(username: string) {
    if (!confirm(`Izbrišem uporabnika ${username}?`)) return;
    const r = await fetch(`${environment.apiBase}/api/admin/users/${encodeURIComponent(username)}`, {
      method: 'DELETE', headers: this.headers
    });
    if (r.ok) {
      await this.loadUsers();
      await this.loadCustomers();
    } else {
      const t = await r.text();
      alert('Delete failed: ' + t);
    }
  }
}
