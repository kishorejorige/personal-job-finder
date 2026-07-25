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

  // Categories list
  protected readonly categories = [
    'IT and Software', 'Engineering', 'Electronics and Electrical', 'Accounting and Finance',
    'Sales and Marketing', 'Administration', 'Customer Service', 'Education', 'Healthcare',
    'Logistics and Operations', 'Hospitality', 'Skilled Trades', 'Manufacturing', 'Retail',
    'Human Resources', 'Creative and Design', 'Legal', 'Fresher or Student', 'Other', 'Unknown'
  ];

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

  protected formObjective = '';
  protected formTotalExperience = '';
  protected formCurrentCompany = '';
  protected formCurrentRole = '';
  protected formPreferredJobRole = '';
  protected formPreferredLocation = '';
  protected formAvailability = '';
  protected formOccupationCategory = 'Unknown';
  protected formTechnicalSkills = '';
  protected formSoftSkills = '';
  protected formLanguages = '';
  protected formAchievements = '';
  protected formTraining = '';
  protected formInternships = '';
  protected formLicences = '';
  protected formToolsAndEquipment = '';
  protected formAdditionalInformation = '';

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

    this.formObjective = data.career_objective || '';
    this.formTotalExperience = data.total_experience || '';
    this.formCurrentCompany = data.current_company || '';
    this.formCurrentRole = data.current_role || '';
    this.formPreferredJobRole = data.preferred_job_role || '';
    this.formPreferredLocation = data.preferred_location || '';
    this.formAvailability = data.availability || '';
    this.formOccupationCategory = data.occupation_category || 'Unknown';
    this.formTechnicalSkills = (data.technical_skills || []).join(', ');
    this.formSoftSkills = (data.soft_skills || []).join(', ');
    this.formLanguages = (data.languages || []).join(', ');
    this.formAchievements = (data.achievements || []).join('\n');
    this.formTraining = (data.training || []).join('\n');
    this.formInternships = (data.internships || []).join('\n');
    this.formLicences = (data.licences || []).join('\n');
    this.formToolsAndEquipment = (data.tools_and_equipment || []).join(', ');
    this.formAdditionalInformation = data.additional_information || '';
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

    const technical_skills = this.formTechnicalSkills.split(',')
      .map(s => s.trim())
      .filter(s => s.length > 0);

    const soft_skills = this.formSoftSkills.split(',')
      .map(s => s.trim())
      .filter(s => s.length > 0);

    const languages = this.formLanguages.split(',')
      .map(s => s.trim())
      .filter(s => s.length > 0);

    const achievements = this.formAchievements.split('\n')
      .map(i => i.trim())
      .filter(i => i.length > 0);

    const training = this.formTraining.split('\n')
      .map(i => i.trim())
      .filter(i => i.length > 0);

    const internships = this.formInternships.split('\n')
      .map(i => i.trim())
      .filter(i => i.length > 0);

    const licences = this.formLicences.split('\n')
      .map(i => i.trim())
      .filter(i => i.length > 0);

    const tools_and_equipment = this.formToolsAndEquipment.split(',')
      .map(s => s.trim())
      .filter(s => s.length > 0);

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
      certifications,

      career_objective: this.formObjective.trim(),
      total_experience: this.formTotalExperience.trim(),
      current_company: this.formCurrentCompany.trim(),
      current_role: this.formCurrentRole.trim(),
      preferred_job_role: this.formPreferredJobRole.trim(),
      preferred_location: this.formPreferredLocation.trim(),
      availability: this.formAvailability.trim(),
      occupation_category: this.formOccupationCategory.trim(),
      technical_skills,
      soft_skills,
      languages,
      achievements,
      training,
      internships,
      licences,
      tools_and_equipment,
      additional_information: this.formAdditionalInformation.trim()
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
