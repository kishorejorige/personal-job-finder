import { ComponentFixture, TestBed } from '@angular/core/testing';
import { JobsComponent } from './jobs.component';
import { JobService } from '../../core/services/job.service';
import { ReportService } from '../../core/services/report.service';
import { of, throwError } from 'rxjs';
import { HttpResponse, HttpHeaders } from '@angular/common/http';

describe('JobsComponent - Export Reports', () => {
  let component: JobsComponent;
  let fixture: ComponentFixture<JobsComponent>;
  let mockJobService: any;
  let mockReportService: any;

  beforeEach(async () => {
    mockJobService = {
      getJobs: jasmine.createSpy('getJobs').and.returnValue(of({ items: [], total: 0, page: 1, total_pages: 1 })),
      getProvidersStatus: jasmine.createSpy('getProvidersStatus').and.returnValue(of([]))
    };

    mockReportService = {
      downloadJobsPdf: jasmine.createSpy('downloadJobsPdf'),
      downloadJobsCsv: jasmine.createSpy('downloadJobsCsv'),
      downloadSingleJobPdf: jasmine.createSpy('downloadSingleJobPdf'),
      downloadApplicationSummaryPdf: jasmine.createSpy('downloadApplicationSummaryPdf')
    };

    await TestBed.configureTestingModule({
      imports: [JobsComponent],
      providers: [
        { provide: JobService, useValue: mockJobService },
        { provide: ReportService, useValue: mockReportService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(JobsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should call reportService with active filters on downloadReport', () => {
    // Setup inputs
    component['searchKeyword'] = 'Python';
    component['filterRemote'] = 'remote';

    const dummyBlob = new Blob(['%PDF-1.4...'], { type: 'application/pdf' });
    const response = new HttpResponse({
      body: dummyBlob,
      headers: new HttpHeaders({ 'content-disposition': 'attachment; filename="all-jobs.pdf"' })
    });

    mockReportService.downloadJobsPdf.and.returnValue(of(response));

    // Spy on browser anchor elements triggers
    const spyAnchor = spyOn(document, 'createElement').and.callThrough();
    const spyUrl = spyOn(window.URL, 'createObjectURL').and.returnValue('blob:dummy');
    const spyRevoke = spyOn(window.URL, 'revokeObjectURL');

    component.downloadReport('pdf', 'all');

    expect(mockReportService.downloadJobsPdf).toHaveBeenCalledWith(
      jasmine.objectContaining({
        search: 'Python',
        remote_status: 'remote'
      }),
      'all'
    );
    expect(spyAnchor).toHaveBeenCalledWith('a');
    expect(spyUrl).toHaveBeenCalledWith(dummyBlob);
    expect(spyRevoke).toHaveBeenCalledWith('blob:dummy');
    expect(component['success']()).toBe('PDF report downloaded successfully.');
  });

  it('should handle export failures cleanly', () => {
    mockReportService.downloadJobsPdf.and.returnValue(throwError(() => new Error('Server Error')));

    component.downloadReport('pdf', 'all');

    expect(component['exportErrorMessage']()).toBe('Unable to create the report. Please try again.');
    expect(component['exportingPdf']()).toBe(false);
  });
});
