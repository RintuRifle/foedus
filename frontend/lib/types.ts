// ── Foedus API types (mirror of backend Pydantic schemas) ────

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  plan: string;
  evals_used: number;
  is_verified: boolean;
  created_at: string;
}

export interface Tender {
  id: string;
  external_id: string | null;
  source: string;
  title: string;
  description: string | null;
  sector: string[] | null;
  state: string | null;
  department: string | null;
  organization: string | null;
  value_lakh: number | null;
  emd_amount: number | null;
  tender_fee: number | null;
  submission_date: string | null;
  opening_date: string | null;
  published_date: string | null;
  pdf_url: string | null;
  status: string;
  days_remaining: number | null;
  scraped_at: string;
}

export interface TenderFeedItem {
  tender: Tender;
  match_score: number;
  match_reasons: string[] | null;
  is_saved: boolean;
  is_seen: boolean;
}

export interface TenderListResponse {
  items: TenderFeedItem[];
  total: number;
  page: number;
  per_page: number;
  has_next: boolean;
}

export interface EvalStartResponse {
  job_id: string;
  tender_id: string;
  status: string;
  message: string;
}

export interface EvalProgress {
  job_id: string;
  status: string;
  progress_pct: number;
  current_agent: string | null;
  current_message: string | null;
  started_at: string | null;
  duration_seconds: number | null;
}

export interface WsProgressEvent {
  job_id: string;
  agent: string;
  progress: number;
  message: string;
  status: string;
  timestamp: string;
}

export interface ComplianceItem {
  criterion: string;
  category: string | null;
  required_value: string | null;
  user_value: string | null;
  status: "met" | "partial" | "missing";
  source_quote: string | null;
  notes: string | null;
}

export interface EvalReport {
  job_id: string;
  tender_title: string;
  status: string;
  match_score: number | null;
  match_reasons: string[] | null;
  eligibility_status: string | null;
  compliance_matrix: ComplianceItem[];
  win_probability: number | null;
  risk_factors: string[] | null;
  competition_level: string | null;
  duration_seconds: number | null;
  completed_at: string | null;
}

export interface Proposal {
  id: string;
  user_id: string;
  tender_id: string;
  evaluation_id: string | null;
  title: string | null;
  content_md: string | null;
  version: number;
  status: string;
  pdf_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface Company {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  sector: string[] | null;
  turnover_lakh: number | null;
  emp_count: number | null;
  years_experience: number | null;
  location_state: string | null;
  location_city: string | null;
  pan_number: string | null;
  gst_number: string | null;
  iso_certs: string[] | null;
  past_projects: string | null;
  keywords: string[] | null;
  brochure_url: string | null;
  created_at: string;
}

export interface BrochureParse {
  name: string | null;
  description: string | null;
  sector: string[] | null;
  turnover_lakh: number | null;
  emp_count: number | null;
  years_experience: number | null;
  location_state: string | null;
  location_city: string | null;
  iso_certs: string[] | null;
  past_projects: string | null;
  keywords: string[] | null;
  confidence: number;
}
