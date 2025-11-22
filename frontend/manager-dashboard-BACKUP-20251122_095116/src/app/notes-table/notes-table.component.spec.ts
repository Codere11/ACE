import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NotesTableComponent } from './notes-table.component';

describe('NotesTableComponent', () => {
  let component: NotesTableComponent;
  let fixture: ComponentFixture<NotesTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NotesTableComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(NotesTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
