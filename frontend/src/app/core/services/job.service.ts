import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../config/api.config';

export interface Job {
  id: number;
  external_id?: string;
  title: string;
  company_name: string;
  location?: string;
  remote_status?: string;
  employment_type?: string;
  salary?: string;
  description?: string;
  skills: string[];
  matched_skills: string[];
  missing_skills: string[];
  source: string;
  source_board?: string;
  original_url?: string;
  posted_date?: string;
  match_score: number;
  application_status: string;
  applied_date?: string;
  notes?: string;
  job_fingerprint?: string;
  duplicate_of_id?: number;
  created_at: string;
  updated_at: string;
  last_seen_at: string;
}

export interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface BoardError {
  board?: string;
  site?: string;
  source?: string;
  message: string;
}

export interface ProviderResult {
  source: string;
  status: string;
  sources_checked: number;
  sources_succeeded: number;
  sources_failed: number;
  jobs_received: number;
  jobs_created: number;
  jobs_updated: number;
  errors: BoardError[];
}

export interface SearchAllResponse {
  started_at: string;
  completed_at: string;
  total_jobs_received: number;
  jobs_created: number;
  jobs_updated: number;
  providers_succeeded: number;
  providers_failed: number;
  provider_results: ProviderResult[];
}

export interface ProviderStatus {
  source: string;
  enabled: boolean;
  configured_sources: number;
  last_run_at?: string;
  last_status: string;
  last_jobs_received: number;
  last_error?: string;
}

export interface ProviderRun {
  id: number;
  source: string;
  started_at: string;
  completed_at?: string;
  status: string;
  sources_checked: number;
  sources_succeeded: number;
  sources_failed: number;
  jobs_received: number;
  jobs_created: number;
  jobs_updated: number;
  error_summary?: string;
}

export interface JobSearchResponse {
  source: string;
  boards_checked: number;
  boards_succeeded: number;
  boards_failed: number;
  jobs_received: number;
  jobs_created: number;
  jobs_updated: number;
  errors: BoardError[];
}

export interface JobSummary {
  total_jobs: number;
  not_applied: number;
  saved: number;
  applied: number;
  interviews: number;
  rejected: number;
  offers: number;
  strong_matches: number;
}

export interface JobFilters {
  search?: string;
  company?: string;
  location?: string;
  remote_status?: string;
  application_status?: string;
  minimum_match_score?: number;
  source?: string;
  include_duplicates?: boolean;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: string;
}

@Injectable({
  providedIn: 'root'
})
export class JobService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = `${API_BASE_URL}/api/jobs`;

  getJobs(filters: JobFilters): Observable<JobListResponse> {
    let params = new HttpParams();
    if (filters.search) params = params.set('search', filters.search);
    if (filters.company) params = params.set('company', filters.company);
    if (filters.location) params = params.set('location', filters.location);
    if (filters.remote_status) params = params.set('remote_status', filters.remote_status);
    if (filters.application_status) params = params.set('application_status', filters.application_status);
    if (filters.source) params = params.set('source', filters.source);
    if (filters.include_duplicates !== undefined && filters.include_duplicates !== null) {
      params = params.set('include_duplicates', filters.include_duplicates.toString());
    }
    if (filters.minimum_match_score !== undefined && filters.minimum_match_score !== null) {
      params = params.set('minimum_match_score', filters.minimum_match_score.toString());
    }
    if (filters.page) params = params.set('page', filters.page.toString());
    if (filters.page_size) params = params.set('page_size', filters.page_size.toString());
    if (filters.sort_by) params = params.set('sort_by', filters.sort_by);
    if (filters.sort_order) params = params.set('sort_order', filters.sort_order);

    return this.http.get<JobListResponse>(this.apiUrl, { params });
  }

  getJob(id: number): Observable<Job> {
    return this.http.get<Job>(`${this.apiUrl}/${id}`);
  }

  searchGreenhouse(): Observable<JobSearchResponse> {
    return this.http.post<JobSearchResponse>(`${this.apiUrl}/search/greenhouse`, {});
  }

  searchAll(sources?: string[], force: boolean = false): Observable<SearchAllResponse> {
    let params = new HttpParams();
    if (force) {
      params = params.set('force', 'true');
    }
    return this.http.post<SearchAllResponse>(`${this.apiUrl}/search/all`, { sources }, { params });
  }

  getProvidersStatus(): Observable<ProviderStatus[]> {
    return this.http.get<ProviderStatus[]>(`${this.apiUrl}/providers`);
  }

  getProviderRuns(source?: string, limit?: number): Observable<ProviderRun[]> {
    let params = new HttpParams();
    if (source) params = params.set('source', source);
    if (limit) params = params.set('limit', limit.toString());
    return this.http.get<ProviderRun[]>(`${this.apiUrl}/provider-runs`, { params });
  }

  updateJobStatus(id: number, status: string): Observable<Job> {
    return this.http.patch<Job>(`${this.apiUrl}/${id}/status`, { application_status: status });
  }

  updateJobNotes(id: number, notes: string): Observable<Job> {
    return this.http.patch<Job>(`${this.apiUrl}/${id}/notes`, { notes });
  }

  recalculateMatches(): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.apiUrl}/recalculate-matches`, {});
  }

  deleteJob(id: number): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(`${this.apiUrl}/${id}`);
  }

  getSummary(): Observable<JobSummary> {
    return this.http.get<JobSummary>(`${this.apiUrl}/summary`);
  }
}
