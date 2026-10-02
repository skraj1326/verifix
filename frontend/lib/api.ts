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
  async analyzeRTL(content: string, filename: string = "design.sv", projectId?: string) {
    return this.post("/rtl/analyze", {
      content,
      filename,
      ...(projectId ? { project_id: projectId } : {}),
    });
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

  // RTL Hierarchy
  async getHierarchy(designId: string) {
    return this.get(`/rtl/hierarchy/${designId}`);
  }

  async generateDiagram(designId: string, format: string = "mermaid") {
    return this.post("/rtl/diagram", { design_id: designId, format });
  }

  // Coverage Dashboard
  async getCoverageDashboard(projectId: string) {
    return this.get(`/coverage/dashboard/${projectId}`);
  }

  async getCoverageDrilldown(projectId: string, moduleName: string, covergroup?: string) {
    return this.get(`/coverage/drilldown/${projectId}/${moduleName}`, { params: { covergroup } });
  }

  async getBinDetails(projectId: string, moduleName: string, covergroupName: string, coverpointName: string) {
    return this.get(`/coverage/bins/${projectId}/${moduleName}/${covergroupName}/${coverpointName}`);
  }

  async getCoverageTrends(projectId: string, days: number = 30) {
    return this.get(`/coverage/trends/${projectId}`, { params: { days } });
  }

  // Reports
  async generateReport(projectId: string, data: { format?: string; include_sections?: string[]; template?: string; simulation_id?: string }) {
    return this.post("/reports/generate", { project_id: projectId, ...data });
  }

  /**
   * The backend route is POST /reports/export/{report_id}, but reports are not
   * persisted, so `report_id` is a required-but-ignored path placeholder. We
   * send the literal "latest" to make that explicit rather than implying a
   * stored report lookup. PDF export is not implemented server-side.
   */
  async exportReport(projectId: string, data: { format?: string; simulation_id?: string; include_sections?: string[]; template?: string }) {
    return this.post("/reports/export/latest", { project_id: projectId, ...data });
  }

  // Waveform
  async uploadWaveform(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return this.client.post("/waveform/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  }

  async getWaveform(waveformId: string) {
    return this.get(`/waveform/${waveformId}`);
  }

  async listSignals(waveformId: string, pattern?: string) {
    return this.get(`/waveform/${waveformId}/signals`, { params: { pattern } });
  }

  async getSignal(waveformId: string, signalName: string) {
    return this.get(`/waveform/${waveformId}/signal/${signalName}`);
  }

  async getWaveformSignalContext(waveformId: string, failureTime: number, window: number = 100) {
    return this.post(`/waveform/${waveformId}/signal-context`, {
      waveform_id: waveformId,
      failure_time: failureTime,
      window,
    });
  }

  async compareWaveforms(waveformId1: string, waveformId2: string, tolerance: number = 0) {
    return this.post("/waveform/compare", {
      waveform_id_1: waveformId1,
      waveform_id_2: waveformId2,
      tolerance,
    });
  }
}

export const api = new ApiClient();
export default api;

/**
 * Named clients used by individual pages.
 *
 * Every method maps to a route that exists in the backend OpenAPI schema
 * (48 operations) and the request bodies match the real Pydantic request
 * models. These clients unwrap the Axios response so callers receive the
 * payload directly, unlike the raw `api` client which returns the response.
 */

async function unwrap<T = any>(promise: Promise<{ data: T }>): Promise<T> {
  const response = await promise;
  return response.data;
}

export interface ProjectCreateBody {
  name: string;
  description?: string;
}

export interface FailureAnalysisBody {
  failure_info: Record<string, any>;
  rtl_content?: string | null;
  log_analysis?: Record<string, any> | null;
  use_ai?: boolean;
}

export interface SimulateBody {
  rtl_content: string;
  test_code: string;
  top_module: string;
  simulator?: string;
  timeout?: number;
}

export interface CompileBody {
  rtl_files: string[];
  testbench: string;
  top_module: string;
  simulator?: string;
  timeout?: number;
}

export interface RegressionBody {
  results: any[];
  changed_modules?: string[] | null;
  budget_minutes?: number;
}

export const projectsApi = {
  list: () => unwrap(api.listProjects()),
  create: (data: ProjectCreateBody) => unwrap(api.createProject(data)),
  get: (projectId: string) => unwrap(api.getProject(projectId)),
  getSummary: (projectId: string) => unwrap(api.getProjectSummary(projectId)),
  remove: (projectId: string) => unwrap(api.deleteProject(projectId)),
};

export const rtlApi = {
  analyze: (content: string, filename = "design.sv", projectId?: string) =>
    unwrap(api.analyzeRTL(content, filename, projectId)),
  upload: (file: File) => unwrap(api.uploadRTL(file)),
  getHierarchy: (designId: string) => unwrap(api.getHierarchy(designId)),
  generateDiagram: (designId: string, format = "mermaid") => unwrap(api.generateDiagram(designId, format)),
};

export const specApi = {
  analyze: (content: string, filename = "spec.md", docType = "markdown") =>
    unwrap(api.analyzeSpec(content, filename, docType)),
  upload: (file: File) => unwrap(api.uploadSpec(file)),
  getRequirementCategories: () => unwrap(api.get("/spec/requirement-categories")),
};

export const verificationApi = {
  generateAssertions: (rtlContent: string) => unwrap(api.generateAssertions(rtlContent)),
  generatePlan: (rtlContent: string, specification?: string) =>
    unwrap(api.generatePlan(rtlContent, specification)),
  generateTests: (rtlContent: string, coverageGaps?: any[], testTypes?: string[]) =>
    unwrap(api.generateTests(rtlContent, coverageGaps, testTypes)),
  runFullFlow: (rtlContent: string, specification?: string) =>
    unwrap(api.runFullFlow(rtlContent, specification)),
};

export const simulationApi = {
  run: (body: SimulateBody) => unwrap(api.post("/simulation/run", body)),
  compile: (body: CompileBody) => unwrap(api.post("/simulation/compile", body)),
  analyzeLog: (body: { log_content: string; log_type?: string }) =>
    unwrap(api.post("/simulation/analyze-log", body)),
};

export const failureApi = {
  analyze: (body: FailureAnalysisBody) => unwrap(api.post("/failure-analysis", body)),
};

export const regressionApi = {
  run: (body: RegressionBody) => unwrap(api.post("/regression/analyze", body)),
};

export const coverageApi = {
  analyze: (coverageReport: string, rtlContent?: string, moduleName?: string) =>
    unwrap(api.analyzeCoverage(coverageReport, rtlContent, moduleName)),
  getDashboard: (projectId: string) => unwrap(api.getCoverageDashboard(projectId)),
  getDrilldown: (projectId: string, moduleName: string, covergroup?: string) =>
    unwrap(api.getCoverageDrilldown(projectId, moduleName, covergroup)),
  getBins: (projectId: string, moduleName: string, covergroup: string, coverpoint: string) =>
    unwrap(api.getBinDetails(projectId, moduleName, covergroup, coverpoint)),
  getTrends: (projectId: string, days = 30) => unwrap(api.getCoverageTrends(projectId, days)),
};

export const reportsApi = {
  generate: (
    projectId: string,
    data: { format?: string; include_sections?: string[]; template?: string; simulation_id?: string }
  ) => unwrap(api.generateReport(projectId, data)),
  exportLatest: (
    projectId: string,
    data: { format?: string; simulation_id?: string; include_sections?: string[]; template?: string }
  ) => unwrap(api.exportReport(projectId, data)),
};

export const waveformApi = {
  upload: (file: File) => unwrap(api.uploadWaveform(file)),
  analyze: (vcdContent: string) => unwrap(api.analyzeWaveform(vcdContent)),
  get: (waveformId: string) => unwrap(api.getWaveform(waveformId)),
  listSignals: (waveformId: string, pattern?: string) => unwrap(api.listSignals(waveformId, pattern)),
  getSignal: (waveformId: string, signalName: string) => unwrap(api.getSignal(waveformId, signalName)),
  getSignalContext: (waveformId: string, failureTime: number, window = 100) =>
    unwrap(api.getWaveformSignalContext(waveformId, failureTime, window)),
  compare: (waveformId1: string, waveformId2: string, tolerance = 0) =>
    unwrap(api.compareWaveforms(waveformId1, waveformId2, tolerance)),
};

export const aiApi = {
  getStatus: () => unwrap(api.getAIStatus()),
  analyzeDesign: (rtlContent: string, parsedModules?: any[]) =>
    unwrap(api.analyzeDesign(rtlContent, parsedModules)),
  improveTest: (testCode: string, failureInfo: string, rtlContent: string) =>
    unwrap(api.improveTest(testCode, failureInfo, rtlContent)),
  analyzeGap: (gapInfo: any, rtlContent: string) => unwrap(api.analyzeGap(gapInfo, rtlContent)),
  assessReachability: (gapInfo: any, rtlContent: string) => unwrap(api.assessReachability(gapInfo, rtlContent)),
  debugFailure: (body: { failure_info: any; rtl_content?: string | null }) =>
    unwrap(api.post("/ai/debug-failure", body)),
};
