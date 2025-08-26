import { TestBed } from '@angular/core/testing';

import { LeadServiceService } from './live-events.service';

describe('LeadServiceService', () => {
  let service: LeadServiceService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(LeadServiceService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
