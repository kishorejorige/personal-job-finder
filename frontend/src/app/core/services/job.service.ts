import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

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
  board: string;
  message: string;
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
  private readonly apiUrl = 'http://127.0.0.1:8010/api/jobs';

  getJobs(filters: JobFilters): Observable<JobListResponse> {
    let params = new HttpParams();
    if (filters.search) params = params.set('search', filters.search);
    if (filters.company) params = params.set('company', filters.company);
    if (filters.location) params = params.set('location', filters.location);
    if (filters.remote_status) params = params.set('remote_status', filters.remote_status);
    if (filters.application_status) params = params.set('application_status', filters.application_status);
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
