import { useEffect, useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api, ApiError } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Loader2 } from 'lucide-react'

const PROVIDERS = [
  {
    id: 'openai',
    name: 'OpenAI',
    models: [
      'o4-mini',
      'o3',
      'o3-mini',
      'o1',
      'o1-mini',
      'o1-pro',
      'gpt-4.1',
      'gpt-4.1-mini',
      'gpt-4.1-nano',
      'gpt-4o',
      'gpt-4o-mini',
      'gpt-4.5-preview',
      'gpt-4-turbo',
    ],
    color: 'bg-emerald-50 border-emerald-200 dark:bg-emerald-950 dark:border-emerald-800',
    icon: '🤖',
  },
  {
    id: 'azure',
    name: 'Azure OpenAI',
    models: [
      'o4-mini',
      'o3',
      'o3-mini',
      'o1',
      'o1-mini',
      'gpt-4.1',
      'gpt-4.1-mini',
      'gpt-4.1-nano',
      'gpt-4o',
      'gpt-4o-mini',
      'gpt-4-turbo',
    ],
    color: 'bg-blue-50 border-blue-200 dark:bg-blue-950 dark:border-blue-800',
    icon: '☁️',
    needsApiBase: true,
  },
  {
    id: 'gemini',
    name: 'Google Gemini',
    models: [
      'gemini-2.5-pro',
      'gemini-2.5-flash',
      'gemini-2.0-flash',
      'gemini-2.0-flash-lite',
      'gemini-1.5-pro',
      'gemini-1.5-flash',
    ],
    color: 'bg-amber-50 border-amber-200 dark:bg-amber-950 dark:border-amber-800',
    icon: '✨',
  },
  {
    id: 'anthropic',
    name: 'Anthropic Claude',
    models: [
      'claude-opus-4-20250514',
      'claude-sonnet-4-20250514',
      'claude-haiku-35-20250620',
      'claude-3.5-sonnet-20241022',
      'claude-3-opus-20240229',
    ],
    color: 'bg-orange-50 border-orange-200 dark:bg-orange-950 dark:border-orange-800',
    icon: '🧠',
  },
] as const

interface SettingsResponse {
  provider: string
  model: string
  has_api_key: boolean
  api_base: string
}

interface TestResult {
  success: boolean
  message: string
}

export function SettingsPage() {
  const [selectedProvider, setSelectedProvider] = useState('')
  const [model, setModel] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [apiBase, setApiBase] = useState('')
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
  const [testMessage, setTestMessage] = useState('')
  const [saving, setSaving] = useState(false)
  const [isConfigured, setIsConfigured] = useState(false)

  useEffect(() => {
    api<SettingsResponse>('/settings')
      .then((s) => {
        if (s.has_api_key && s.provider) {
          setSelectedProvider(s.provider)
          setModel(s.model)
          setApiBase(s.api_base || '')
          setIsConfigured(true)
        }
      })
      .catch(() => {})
  }, [])

  const currentProvider = PROVIDERS.find((p) => p.id === selectedProvider)

  async function handleTest() {
    setTestStatus('testing')
    setTestMessage('')
    try {
      const result = await api<TestResult>('/settings/test', {
        method: 'POST',
        body: JSON.stringify({
          provider: selectedProvider,
          model,
          api_key: apiKey,
          api_base: apiBase,
        }),
      })
      setTestStatus(result.success ? 'success' : 'error')
      setTestMessage(result.message)
    } catch (err) {
      setTestStatus('error')
      setTestMessage(err instanceof Error ? err.message : 'שגיאה לא צפויה')
    }
  }

  async function handleSave() {
    setSaving(true)
    try {
      await api<SettingsResponse>('/settings', {
        method: 'POST',
        body: JSON.stringify({
          provider: selectedProvider,
          model,
          api_key: apiKey,
          api_base: apiBase,
        }),
      })
      setIsConfigured(true)
      setApiKey('')
      setTestStatus('success')
      setTestMessage('ההגדרות נשמרו בהצלחה ✓')
    } catch (err) {
      setTestStatus('error')
      setTestMessage(err instanceof ApiError ? err.message : 'שגיאה בשמירה')
    } finally {
      setSaving(false)
    }
  }

  function handleProviderSelect(providerId: string) {
    setSelectedProvider(providerId)
    setTestStatus('idle')
    setTestMessage('')
    const provider = PROVIDERS.find((p) => p.id === providerId)
    if (provider && provider.models.length > 0) {
      setModel(provider.models[0])
    }
    if (providerId !== 'azure') {
      setApiBase('')
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">הגדרות LLM</h1>
        <p className="text-muted-foreground mt-1">בחר ספק שירות והזן את פרטי ההתחברות</p>
      </div>

      {/* Provider cards */}
      <div className="grid grid-cols-2 gap-4">
        {PROVIDERS.map((provider) => (
          <Card
            key={provider.id}
            className={cn(
              'cursor-pointer transition-all border-2',
              provider.color,
              selectedProvider === provider.id
                ? 'ring-2 ring-primary shadow-md'
                : 'hover:shadow-sm'
            )}
            onClick={() => handleProviderSelect(provider.id)}
          >
            <CardContent className="flex items-center gap-3 p-4">
              <span className="text-3xl">{provider.icon}</span>
              <span className="font-semibold">{provider.name}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Configuration form */}
      {selectedProvider && currentProvider && (
        <Card>
          <CardContent className="space-y-4 p-6">
            {/* Model selector */}
            <div className="space-y-2">
              <Label htmlFor="model">מודל</Label>
              <input
                id="model"
                list={`models-${selectedProvider}`}
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="בחר מודל"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-base shadow-xs transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 md:text-sm"
              />
              <datalist id={`models-${selectedProvider}`}>
                {currentProvider.models.map((m) => (
                  <option key={m} value={m} />
                ))}
              </datalist>
            </div>

            {/* API Key */}
            <div className="space-y-2">
              <Label htmlFor="apiKey">API Key</Label>
              <Input
                id="apiKey"
                type="password"
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value)
                  setTestStatus('idle')
                  setTestMessage('')
                }}
                placeholder="הזן API Key"
              />
              {isConfigured && !apiKey && (
                <p className="text-sm text-muted-foreground">מפתח שמור — השאר ריק לשמירת הקיים</p>
              )}
            </div>

            {/* Azure endpoint */}
            {'needsApiBase' in currentProvider && currentProvider.needsApiBase && (
              <div className="space-y-2">
                <Label htmlFor="apiBase">Endpoint URL</Label>
                <Input
                  id="apiBase"
                  value={apiBase}
                  onChange={(e) => setApiBase(e.target.value)}
                  placeholder="https://your-resource.openai.azure.com/"
                  dir="ltr"
                />
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-3 pt-2">
              <Button
                onClick={handleTest}
                variant="outline"
                disabled={testStatus === 'testing' || !model || (!apiKey && !isConfigured)}
              >
                {testStatus === 'testing' && <Loader2 className="h-4 w-4 animate-spin me-2" />}
                בדיקת חיבור
              </Button>
              <Button
                onClick={handleSave}
                disabled={testStatus !== 'success' || saving}
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin me-2" />}
                שמור הגדרות
              </Button>
            </div>

            {/* Inline status */}
            {testMessage && (
              <p
                className={cn(
                  'text-sm font-medium',
                  testStatus === 'success' ? 'text-green-600' : 'text-red-600'
                )}
              >
                {testStatus === 'success' ? '✓' : '✗'} {testMessage}
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
