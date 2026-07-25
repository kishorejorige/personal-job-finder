import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ReportService } from './report.service';
import { HttpResponse, HttpHeaders } from '@angular/common/http';

describe('ReportService', () => {
  let service: ReportService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ReportService]
    });
    service = TestBed.inject(ReportService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should download jobs PDF report', () => {
    const dummyBlob = new Blob(['%PDF-1.4...'], { type: 'application/pdf' });
    const filters = { search: 'Python', remote_status: 'remote' };

    service.downloadJobsPdf(filters, 'applied').subscribe((res: HttpResponse<Blob>) => {
      expect(res.body).toEqual(dummyBlob);
      expect(res.headers.get('content-disposition')).toBe('attachment; filename=test.pdf');
    });

    const req = httpMock.expectOne(request =>
      request.url.endsWith('/api/reports/jobs.pdf') &&
      request.params.get('status') === 'applied' &&
      request.params.get('search') === 'Python' &&
      request.params.get('remote_status') === 'remote'
    );
    expect(req.request.method).toBe('GET');

    req.flush(dummyBlob, {
      headers: new HttpHeaders({
        'content-disposition': 'attachment; filename=test.pdf'
      })
    });
  });

  it('should download jobs CSV report', () => {
    const dummyBlob = new Blob(['id,title...'], { type: 'text/csv' });
    const filters = { company: 'TechCorp' };

    service.downloadJobsCsv(filters, 'all').subscribe((res: HttpResponse<Blob>) => {
      expect(res.body).toEqual(dummyBlob);
    });

    const req = httpMock.expectOne(request =>
      request.url.endsWith('/api/reports/jobs.csv') &&
      request.params.get('status') === 'all' &&
      request.params.get('company') === 'TechCorp'
    );
    expect(req.request.method).toBe('GET');

    req.flush(dummyBlob);
  });

  it('should download single job PDF', () => {
    const dummyBlob = new Blob(['%PDF-1.4...'], { type: 'application/pdf' });

    service.downloadSingleJobPdf(42).subscribe((res: HttpResponse<Blob>) => {
      expect(res.body).toEqual(dummyBlob);
    });

    const req = httpMock.expectOne(request => request.url.endsWith('/api/reports/jobs/42.pdf'));
    expect(req.request.method).toBe('GET');
    req.flush(dummyBlob);
  });

  it('should download application summary PDF', () => {
    const dummyBlob = new Blob(['%PDF-1.4...'], { type: 'application/pdf' });

    service.downloadApplicationSummaryPdf().subscribe((res: HttpResponse<Blob>) => {
      expect(res.body).toEqual(dummyBlob);
    });

    const req = httpMock.expectOne(request => request.url.endsWith('/api/reports/application-summary.pdf'));
    expect(req.request.method).toBe('GET');
    req.flush(dummyBlob);
  });
});
