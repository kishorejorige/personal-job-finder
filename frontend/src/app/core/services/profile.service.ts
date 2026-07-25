import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_BASE_URL } from '../config/api.config';

export interface Profile {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  location: string;
  professional_title: string;
  professional_summary: string;
  skills: string[];
  work_experience: string[];
  education: string[];
  projects: string[];
  certifications: string[];
  resume_filename?: string;
  resume_text?: string;

  career_objective?: string;
  total_experience?: string;
  current_company?: string;
  current_role?: string;
  preferred_job_role?: string;
  preferred_location?: string;
  availability?: string;
  occupation_category?: string;
  technical_skills?: string[];
  soft_skills?: string[];
  languages?: string[];
  achievements?: string[];
  training?: string[];
  internships?: string[];
  licences?: string[];
  tools_and_equipment?: string[];
  additional_information?: string;
  resume_quality?: string;
}

export interface ProfileUpdate {
  full_name: string;
  email: string;
  phone: string;
  location: string;
  professional_title: string;
  professional_summary: string;
  skills: string[];
  work_experience: string[];
  education: string[];
  projects: string[];
  certifications: string[];

  career_objective: string;
  total_experience: string;
  current_company: string;
  current_role: string;
  preferred_job_role: string;
  preferred_location: string;
  availability: string;
  occupation_category: string;
  technical_skills: string[];
  soft_skills: string[];
  languages: string[];
  achievements: string[];
  training: string[];
  internships: string[];
  licences: string[];
  tools_and_equipment: string[];
  additional_information: string;
}

export interface ResumeUploadResponse {
  message: string;
  profile: Profile;
}

@Injectable({
  providedIn: 'root'
})
export class ProfileService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = `${API_BASE_URL}/api/profile`;

  getProfile(): Observable<Profile> {
    return this.http.get<Profile>(this.apiUrl);
  }

  uploadResume(file: File): Observable<ResumeUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ResumeUploadResponse>(`${this.apiUrl}/upload-resume`, formData);
  }

  updateProfile(profile: ProfileUpdate): Observable<Profile> {
    return this.http.put<Profile>(this.apiUrl, profile);
  }
}
