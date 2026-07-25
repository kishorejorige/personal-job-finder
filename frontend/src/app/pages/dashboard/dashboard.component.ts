import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpResponse } from '@angular/common/http';
import { HealthService, HealthResponse } from '../../core/services/health.service';
import { JobService, JobSummary, ProviderStatus } from '../../core/services/job.service';
import { ReportService } from '../../core/services/report.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrls: []
})
export class DashboardComponent implements OnInit {
  private readonly healthService = inject(HealthService);
  private readonly jobService = inject(JobService);
  private readonly reportService = inject(ReportService);

  protected readonly loading = signal(false);
  protected readonly healthData = signal<HealthResponse | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly jobSummary = signal<JobSummary | null>(null);
  protected readonly providerStatuses = signal<ProviderStatus[]>([]);

  protected readonly exporting = signal(false);
  protected readonly exportSuccess = signal<string | null>(null);
  protected readonly exportError = signal<string | null>(null);

  ngOnInit(): void {
    this.refreshDashboard();
  }

  refreshDashboard(): void {
    this.checkHealth();
    this.loadJobSummary();
    this.loadProviderStatuses();
  }

  checkHealth(): void {
    this.loading.set(true);
    this.error.set(null);

    this.healthService.getHealth().subscribe({
      next: (data) => {
        this.healthData.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Health check failed', err);
        this.healthData.set(null);
        this.error.set('Could not connect to the backend server. Please make sure it is running.');
        this.loading.set(false);
      }
    });
  }

  loadJobSummary(): void {
    this.jobService.getSummary().subscribe({
      next: (summary) => {
        this.jobSummary.set(summary);
      },
      error: (err) => {
        console.error('Failed to load job summary', err);
      }
    });
  }

  loadProviderStatuses(): void {
    this.jobService.getProvidersStatus().subscribe({
      next: (statuses) => {
        this.providerStatuses.set(statuses);
      },
      error: (err) => {
        console.error('Failed to load provider statuses', err);
      }
    });
  }

  protected getActiveSourcesCount(): number {
    return this.providerStatuses().filter(p => p.enabled).length;
  }

  protected getLastRefreshDate(): Date | null {
    const dates = this.providerStatuses()
      .map(p => p.last_run_at ? new Date(p.last_run_at) : null)
      .filter((d): d is Date => d !== null);
    if (dates.length === 0) return null;
    return new Date(Math.max(...dates.map(d => d.getTime())));
  }

  downloadReport(format: 'pdf', status: string): void {
    this.exporting.set(true);
    this.exportSuccess.set(null);
    this.exportError.set(null);

    this.reportService.downloadJobsPdf(null, status).subscribe({
      next: (response: HttpResponse<Blob>) => {
        const blob = response.body;
        if (!blob) {
          this.exportError.set('Received empty report data.');
          this.exporting.set(false);
          return;
        }

        const contentDisposition = response.headers.get('content-disposition') || response.headers.get('Content-Disposition');
        let filename = `personal-job-finder-${status}-jobs.pdf`;
        if (contentDisposition) {
          const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
          const matches = filenameRegex.exec(contentDisposition);
          if (matches != null && matches[1]) {
            filename = matches[1].replace(/['"]/g, '');
          }
        }

        const link = document.createElement('a');
        const url = window.URL.createObjectURL(blob);
        link.href = url;
        link.download = filename;
        link.click();
        window.URL.revokeObjectURL(url);

        this.exporting.set(false);
        this.exportSuccess.set('Report downloaded successfully.');
      },
      error: (err) => {
        console.error('Export failed', err);
        this.exporting.set(false);
        this.exportError.set('Unable to create the report.');
      }
    });
  }
}
