import axios, { AxiosInstance, InternalAxiosRequestConfig } from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        "Content-Type": "application/json",
      },
      timeout: 30000,
    });

    // Request interceptor for auth
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // Add auth token if available
        const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Handle unauthorized
          if (typeof window !== "undefined") {
            localStorage.removeItem("auth_token");
            window.location.href = "/login";
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // Generic methods
  async get(url: string, params?: any) {
    return this.client.get(url, { params });
  }

  async post(url: string, data?: any) {
    return this.client.post(url, data);
  }

  async put(url: string, data?: any) {
    return this.client.put(url, data);
  }

  async delete(url: string) {
    return this.client.delete(url);
  }

  // Project methods
  async createProject(data: { name: string; description?: string }) {
    return this.post("/projects/", data);
  }

  async listProjects() {
    return this.get("/projects/");
  }

  async getProject(id: string) {
    return this.get(`/projects/${id}`);
  }

  async getProjectSummary(id: string) {
    return this.get(`/projects/${id}/summary`);
  }

  async deleteProject(id: string) {
    return this.delete(`/projects/${id}`);
  }

  // RTL Analysis
  async analyzeRTL(content: string, filename: string = "design.sv") {
    return this.post("/rtl/analyze", { content, filename });
  }

  async uploadRTL(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return this.client.post("/rtl/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  }

  // Specification Analysis
  async analyzeSpec(content: string, filename: string = "spec.md", docType: string = "markdown") {
    return this.post("/spec/analyze", { content, filename, doc_type: docType });
  }

  async uploadSpec(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return this.client.post("/spec/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  }

  // Verification Plan
  async generatePlan(rtlContent: string, specification?: string) {
    return this.post("/verification/plan", { rtl_content: rtlContent, specification });
  }

  // Assertions
  async generateAssertions(rtlContent: string) {
    return this.post("/verification/assertions", { rtl_content: rtlContent });
  }

  // Tests
  async generateTests(rtlContent: string, coverageGaps?: any[], testTypes?: string[]) {
    return this.post("/verification/tests", { rtl_content: rtlContent, coverage_gaps: coverageGaps, test_types: testTypes });
  }

  // Full Flow
  async runFullFlow(rtlContent: string, specification?: string) {
    return this.post("/verification/full-flow", { rtl_content: rtlContent, specification });
  }

  // Simulation
  async compileRTL(rtlFiles: string[], testbench: string, topModule: string, simulator: string = "verilator") {
    return this.post("/simulation/compile", { rtl_files: rtlFiles, testbench, top_module: topModule, simulator });
  }

  async runSimulation(rtlContent: string, testCode: string, topModule: string, simulator: string = "verilator") {
    return this.post("/simulation/run", { rtl_content: rtlContent, test_code: testCode, top_module: topModule, simulator });
  }

  async analyzeLog(logContent: string, logType: string = "simulation") {
    return this.post("/simulation/analyze-log", { log_content: logContent, log_type: logType });
  }

  // Coverage
  async analyzeCoverage(coverageReport: string, rtlContent?: string, moduleName?: string) {
    return this.post("/coverage/analyze", { coverage_report: coverageReport, rtl_content: rtlContent, module_name: moduleName });
  }

  async identifyGaps(coverageReport: string, rtlContent: string, moduleName: string) {
    return this.post("/coverage/gaps", { coverage_report: coverageReport, rtl_content: rtlContent, module_name: moduleName });
  }

  async generateTargetedTests(coverageReport: string, rtlContent: string, moduleName: string) {
    return this.post("/coverage/generate-targeted-tests", { coverage_report: coverageReport, rtl_content: rtlContent, module_name: moduleName });
  }

  async compareCoverage(before: any, after: any) {
    return this.post("/coverage/compare", { coverage_before: before, coverage_after: after });
  }

  // Analysis
  async analyzeFailure(failureInfo: any, rtlContent?: string, logAnalysis?: any, useAI?: boolean) {
    return this.post("/failure-analysis", { failure_info: failureInfo, rtl_content: rtlContent, log_analysis: logAnalysis, use_ai: useAI });
  }

  async analyzeRegression(results: any[], changedModules?: string[], budgetMinutes?: number) {
    return this.post("/regression/analyze", { results, changed_modules: changedModules, budget_minutes: budgetMinutes });
  }

  async analyzeWaveform(vcdContent: string) {
    return this.post("/waveform/analyze", { vcd_content: vcdContent });
  }

  async getSignalContext(vcdContent: string, failureTime: number, window: number = 100) {
    return this.post("/waveform/signal-context", { vcd_content: vcdContent, failure_time: failureTime, window });
  }

  // AI Agents
  async getAIStatus() {
    return this.get("/ai/status");
  }

  async analyzeDesign(rtlContent: string, parsedModules?: any[]) {
    return this.post("/ai/analyze-design", { rtl_content: rtlContent, parsed_modules: parsedModules });
  }

  async improveTest(testCode: string, failureInfo: string, rtlContent: string) {
    return this.post("/ai/improve-test", { test_code: testCode, failure_info: failureInfo, rtl_content: rtlContent });
  }

  async analyzeGap(gapInfo: any, rtlContent: string) {
    return this.post("/ai/analyze-gap", { gap_info: gapInfo, rtl_content: rtlContent });
  }

  async assessReachability(gapInfo: any, rtlContent: string) {
    return this.post("/ai/assess-reachability", { gap_info: gapInfo, rtl_content: rtlContent });
  }
}

export const api = new ApiClient();
export default api;