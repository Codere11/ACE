import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService, User } from './auth/services/auth.service';
import { environment } from '../environments/environment';

type Customer = {
  slug: string;
  display_name?: string;
  last_paid?: string | null;
  contact?: { name?: string; email?: string; phone?: string };
  users?: string[];
  chatbot_url: string;
};

type ListedUser = { username: string; role: 'admin'|'manager'; tenant_slug?: string|null };

type ProfileForm = {
  display_name: string;
  last_paid: string;
  contact: { name: string; email: string; phone: string };
};

@Component({
  standalone: true,
  selector: 'app-home',
  imports: [CommonModule, FormsModule],
  template: `
  <div class="list" *ngIf="role() === 'admin'">
    <h2>Dodaj novo stranko</h2>
    <div class="item">
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px">
        <input placeholder="slug (npr. my-agency)" [(ngModel)]="newCustomer.slug">
        <input placeholder="Poslovno ime" [(ngModel)]="newCustomer.display_name">
        <input placeholder="Kontakt ime" [(ngModel)]="newCustomer.contact.name">
        <input placeholder="Email" [(ngModel)]="newCustomer.contact.email">
        <input placeholder="Telefon" [(ngModel)]="newCustomer.contact.phone">
        <input placeholder="Zadnje plačilo (YYYY-MM-DD)" [(ngModel)]="newCustomer.last_paid">
      </div>
      <div style="margin-top:10px"><b>Ustvari tudi uporabnika (opcijsko)</b></div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px">
        <input placeholder="username" [(ngModel)]="newCustomer.create_user.username">
        <input placeholder="password" type="password" [(ngModel)]="newCustomer.create_user.password">
        <select [(ngModel)]="newCustomer.create_user.role">
          <option value="manager">manager</option>
          <option value="admin">admin</option>
        </select>
      </div>
      <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">
        <button (click)="createCustomer()">Ustvari stranko</button>
        <button class="secondary" (click)="cancelNewCustomer()">Prekliči</button>
      </div>
    </div>

    <h2 style="margin-top:24px">Stranke</h2>

    <div class="item" *ngFor="let c of customers(); trackBy: trackBySlug">
      <div class="flex">
        <div>
          <div><b>{{c.display_name || c.slug}}</b> <small style="opacity:.7">({{c.slug}})</small></div>
          <div style="opacity:.7">Zadnje plačilo: {{c.last_paid || '—'}}</div>
          <div style="opacity:.8">Uporabniki: {{ (c.users || []).join(', ') || '—' }}</div>
          <div><a [href]="c.chatbot_url" target="_blank">Odpri chatbot</a></div>
        </div>
        <div style="display:flex;gap:8px">
          <button class="danger" (click)="deleteCustomer(c.slug)">Izbriši stranko</button>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;margin-top:10px">
        <label>Poslovno ime
          <input [(ngModel)]="profileForms[c.slug].display_name">
        </label>
        <label>Kontakt ime
          <input [(ngModel)]="profileForms[c.slug].contact.name">
        </label>
        <label>Email
          <input [(ngModel)]="profileForms[c.slug].contact.email">
        </label>
        <label>Telefon
          <input [(ngModel)]="profileForms[c.slug].contact.phone">
        </label>
        <label>Zadnje plačilo (YYYY-MM-DD)
          <input [(ngModel)]="profileForms[c.slug].last_paid">
        </label>
      </div>
      <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">
        <button (click)="saveProfile(c.slug)">Shrani profil</button>
        <button class="secondary" (click)="cancelProfile(c.slug)">Prekliči</button>
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
        <button class="secondary" (click)="cancelCreateUser()">Prekliči</button>
      </div>
    </div>

    <div class="item" *ngFor="let u of users()">
      <div class="flex">
        <div><b>{{u.username}}</b> <small style="opacity:.7">({{u.role}})</small></div>
        <div style="display:flex;gap:8px">
          <button class="secondary" (click)="cancelUserEdit(u.username)">Prekliči</button>
          <button *ngIf="u.username!=='admin'" (click)="deleteUser(u.username)">Izbriši</button>
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
    button.secondary { background:#2a2a2a; border:1px solid #3a3a3a }
    button.danger { background:#b91c1c }
    h3 { margin: 0 0 10px 0 }
  `]
})
export class HomeComponent implements OnInit {
  role = signal<'admin'|'manager'>('manager');
  customers = signal<Customer[]>([]);
  users = signal<ListedUser[]>([]);

  profileForms: Record<string, ProfileForm> = {};

  userEdits: Record<string, { password?: string; role: 'admin'|'manager'; tenant_slug: string|null }> = {};
  newUser: { username: string; password: string; role: 'admin'|'manager'; tenant_slug: string|null } = {
    username: '', password: '', role: 'manager', tenant_slug: null
  };

  newCustomer = {
    slug: '',
    display_name: '',
    last_paid: '',
    contact: { name: '', email: '', phone: '' },
    create_user: { username: '', password: '', role: 'manager' as 'manager'|'admin' }
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
    if (u.role === 'admin') this.loadAll();
  }

  trackBySlug(_: number, c: Customer) { return c.slug; }

  // ------------ data loading
  private async loadAll() {
    await Promise.all([this.loadCustomers(), this.loadUsers()]);
    this.rebuildUserEditsFromServer();
    this.rebuildProfileFormsFromServer();
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

  private rebuildUserEditsFromServer() {
    const map: Record<string, { password?: string; role: 'admin'|'manager'; tenant_slug: string|null }> = {};
    this.users().forEach(u => { map[u.username] = { role: u.role, tenant_slug: (u.tenant_slug ?? null) }; });
    this.userEdits = map;
  }

  private rebuildProfileFormsFromServer() {
    const forms: Record<string, ProfileForm> = {};
    for (const c of this.customers()) {
      forms[c.slug] = {
        display_name: (c.display_name ?? '') as string,
        last_paid: (c.last_paid ?? '') as string,
        contact: {
          name: c.contact?.name ?? '',
          email: c.contact?.email ?? '',
          phone: c.contact?.phone ?? '',
        }
      };
    }
    this.profileForms = forms;
  }

  // ------------ customer create/delete
  async createCustomer() {
    const body = {
      slug: this.newCustomer.slug.trim(),
      display_name: this.newCustomer.display_name.trim() || this.newCustomer.slug.trim(),
      last_paid: this.newCustomer.last_paid.trim() || null,
      contact: { ...this.newCustomer.contact },
      create_user: (this.newCustomer.create_user.username && this.newCustomer.create_user.password)
        ? { ...this.newCustomer.create_user }
        : undefined
    };
    const r = await fetch(`${environment.apiBase}/api/admin/customers`, {
      method: 'POST', headers: this.headers, body: JSON.stringify(body)
    });
    if (r.ok) {
      await this.loadAll();
      this.cancelNewCustomer();
    } else {
      alert('Create customer failed: ' + await r.text());
    }
  }

  cancelNewCustomer() {
    this.newCustomer = {
      slug: '',
      display_name: '',
      last_paid: '',
      contact: { name: '', email: '', phone: '' },
      create_user: { username: '', password: '', role: 'manager' }
    };
  }

  async deleteCustomer(slug: string) {
    if (!confirm(`Izbrišem stranko "${slug}"? (uporabniki bodo izbrisani) `)) return;
    const r = await fetch(`${environment.apiBase}/api/admin/customers/${encodeURIComponent(slug)}?cascade_users=true`, {
      method: 'DELETE', headers: this.headers
    });
    if (r.ok) {
      await this.loadAll();
    } else {
      alert('Delete customer failed: ' + await r.text());
    }
  }

  // ------------ profile actions
  async cancelProfile(slug: string) {
    const c = this.customers().find(x => x.slug === slug);
    if (!c) return;
    this.profileForms[slug] = {
      display_name: (c.display_name ?? '') as string,
      last_paid: (c.last_paid ?? '') as string,
      contact: {
        name: c.contact?.name ?? '',
        email: c.contact?.email ?? '',
        phone: c.contact?.phone ?? '',
      }
    };
  }

  async saveProfile(slug: string) {
    const form = this.profileForms[slug];
    if (!form) return;
    const r = await fetch(`${environment.apiBase}/api/admin/customers/${slug}/profile`, {
      method: 'PATCH',
      headers: this.headers,
      body: JSON.stringify(form)
    });
    if (r.ok) {
      await this.loadCustomers();
      this.rebuildProfileFormsFromServer();
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
      this.cancelCreateUser();
      await this.loadUsers();
      await this.loadCustomers();
      this.rebuildUserEditsFromServer();
    } else {
      alert('Create failed: ' + await r.text());
    }
  }

  cancelCreateUser() {
    this.newUser = { username: '', password: '', role: 'manager', tenant_slug: null };
  }

  async updateUser(username: string) {
    const body = this.userEdits[username];
    if (!body) return;
    const r = await fetch(`${environment.apiBase}/api/admin/users/${encodeURIComponent(username)}`, {
      method: 'PATCH', headers: this.headers, body: JSON.stringify(body)
    });
    if (r.ok) {
      this.userEdits[username].password = '';
      await this.loadUsers();
      await this.loadCustomers();
      this.rebuildUserEditsFromServer();
    } else {
      alert('Update failed: ' + await r.text());
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
      this.rebuildUserEditsFromServer();
    } else {
      alert('Delete failed: ' + await r.text());
    }
  }

  async cancelUserEdit(username: string) {
    const u = this.users().find(x => x.username === username);
    if (u) this.userEdits[username] = { role: u.role, tenant_slug: (u.tenant_slug ?? null) };
    if (this.userEdits[username]) this.userEdits[username].password = '';
  }
}
