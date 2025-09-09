import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

/** Local types for the designer */
type FlowChoice = { title: string; next: string };
type FlowNode = {
  id: string;
  texts?: string[];
  text?: string;
  choices?: FlowChoice[];
  openInput?: boolean;
  inputType?: 'single' | 'dual' | 'dual-contact';
  action?: string;
  next?: string;
  payload?: any;
};
type Flow = { nodes: FlowNode[] };

@Component({
  selector: 'ace-flow-designer',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './flow-designer.component.html',
  styleUrls: ['./flow-designer.component.scss']
})
export class FlowDesignerComponent implements OnChanges {
  @Input() initialFlow: Flow | null = null;
  @Output() flowChange = new EventEmitter<Flow>();

  flow: Flow = { nodes: [] };
  selectedIndex = 0;
  errors: string[] = [];
  info: string[] = [];

  private readonly LS_KEY = 'ace_flow_designer_json';

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['initialFlow']) this.loadFromInputOrStorage();
  }

  /** ---------- Init / Storage ---------- */
  private loadFromInputOrStorage() {
    const fromLS = this.readLS();
    if (this.initialFlow && Array.isArray(this.initialFlow.nodes) && this.initialFlow.nodes.length) {
      this.flow = this.cloneFlow(this.initialFlow);
    } else if (fromLS) {
      this.flow = this.cloneFlow(fromLS);
    } else {
      this.flow = this.cloneFlow(this.defaultFlow());
    }
    this.normalize();
    this.validate();
    this.emitChange();
  }

  private readLS(): Flow | null {
    try {
      const raw = localStorage.getItem(this.LS_KEY);
      if (!raw) return null;
      const j = JSON.parse(raw);
      if (j && Array.isArray(j.nodes)) return j as Flow;
    } catch {}
    return null;
  }

  private writeLS() {
    try { localStorage.setItem(this.LS_KEY, JSON.stringify(this.flow, null, 2)); } catch {}
  }

  /** ---------- Core helpers ---------- */
  private cloneFlow(f: Flow): Flow {
    return JSON.parse(JSON.stringify(f || { nodes: [] }));
  }

  private normalize() {
    for (const n of this.flow.nodes) {
      if (!n.id) n.id = this.uniqueId('node');
      if (!n.texts && n.text) n.texts = [n.text];
      if (!n.texts) n.texts = [''];
      if (n.openInput && !n.inputType) n.inputType = 'single';
      if (!Array.isArray(n.choices)) n.choices = [];
    }
    if (!this.flow.nodes.length) this.flow.nodes.push(this.makeNode());
    if (this.selectedIndex < 0 || this.selectedIndex >= this.flow.nodes.length) this.selectedIndex = 0;
  }

  private emitChange() {
    this.flowChange.emit(this.flow);
    this.writeLS();
  }

  /** ---------- Defaults ---------- */
  private defaultFlow(): Flow {
    return {
      nodes: [
        {
          id: 'welcome',
          texts: [
            'Preden začnemo – prosim vnesite kontakt (e-pošta in/ali telefon) za povratni info.'
          ],
          openInput: true,
          inputType: 'dual-contact',
          next: 'listing_highlights'
        },
        {
          id: 'listing_highlights',
          texts: [
            '✅ Ključni podatki izbrane nepremičnine\n📍 Vič, Ljubljana\n💶 Cena: €685.000\n📐 180 m² + terasa/vrt\n🛏️ 4 sobe | 🛁 2 kopalnici | 🅿️ 2 parkirni mesti\n\nŽelite nadaljevati?'
          ],
          choices: [{ title: 'Naprej', next: 'fit_check' }]
        },
        {
          id: 'fit_check',
          texts: ['Ali okvirno ustreza vašim željam glede lokacije, cene in velikosti?'],
          choices: [
            { title: 'Da, izgleda super', next: 'timeline' },
            { title: 'Mogoče – imam vprašanja', next: 'open_question' },
            { title: 'Ne – iščem nekaj drugega', next: 'fallback_prefs' }
          ]
        },
        {
          id: 'open_question',
          texts: ['Odlično – kaj vas zanima?'],
          openInput: true,
          inputType: 'single',
          action: 'store_answer',
          next: 'survey_done'
        },
        { id: 'survey_done', action: 'deepseek_score', next: 'timeline' },
        {
          id: 'timeline',
          texts: ['Kdaj bi vam okvirno ustrezal ogled? (ta teden, naslednji teden, vikend?)'],
          choices: [
            { title: 'Ta teden', next: 'schedule_intro' },
            { title: 'Naslednji teden', next: 'schedule_intro' },
            { title: 'Vikend', next: 'schedule_intro' },
            { title: 'Kasneje / nisem prepričan', next: 'closing' }
          ]
        },
        { id: 'schedule_intro', texts: ['Super. Upoštevali bomo vaš termin in vam pošljemo predlog ogleda na posredovani kontakt.'], next: 'end' },
        {
          id: 'fallback_prefs',
          texts: ['Brez skrbi – napišite še: lokacija, proračun in tip (stanovanje/hiša), da predlagam boljše alternative.'],
          openInput: true,
          inputType: 'single',
          action: 'store_answer',
          next: 'closing_alt'
        },
        {
          id: 'closing_alt',
          texts: ['Želite, da za izbrano nepremičnino uredimo ogled ali pošljemo več informacij na vaš kontakt?'],
          choices: [
            { title: 'Uredi ogled', next: 'end' },
            { title: 'Pošlji več informacij', next: 'end' }
          ]
        },
        {
          id: 'closing',
          texts: ['Hvala za informacije 🚀. Predlagam: (1) rezerviramo termin ogleda ali (2) pošljem brošuro s tlorisom in dodatnimi podatki. Kaj vam ustreza?'],
          openInput: true,
          inputType: 'single'
        },
        { id: 'end', texts: ['Odlično 👍. Potrditev in podrobnosti pošljemo kmalu.', 'Hvala za zanimanje – slišimo se v kratkem!'] }
      ]
    };
  }

  private makeNode(partial: Partial<FlowNode> = {}): FlowNode {
    return {
      id: partial.id || this.uniqueId('node'),
      texts: partial.texts || [''],
      choices: partial.choices || [],
      openInput: !!partial.openInput,
      inputType: partial.inputType,
      action: partial.action,
      next: partial.next,
      payload: partial.payload
    };
  }

  private uniqueId(prefix: string): string {
    let i = this.flow.nodes.length + 1;
    while (true) {
      const id = `${prefix}_${i}`;
      if (!this.flow.nodes.some(n => n.id === id)) return id;
      i++;
    }
  }

  /** ---------- Node list ops ---------- */
  selectNode(i: number) {
    if (i < 0 || i >= this.flow.nodes.length) return;
    this.selectedIndex = i;
  }

  addNodeAt(i: number) {
    const n = this.makeNode();
    this.flow.nodes.splice(Math.max(0, i) + 1, 0, n);
    this.selectedIndex = Math.max(0, i) + 1;
    this.normalize();
    this.validate();
    this.emitChange();
  }

  duplicateNode(i: number) {
    const src = this.flow.nodes[i];
    const copy = this.makeNode({
      ...src,
      id: this.uniqueId(src.id || 'node')
    });
    this.flow.nodes.splice(i + 1, 0, copy);
    this.selectedIndex = i + 1;
    this.validate();
    this.emitChange();
  }

  moveNode(i: number, dir: -1 | 1) {
    const j = i + dir;
    if (j < 0 || j >= this.flow.nodes.length) return;
    const [n] = this.flow.nodes.splice(i, 1);
    this.flow.nodes.splice(j, 0, n);
    this.selectedIndex = j;
    this.emitChange();
  }

  deleteNode(i: number) {
    if (this.flow.nodes.length <= 1) return;
    const removedId = this.flow.nodes[i].id;
    this.flow.nodes.splice(i, 1);
    for (const n of this.flow.nodes) {
      if (n.next === removedId) n.next = undefined;
      if (Array.isArray(n.choices)) for (const c of n.choices) if (c.next === removedId) c.next = '';
    }
    this.selectedIndex = Math.max(0, i - 1);
    this.validate();
    this.emitChange();
  }

  /** ---------- Node editor helpers ---------- */
  node(): FlowNode {
    return this.flow.nodes[this.selectedIndex];
  }

  onIdChange(newId: string) {
    const n = this.node();
    const oldId = n.id;
    const trimmed = (newId || '').trim();
    if (!trimmed || trimmed === oldId) return;
    for (const nn of this.flow.nodes) {
      if (nn.next === oldId) nn.next = trimmed;
      if (Array.isArray(nn.choices)) for (const c of nn.choices) if (c.next === oldId) c.next = trimmed;
    }
    n.id = trimmed;
    this.validate();
    this.emitChange();
  }

  addTextLine() {
    const n = this.node();
    n.texts = n.texts || [''];
    n.texts.push('');
    this.emitChange();
  }

  removeTextLine(i: number) {
    const n = this.node();
    if (!n.texts) return;
    if (n.texts.length <= 1) n.texts[0] = '';
    else n.texts.splice(i, 1);
    this.emitChange();
  }

  toggleOpenInput() {
    const n = this.node();
    n.openInput = !n.openInput;
    if (n.openInput && !n.inputType) n.inputType = 'single';
    this.validate();
    this.emitChange();
  }

  addChoice() {
    const n = this.node();
    if (!Array.isArray(n.choices)) n.choices = [];
    n.choices.push({ title: 'Nova izbira', next: '' });
    this.emitChange();
  }

  removeChoice(i: number) {
    const n = this.node();
    if (!Array.isArray(n.choices)) return;
    n.choices.splice(i, 1);
    if (n.choices.length === 0) n.choices = [];
    this.emitChange();
  }

  /** ---------- Payload helpers (fixes template parser errors) ---------- */
  payloadToText(): string {
    const n = this.node();
    if (n.payload === undefined || n.payload === null) return '';
    try {
      return typeof n.payload === 'string'
        ? n.payload
        : JSON.stringify(n.payload, null, 2);
    } catch {
      return String(n.payload ?? '');
    }
  }

  onPayloadChange(text: string) {
    const n = this.node();
    const v = (text || '').trim();
    if (!v) {
      n.payload = undefined;
    } else {
      try {
        n.payload = JSON.parse(v);
      } catch {
        // Keep raw text if not valid JSON
        n.payload = v;
      }
    }
    this.emitChange();
  }

  /** ---------- Validation ---------- */
  validate() {
    const errs: string[] = [];
    const info: string[] = [];

    const ids = new Set<string>();
    for (const n of this.flow.nodes) {
      if (!n.id?.trim()) errs.push('Node with empty id.');
      else if (ids.has(n.id)) errs.push(`Duplicate node id "${n.id}".`);
      else ids.add(n.id);
    }

    const idList = new Set(this.flow.nodes.map(n => n.id));
    for (const n of this.flow.nodes) {
      if (n.next && !idList.has(n.next) && n.next !== 'done') {
        errs.push(`Node "${n.id}" has invalid next -> "${n.next}".`);
      }
      if (Array.isArray(n.choices)) {
        for (const c of n.choices) {
          if (!c.title?.trim()) errs.push(`Node "${n.id}" has a choice without title.`);
          if (c.next && !idList.has(c.next) && c.next !== 'done') {
            errs.push(`Node "${n.id}" choice "${c.title}" has invalid next -> "${c.next}".`);
          }
        }
      }
      if (n.openInput && !n.inputType) {
        errs.push(`Node "${n.id}" is openInput but missing inputType.`);
      }
    }

    if (!this.flow.nodes[0] || !this.flow.nodes[0].id) {
      errs.push('First node is missing.');
    } else {
      info.push(`Start node: ${this.flow.nodes[0].id}`);
    }

    this.errors = errs;
    this.info = info;
  }

  /** ---------- Export / Import ---------- */
  exportJson() {
    const blob = new Blob([JSON.stringify(this.flow, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'conversation_flow.json';
    a.click();
    URL.revokeObjectURL(url);
  }

  copyJson() {
    const text = JSON.stringify(this.flow, null, 2);
    navigator.clipboard?.writeText(text);
  }

  onImportFile(files: FileList | null) {
    if (!files || !files.length) return;
    const f = files[0];
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const j = JSON.parse(String(reader.result));
        if (!j || !Array.isArray(j.nodes)) throw new Error('Invalid flow JSON');
        this.flow = this.cloneFlow(j);
        this.normalize();
        this.validate();
        this.emitChange();
      } catch {
        alert('Napaka pri uvozu JSON.');
      }
    };
    reader.readAsText(f, 'utf-8');
  }

  saveLocal() { this.writeLS(); }

  resetDefault() {
    if (!confirm('Ponastavim na privzeti primer?')) return;
    this.flow = this.defaultFlow();
    this.normalize();
    this.validate();
    this.emitChange();
  }

  /** ---------- Utils ---------- */
  allNodeIds(): string[] {
    return this.flow.nodes.map(n => n.id);
  }
}
