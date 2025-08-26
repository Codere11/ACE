import { TestBed } from '@angular/core/testing';

import { LiveEventsService } from './live-events.service';

describe('LiveEventsService', () => {
  let service: LiveEventsService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(LiveEventsService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
