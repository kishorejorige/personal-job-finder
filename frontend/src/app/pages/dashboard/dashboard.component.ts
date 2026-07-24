import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HealthService, HealthResponse } from '../../core/services/health.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrls: []
})
export class DashboardComponent implements OnInit {
  private readonly healthService = inject(HealthService);

  protected readonly loading = signal(false);
  protected readonly healthData = signal<HealthResponse | null>(null);
  protected readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.checkHealth();
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
}
