import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

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
  private readonly apiUrl = 'http://127.0.0.1:8010/api/profile';

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
