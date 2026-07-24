import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProfileService, Profile, ProfileUpdate } from '../../core/services/profile.service';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.css']
})
export class ProfileComponent implements OnInit {
  private readonly profileService = inject(ProfileService);

  protected readonly profile = signal<Profile | null>(null);
  protected readonly loading = signal(false);
  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly success = signal<string | null>(null);
  protected selectedFileName = '';

  // Form bindable fields
  protected formName = '';
  protected formEmail = '';
  protected formPhone = '';
  protected formLocation = '';
  protected formTitle = '';
  protected formSummary = '';
  protected formSkills = '';
  protected formExperience = '';
  protected formEducation = '';
  protected formProjects = '';
  protected formCertifications = '';

  ngOnInit(): void {
    this.loadProfile();
  }

  loadProfile(): void {
    this.loading.set(true);
    this.error.set(null);
    this.profileService.getProfile().subscribe({
      next: (data) => {
        this.updateFormFields(data);
        this.loading.set(false);
      },
      error: (err) => {
        // Missing profile is expected on first run
        console.log('No profile found in database', err);
        this.profile.set(null);
        this.loading.set(false);
      }
    });
  }

  updateFormFields(data: Profile): void {
    this.profile.set(data);
    this.formName = data.full_name || '';
    this.formEmail = data.email || '';
    this.formPhone = data.phone || '';
    this.formLocation = data.location || '';
    this.formTitle = data.professional_title || '';
    this.formSummary = data.professional_summary || '';
    this.formSkills = (data.skills || []).join(', ');
    this.formExperience = (data.work_experience || []).join('\n');
    this.formEducation = (data.education || []).join('\n');
    this.formProjects = (data.projects || []).join('\n');
    this.formCertifications = (data.certifications || []).join('\n');
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      const file = input.files[0];
      this.selectedFileName = file.name;

      // 2MB size limit check
      if (file.size > 2 * 1024 * 1024) {
        this.error.set('The uploaded resume is larger than 2 MB.');
        this.success.set(null);
        return;
      }

      // Extension check
      const ext = file.name.split('.').pop()?.toLowerCase();
      if (ext !== 'pdf' && ext !== 'docx' && ext !== 'txt') {
        this.error.set('Only PDF, DOCX, and TXT resumes are supported.');
        this.success.set(null);
        return;
      }

      this.uploadFile(file);
    }
  }

  uploadFile(file: File): void {
    this.loading.set(true);
    this.error.set(null);
    this.success.set(null);

    this.profileService.uploadResume(file).subscribe({
      next: (res) => {
        this.updateFormFields(res.profile);
        this.success.set('Resume uploaded and scanned successfully.');
        this.loading.set(false);
      },
      error: (err) => {
        console.error('Scan failed', err);
        const errMsg = err.error?.detail || 'Failed to scan resume. Please ensure it is a readable file.';
        this.error.set(errMsg);
        this.loading.set(false);
      }
    });
  }

  saveProfile(): void {
    if (!this.profile()) return;

    this.saving.set(true);
    this.error.set(null);
    this.success.set(null);

    // Client-side basic email validation
    if (this.formEmail.trim() && (!this.formEmail.includes('@') || !this.formEmail.includes('.'))) {
      this.error.set('Please enter a valid email address.');
      this.saving.set(false);
      return;
    }

    // Split edit inputs back to string arrays
    const skills = this.formSkills.split(',')
      .map(s => s.trim())
      .filter(s => s.length > 0);

    const work_experience = this.formExperience.split('\n')
      .map(i => i.trim())
      .filter(i => i.length > 0);

    const education = this.formEducation.split('\n')
      .map(i => i.trim())
      .filter(i => i.length > 0);

    const projects = this.formProjects.split('\n')
      .map(i => i.trim())
      .filter(i => i.length > 0);

    const certifications = this.formCertifications.split('\n')
      .map(i => i.trim())
      .filter(i => i.length > 0);

    const updateData: ProfileUpdate = {
      full_name: this.formName.trim(),
      email: this.formEmail.trim(),
      phone: this.formPhone.trim(),
      location: this.formLocation.trim(),
      professional_title: this.formTitle.trim(),
      professional_summary: this.formSummary.trim(),
      skills,
      work_experience,
      education,
      projects,
      certifications
    };

    this.profileService.updateProfile(updateData).subscribe({
      next: (data) => {
        this.updateFormFields(data);
        this.success.set('Profile updated successfully.');
        this.saving.set(false);
      },
      error: (err) => {
        console.error('Update failed', err);
        const errMsg = err.error?.detail || 'Failed to save profile edits.';
        this.error.set(errMsg);
        this.saving.set(false);
      }
    });
  }

  resetChanges(): void {
    const active = this.profile();
    if (active) {
      this.updateFormFields(active);
      this.success.set('Form changes reset.');
      this.error.set(null);
    }
  }
}
