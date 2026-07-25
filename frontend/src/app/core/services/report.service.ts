import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams, HttpResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../config/api.config';

@Injectable({
  providedIn: 'root'
})
export class ReportService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = `${API_BASE_URL}/api/reports`;

  downloadJobsPdf(filters: any, reportStatus: string): Observable<HttpResponse<Blob>> {
    let params = new HttpParams().set('status', reportStatus);
    params = this.appendFilterParams(params, filters);

    return this.http.get(`${this.apiUrl}/jobs.pdf`, {
      params,
      responseType: 'blob',
      observe: 'response'
    });
  }

  downloadJobsCsv(filters: any, reportStatus: string): Observable<HttpResponse<Blob>> {
    let params = new HttpParams().set('status', reportStatus);
    params = this.appendFilterParams(params, filters);

    return this.http.get(`${this.apiUrl}/jobs.csv`, {
      params,
      responseType: 'blob',
      observe: 'response'
    });
  }

  downloadSingleJobPdf(jobId: number): Observable<HttpResponse<Blob>> {
    return this.http.get(`${this.apiUrl}/jobs/${jobId}.pdf`, {
      responseType: 'blob',
      observe: 'response'
    });
  }

  downloadApplicationSummaryPdf(): Observable<HttpResponse<Blob>> {
    return this.http.get(`${this.apiUrl}/application-summary.pdf`, {
      responseType: 'blob',
      observe: 'response'
    });
  }

  private appendFilterParams(params: HttpParams, filters: any): HttpParams {
    if (!filters) return params;
    if (filters.search) params = params.set('search', filters.search);
    if (filters.company) params = params.set('company', filters.company);
    if (filters.location) params = params.set('location', filters.location);
    if (filters.remote_status) params = params.set('remote_status', filters.remote_status);
    if (filters.source) params = params.set('source', filters.source);
    if (filters.minimum_match_score !== undefined && filters.minimum_match_score !== null) {
      params = params.set('minimum_match_score', filters.minimum_match_score.toString());
    }
    if (filters.posted_after) params = params.set('posted_after', filters.posted_after);
    if (filters.sort_by) params = params.set('sort_by', filters.sort_by);
    if (filters.sort_order) params = params.set('sort_order', filters.sort_order);
    if (filters.include_duplicates !== undefined && filters.include_duplicates !== null) {
      params = params.set('include_duplicates', filters.include_duplicates.toString());
    }
    return params;
  }
}
