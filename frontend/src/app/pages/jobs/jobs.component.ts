import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { JobService, Job, JobListResponse, JobFilters, JobSearchResponse } from '../../core/services/job.service';

@Component({
  selector: 'app-jobs',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './jobs.component.html',
  styleUrls: ['./jobs.component.css']
})
export class JobsComponent implements OnInit {
  private readonly jobService = inject(JobService);

  protected readonly jobs = signal<Job[]>([]);
  protected readonly loading = signal(false);
  protected readonly crawling = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly success = signal<string | null>(null);

  // Crawler statistics
  protected searchResult = signal<JobSearchResponse | null>(null);

  // Pagination & Filtering
  protected totalItems = 0;
  protected currentPage = 1;
  protected totalPages = 1;
  protected readonly pageSize = 25;

  // Filter bindings
  protected searchKeyword = '';
  protected filterCompany = '';
  protected filterLocation = '';
  protected filterRemote = '';
  protected filterStatus = '';
  protected filterMinScore: number | null = null;

  // Sorting
  protected sortBy = 'match_score';
  protected sortOrder = 'desc';

  // Details Modal
  protected selectedJob = signal<Job | null>(null);
  protected editNotesText = '';
  protected isSavingNotes = false;

  ngOnInit(): void {
    this.fetchJobs();
  }

  fetchJobs(): void {
    this.loading.set(true);
    this.error.set(null);

    const filters: JobFilters = {
      search: this.searchKeyword.trim() || undefined,
      company: this.filterCompany.trim() || undefined,
      location: this.filterLocation.trim() || undefined,
      remote_status: this.filterRemote || undefined,
      application_status: this.filterStatus || undefined,
      minimum_match_score: this.filterMinScore !== null ? this.filterMinScore : undefined,
      page: this.currentPage,
      page_size: this.pageSize,
      sort_by: this.sortBy,
      sort_order: this.sortOrder
    };

    this.jobService.getJobs(filters).subscribe({
      next: (res: JobListResponse) => {
        this.jobs.set(res.items);
        this.totalItems = res.total;
        this.currentPage = res.page;
        this.totalPages = res.total_pages;
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Failed to load jobs', err);
        this.error.set('Failed to retrieve jobs. Please check the backend connection.');
        this.loading.set(false);
      }
    });
  }

  applyFilters(): void {
    this.currentPage = 1;
    this.fetchJobs();
  }

  resetFilters(): void {
    this.searchKeyword = '';
    this.filterCompany = '';
    this.filterLocation = '';
    this.filterRemote = '';
    this.filterStatus = '';
    this.filterMinScore = null;
    this.currentPage = 1;
    this.fetchJobs();
  }

  showAllJobs(): void {
    this.resetFilters();
  }

  changePage(direction: number): void {
    const targetPage = this.currentPage + direction;
    if (targetPage >= 1 && targetPage <= this.totalPages) {
      this.currentPage = targetPage;
      this.fetchJobs();
    }
  }

  changeSort(field: string): void {
    if (this.sortBy === field) {
      this.sortOrder = this.sortOrder === 'desc' ? 'asc' : 'desc';
    } else {
      this.sortBy = field;
      this.sortOrder = 'desc';
    }
    this.currentPage = 1;
    this.fetchJobs();
  }

  crawlGreenhouse(): void {
    this.crawling.set(true);
    this.error.set(null);
    this.success.set(null);
    this.searchResult.set(null);

    this.jobService.searchGreenhouse().subscribe({
      next: (res: JobSearchResponse) => {
        this.searchResult.set(res);
        this.success.set('Greenhouse search and sync completed.');
        this.crawling.set(false);
        this.fetchJobs();
      },
      error: (err) => {
        console.error('Greenhouse crawl failed', err);
        const errMsg = err.error?.detail || 'Greenhouse crawl failed. Please check backend log details.';
        this.error.set(errMsg);
        this.crawling.set(false);
      }
    });
  }

  openJobDetails(job: Job): void {
    this.selectedJob.set(job);
    this.editNotesText = job.notes || '';
  }

  closeJobDetails(): void {
    this.selectedJob.set(null);
  }

  updateJobStatus(job: Job, newStatus: string): void {
    this.jobService.updateJobStatus(job.id, newStatus).subscribe({
      next: (updated: Job) => {
        const updatedList = this.jobs().map(j => j.id === job.id ? updated : j);
        this.jobs.set(updatedList);

        const active = this.selectedJob();
        if (active && active.id === job.id) {
          this.selectedJob.set(updated);
        }
      },
      error: (err) => {
        console.error('Status update failed', err);
        alert('Failed to update job status.');
      }
    });
  }

  saveNotes(): void {
    const active = this.selectedJob();
    if (!active) return;

    this.isSavingNotes = true;
    this.jobService.updateJobNotes(active.id, this.editNotesText).subscribe({
      next: (updated: Job) => {
        const updatedList = this.jobs().map(j => j.id === active.id ? updated : j);
        this.jobs.set(updatedList);
        this.selectedJob.set(updated);
        this.isSavingNotes = false;
      },
      error: (err) => {
        console.error('Notes update failed', err);
        alert('Failed to save notes.');
        this.isSavingNotes = false;
      }
    });
  }

  deleteJob(job: Job): void {
    if (confirm(`Are you sure you want to delete this job at ${job.company_name}?`)) {
      this.jobService.deleteJob(job.id).subscribe({
        next: () => {
          this.fetchJobs();
          if (this.selectedJob()?.id === job.id) {
            this.selectedJob.set(null);
          }
        },
        error: (err) => {
          console.error('Deletion failed', err);
          alert('Failed to delete job.');
        }
      });
    }
  }

  recalculateAllMatches(): void {
    this.loading.set(true);
    this.jobService.recalculateMatches().subscribe({
      next: (res) => {
        alert(res.message);
        this.fetchJobs();
      },
      error: (err) => {
        console.error('Recalculate failed', err);
        alert('Failed to recalculate scores.');
        this.loading.set(false);
      }
    });
  }

  getMatchLabel(score: number): string {
    if (score >= 80) return 'Strong';
    if (score >= 60) return 'Good';
    if (score >= 40) return 'Partial';
    return 'Low';
  }

  getMatchClass(score: number): string {
    if (score >= 80) return 'match-strong';
    if (score >= 60) return 'match-good';
    if (score >= 40) return 'match-partial';
    return 'match-low';
  }
}
