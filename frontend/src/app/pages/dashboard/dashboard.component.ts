import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HealthService, HealthResponse } from '../../core/services/health.service';
import { JobService, JobSummary, ProviderStatus } from '../../core/services/job.service';

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

  protected readonly loading = signal(false);
  protected readonly healthData = signal<HealthResponse | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly jobSummary = signal<JobSummary | null>(null);
  protected readonly providerStatuses = signal<ProviderStatus[]>([]);

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
}
