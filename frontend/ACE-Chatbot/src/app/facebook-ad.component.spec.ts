import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FacebookAdComponent } from './facebook-ad.component';

describe('FacebookAdComponent', () => {
  let component: FacebookAdComponent;
  let fixture: ComponentFixture<FacebookAdComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FacebookAdComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(FacebookAdComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
