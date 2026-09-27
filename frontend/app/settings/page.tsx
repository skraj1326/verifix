'use client';

import { useState, useEffect } from 'react';
import { 
  Settings, 
  Database, 
  Terminal, 
  Key,
  Brain,
  Save,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Eye,
  EyeOff,
  Copy,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const defaultSettings = {
  database: {
    url: 'sqlite+aiosqlite:///./astrixcore.db',
    syncUrl: 'sqlite:///./astrixcore.db',
  },
  storage: {
    root: './storage',
    rtl: './storage/rtl',
    tests: './storage/tests',
    logs: './storage/logs',
    coverage: './storage/coverage',
  },
  simulation: {
    verilatorPath: 'verilator',
    icarusPath: 'iverilog',
    timeout: 300,
    maxConcurrent: 4,
  },
  ai: {
    provider: 'mock',
    apiKey: '',
    model: 'gpt-4o',
    baseUrl: '',
    temperature: 0.1,
    maxTokens: 4096,
    enabled: true,
    confidenceThreshold: 0.6,
    maxRetries: 3,
  },
  security: {
    secretKey: 'change-me-in-production',
    encryptionKey: '',
    auditLogEnabled: true,
    corsOrigins: ['http://localhost:3000', 'http://localhost:5173'],
  },
  app: {
    name: 'AstrixCore Verification AI',
    version: '0.1.0',
    debug: false,
    apiPrefix: '/api/v1',
  },
};

export default function SettingsPage() {
  const [settings, setSettings] = useState(defaultSettings);
  const [saved, setSaved] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, boolean>>({});

  const handleChange = (section: string, field: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [field]: value,
      },
    }));
    setSaved(false);
  };

  const handleSave = async () => {
    // In a real app, this would POST to the backend
    console.log('Saving settings:', settings);
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const testConnection = async (type: string) => {
    setTesting(type);
    // Simulate connection test
    await new Promise(resolve => setTimeout(resolve, 1500));
    setTestResults(prev => ({ ...prev, [type]: true }));
    setTesting(null);
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold">Settings</h1>
            <button
              onClick={handleSave}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
            >
              <Save className="w-4 h-4 mr-2" />
              {saved ? 'Saved!' : 'Save Changes'}
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar */}
          <aside className="lg:col-span-1">
            <nav className="space-y-1">
              {[
                { id: 'app', label: 'Application', icon: Settings },
                { id: 'database', label: 'Database', icon: Database },
                { id: 'storage', label: 'Storage', icon: Terminal },
                { id: 'simulation', label: 'Simulation', icon: Terminal },
                { id: 'ai', label: 'AI / LLM', icon: Brain },
                { id: 'security', label: 'Security', icon: Key },
              ].map((section) => (
                <button
                  key={section.id}
                  className="w-full px-4 py-3 rounded-lg text-left text-sm font-medium hover:bg-secondary transition-colors"
                >
                  <section.icon className="w-5 h-5 mr-3" />
                  {section.label}
                </button>
              ))}
            </nav>
          </aside>

          {/* Content */}
          <div className="lg:col-span-3 space-y-6">
            {/* Application */}
            <SettingsSection title="Application" icon={Settings}>
              <SettingField
                label="Application Name"
                value={settings.app.name}
                onChange={(v) => handleChange('app', 'name', v)}
              />
              <SettingField
                label="Version"
                value={settings.app.version}
                onChange={(v) => handleChange('app', 'version', v)}
                disabled
              />
              <SettingField
                label="API Prefix"
                value={settings.app.apiPrefix}
                onChange={(v) => handleChange('app', 'apiPrefix', v)}
              />
              <SettingToggle
                label="Debug Mode"
                checked={settings.app.debug}
                onChange={(v) => handleChange('app', 'debug', v)}
              />
            </SettingsSection>

            {/* Database */}
            <SettingsSection title="Database" icon={Database}>
              <SettingField
                label="Database URL (Async)"
                value={settings.database.url}
                onChange={(v) => handleChange('database', 'url', v)}
                type="text"
                description="SQLite: sqlite+aiosqlite:///./astrixcore.db | PostgreSQL: postgresql+asyncpg://user:pass@host:5432/db"
              />
              <SettingField
                label="Database URL (Sync)"
                value={settings.database.syncUrl}
                onChange={(v) => handleChange('database', 'syncUrl', v)}
                type="text"
                description="For migrations and workers"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => testConnection('database')}
                  disabled={testing === 'database'}
                  className="px-4 py-2 bg-secondary border border-border rounded-lg hover:bg-secondary/80"
                >
                  {testing === 'database' ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : testResults.database ? (
                    <CheckCircle className="w-4 h-4 text-green-500" />
                  ) : (
                    'Test Connection'
                  )}
                </button>
              </div>
            </SettingsSection>

            {/* Storage */}
            <SettingsSection title="File Storage" icon={Terminal}>
              <SettingField
                label="Storage Root"
                value={settings.storage.root}
                onChange={(v) => handleChange('storage', 'root', v)}
              />
              <SettingField
                label="RTL Storage"
                value={settings.storage.rtl}
                onChange={(v) => handleChange('storage', 'rtl', v)}
              />
              <SettingField
                label="Test Storage"
                value={settings.storage.tests}
                onChange={(v) => handleChange('storage', 'tests', v)}
              />
              <SettingField
                label="Log Storage"
                value={settings.storage.logs}
                onChange={(v) => handleChange('storage', 'logs', v)}
              />
              <SettingField
                label="Coverage Storage"
                value={settings.storage.coverage}
                onChange={(v) => handleChange('storage', 'coverage', v)}
              />
            </SettingsSection>

            {/* Simulation */}
            <SettingsSection title="Simulation" icon={Terminal}>
              <SettingField
                label="Verilator Path"
                value={settings.simulation.verilatorPath}
                onChange={(v) => handleChange('simulation', 'verilatorPath', v)}
                description="Leave as 'verilator' if in PATH, or provide full path"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => testConnection('verilator')}
                  disabled={testing === 'verilator'}
                  className="px-4 py-2 bg-secondary border border-border rounded-lg hover:bg-secondary/80"
                >
                  {testing === 'verilator' ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : testResults.verilator ? (
                    <CheckCircle className="w-4 h-4 text-green-500" />
                  ) : (
                    'Test Verilator'
                  )}
                </button>
                <button
                  onClick={() => testConnection('icarus')}
                  disabled={testing === 'icarus'}
                  className="px-4 py-2 bg-secondary border border-border rounded-lg hover:bg-secondary/80"
                >
                  {testing === 'icarus' ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : testResults.icarus ? (
                    <CheckCircle className="w-4 h-4 text-green-500" />
                  ) : (
                    'Test Icarus'
                  )}
                </button>
              </div>
              <SettingField
                label="Icarus Verilog Path"
                value={settings.simulation.icarusPath}
                onChange={(v) => handleChange('simulation', 'icarusPath', v)}
              />
              <SettingField
                label="Simulation Timeout (seconds)"
                value={settings.simulation.timeout}
                onChange={(v) => handleChange('simulation', 'timeout', Number(v))}
                type="number"
              />
              <SettingField
                label="Max Concurrent Simulations"
                value={settings.simulation.maxConcurrent}
                onChange={(v) => handleChange('simulation', 'maxConcurrent', Number(v))}
                type="number"
              />
            </SettingsSection>

            {/* AI / LLM */}
            <SettingsSection title="AI / LLM Provider" icon={Brain}>
              <SettingField
                label="Provider"
                value={settings.ai.provider}
                onChange={(v) => handleChange('ai', 'provider', v)}
                type="select"
                options={['mock', 'openai']}
              />
              <SettingField
                label="Model"
                value={settings.ai.model}
                onChange={(v) => handleChange('ai', 'model', v)}
                description="e.g., gpt-4o, gpt-4-turbo, claude-3-opus"
              />
              <SettingField
                label="API Key"
                value={settings.ai.apiKey}
                onChange={(v) => handleChange('ai', 'apiKey', v)}
                type="password"
                description="Leave empty to use mock provider"
                showCopy={true}
                onCopy={() => copyToClipboard(settings.ai.apiKey)}
              />
              <SettingField
                label="Base URL (Optional)"
                value={settings.ai.baseUrl}
                onChange={(v) => handleChange('ai', 'baseUrl', v)}
                description="For OpenAI-compatible APIs (e.g., Azure, local)"
              />
              <SettingField
                label="Temperature"
                value={settings.ai.temperature}
                onChange={(v) => handleChange('ai', 'temperature', Number(v))}
                type="number"
                step="0.1"
                min="0"
                max="2"
              />
              <SettingField
                label="Max Tokens"
                value={settings.ai.maxTokens}
                onChange={(v) => handleChange('ai', 'maxTokens', Number(v))}
                type="number"
              />
              <SettingToggle
                label="AI Enabled"
                checked={settings.ai.enabled}
                onChange={(v) => handleChange('ai', 'enabled', v)}
              />
              <SettingField
                label="Confidence Threshold"
                value={settings.ai.confidenceThreshold}
                onChange={(v) => handleChange('ai', 'confidenceThreshold', Number(v))}
                type="number"
                step="0.1"
                min="0"
                max="1"
              />
              <SettingField
                label="Max Retries"
                value={settings.ai.maxRetries}
                onChange={(v) => handleChange('ai', 'maxRetries', Number(v))}
                type="number"
              />
            </SettingsSection>

            {/* Security */}
            <SettingsSection title="Security" icon={Key}>
              <SettingField
                label="Secret Key"
                value={settings.security.secretKey}
                onChange={(v) => handleChange('security', 'secretKey', v)}
                type="password"
                showCopy={true}
                onCopy={() => copyToClipboard(settings.security.secretKey)}
                description="Use openssl rand -hex 32 to generate"
              />
              <SettingField
                label="Encryption Key (Optional)"
                value={settings.security.encryptionKey}
                onChange={(v) => handleChange('security', 'encryptionKey', v)}
                type="password"
                showCopy={true}
                onCopy={() => copyToClipboard(settings.security.encryptionKey)}
              />
              <SettingToggle
                label="Audit Logging Enabled"
                checked={settings.security.auditLogEnabled}
                onChange={(v) => handleChange('security', 'auditLogEnabled', v)}
              />
              <div className="space-y-2">
                <label className="text-sm text-muted-foreground">CORS Origins</label>
                <div className="space-y-1">
                  {settings.security.corsOrigins.map((origin: string, i: number) => (
                    <div key={i} className="flex gap-2">
                      <input
                        type="text"
                        value={origin}
                        onChange={(e) => {
                          const newOrigins = [...settings.security.corsOrigins];
                          newOrigins[i] = e.target.value;
                          handleChange('security', 'corsOrigins', newOrigins);
                        }}
                        className="flex-1 px-3 py-2 bg-secondary border border-border rounded-lg text-sm"
                      />
                      <button
                        onClick={() => {
                          const newOrigins = settings.security.corsOrigins.filter((_, idx) => idx !== i);
                          handleChange('security', 'corsOrigins', newOrigins);
                        }}
                        className="p-2 text-red-500 hover:text-red-400"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={() => {
                      handleChange('security', 'corsOrigins', [...settings.security.corsOrigins, '']);
                    }}
                    className="px-3 py-1.5 text-sm bg-secondary border border-border rounded-lg hover:bg-secondary/80"
                  >
                    + Add Origin
                  </button>
                </div>
              </div>
            </SettingsSection>
          </div>
        </div>
      </main>
    </div>
  );
}

function SettingsSection({ title, icon: Icon, children }: { title: string; icon: any; children: React.ReactNode }) {
  return (
    <div className="bg-card border border-border rounded-xl p-6">
      <div className="flex items-center gap-2 mb-4">
        <Icon className="w-5 h-5" />
        <h2 className="text-lg font-semibold">{title}</h2>
      </div>
      {children}
    </div>
  );
}

function SettingField({ 
  label, 
  value, 
  onChange, 
  type = 'text', 
  description, 
  disabled,
  showCopy,
  onCopy,
}: any) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">{label}</label>
      <div className="relative">
        {type === 'select' ? (
          <select
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            className="w-full px-3 py-2 bg-secondary border border-border rounded-lg text-sm"
          >
            {description?.options?.map((opt: string) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        ) : (
          <input
            type={type}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
            className={cn(
              'w-full px-3 py-2 bg-secondary border border-border rounded-lg text-sm',
              showCopy && 'pr-10'
            )}
          />
        )}
        {showCopy && (
          <button
            onClick={onCopy}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground"
          >
            <Copy className="w-4 h-4" />
          </button>
        )}
      </div>
      {description && <p className="text-xs text-muted-foreground">{description}</p>}
    </div>
  );
}

function SettingToggle({ label, checked, onChange }: any) {
  return (
    <div className="flex items-center justify-between">
      <label className="text-sm font-medium">{label}</label>
      <button
        onClick={() => onChange(!checked)}
        className={cn(
          'relative w-11 h-6 rounded-full transition-colors',
          checked ? 'bg-primary' : 'bg-secondary border border-border'
        )}
      >
        <span className={cn(
          'absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform',
          checked ? 'translate-x-5' : 'translate-x-0.5'
        )} />
      </button>
    </div>
  );
}