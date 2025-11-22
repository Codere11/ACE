import { Component, Input, OnInit, OnChanges, SimpleChanges, signal, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

type Stage = 'Pre-Lead' | 'Lead' | 'Qualified' | 'Hot' | 'Won' | 'Lost';

interface NoteRow {
  id: string;
  stage: Stage;
  title: string;
  details: string;
  createdAt: number;  // ms
  updatedAt: number;  // ms
}

@Component({
  selector: 'ace-notes-table',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './notes-table.component.html',
  styleUrls: ['./notes-table.component.scss'],
})
export class NotesTableComponent implements OnInit, OnChanges {
  /** MUST be the LEAD/SESSION id (not the dashboard/browser sid) */
  @Input({ required: true }) sid!: string;

  stages: Stage[] = ['Pre-Lead', 'Lead', 'Qualified', 'Hot', 'Won', 'Lost'];

  rows = signal<NoteRow[]>([]);
  expandedId = signal<string | null>(null);
  savedFlag = signal<boolean>(false);

  private get storageKey(): string | null {
    if (!this.sid || this.sid === 'SSR_NO_SID') return null;
    return `ace_notes_${this.sid}`;
  }

  ngOnInit(): void {
    this.load();
    // autosave when rows change
    effect(() => {
      void this.rows();
      this.save();
    });
  }

  ngOnChanges(ch: SimpleChanges): void {
    if ('sid' in ch && !ch['sid'].firstChange) {
      this.load(); // reload notes when the selected session changes
    }
  }

  addRow(): void {
    if (!this.storageKey) return;
    const now = Date.now();
    const row: NoteRow = {
      id: cryptoRandomId(),
      stage: 'Lead',
      title: '',
      details: '',
      createdAt: now,
      updatedAt: now,
    };
    this.rows.update(list => [row, ...list]);
    this.expandedId.set(row.id);
    this.flashSaved();
  }

  remove(id: string): void {
    if (!this.storageKey) return;
    this.rows.update(list => list.filter(x => x.id !== id));
    if (this.expandedId() === id) this.expandedId.set(null);
    this.flashSaved();
  }

  toggle(id: string): void {
    this.expandedId.set(this.expandedId() === id ? null : id);
  }

  touch(r: NoteRow): void {
    if (!this.storageKey) return;
    r.updatedAt = Date.now();
    // replace only the edited row; trackBy keeps DOM/focus stable
    this.rows.update(list => list.map(x => (x.id === r.id ? { ...r } : x)));
    this.flashSaved();
  }

  ts(ms: number): string {
    const d = new Date(ms);
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  trackById = (_: number, item: NoteRow) => item.id;

  private load(): void {
    try {
      if (!this.storageKey) { this.rows.set([]); return; }
      const raw = localStorage.getItem(this.storageKey);
      const parsed = raw ? (JSON.parse(raw) as NoteRow[]) : [];
      const cleaned = parsed.map(p => ({
        ...p,
        stage: (this.stages as string[]).includes(p.stage) ? (p.stage as Stage) : 'Lead',
      }));
      this.rows.set(cleaned);
    } catch {
      this.rows.set([]);
    }
  }

  private save(): void {
    try {
      if (!this.storageKey) return; // don't save under an invalid key
      localStorage.setItem(this.storageKey, JSON.stringify(this.rows()));
    } catch {}
  }

  private flashSaved(): void {
    this.savedFlag.set(true);
    setTimeout(() => this.savedFlag.set(false), 700);
  }
}

/** Tiny id helper using the browser Crypto API */
function cryptoRandomId(): string {
  const c = (window.crypto as Crypto);
  if (typeof c.randomUUID === 'function') return c.randomUUID();
  const a = new Uint8Array(16);
  c.getRandomValues(a);
  return Array.from(a).map(b => b.toString(16).padStart(2, '0')).join('');
}
