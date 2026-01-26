import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { Eye, EyeOff, Save, Check, AlertCircle, Copy, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

import { loadSettings, saveSettings, type APISettings } from '@/lib/settings';
import { API_ENDPOINTS, API_TIMEOUT } from '@/config';

export const SettingsForm = () => {
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const { register, handleSubmit, setValue, getValues, watch } = useForm<APISettings>({
    defaultValues: loadSettings()
  });

  const apiKey = watch('openai_api_key');

  useEffect(() => {
    // 从 localStorage 加载设置
    const settings = loadSettings();
    setValue('openai_api_key', settings.openai_api_key);
    setValue('model_name', settings.model_name);
    setValue('api_base', settings.api_base);
  }, [setValue]);

  const onSubmit = async (data: APISettings) => {
    setIsSaving(true);
    setTestResult(null);

    try {
      // 保存到 localStorage
      saveSettings(data);
      toast.success('设置已保存到本地');
    } catch (error) {
      console.error('Error saving settings:', error);
      toast.error('保存失败');
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    const data = getValues();

    if (!data.openai_api_key) {
      toast.error('请先输入 API Key');
      setIsTesting(false);
      return;
    }

    try {
      const response = await fetch(API_ENDPOINTS.TEST_CONNECTION, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: data.openai_api_key,
          api_base: data.api_base,
          model_name: data.model_name
        }),
      });

      const result = await response.json();

      if (result.status === 'success') {
        setTestResult({ success: true, message: '连接测试成功！配置已保存。' });
        toast.success('连接测试成功');
        // 测试成功后自动保存
        saveSettings(data);
      } else {
        setTestResult({ success: false, message: result.message || '连接测试失败' });
        toast.error('连接测试失败');
      }
    } catch (error) {
      setTestResult({ success: false, message: '网络错误或无法连接到后端' });
      toast.error('连接测试失败');
    } finally {
      setIsTesting(false);
    }
  };

  const copyToClipboard = () => {
    if (apiKey) {
      navigator.clipboard.writeText(apiKey);
      toast.success('API Key 已复制');
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>API 配置</CardTitle>
        <CardDescription>
          配置你的 AI 模型 API（豆包、通义千问等兼容 OpenAI API 的服务）
        </CardDescription>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* API Key */}
          <div className="space-y-2">
            <Label htmlFor="api_key">API Key *</Label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Input
                  id="api_key"
                  type={showApiKey ? 'text' : 'password'}
                  placeholder="输入你的 API Key"
                  {...register('openai_api_key', { required: true })}
                  className="pr-20"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-2 top-1/2 -translate-y-1/2 h-7 px-2"
                  onClick={() => setShowApiKey(!showApiKey)}
                >
                  {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
              <Button
                type="button"
                variant="outline"
                size="icon"
                onClick={copyToClipboard}
                disabled={!apiKey}
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Model Name */}
          <div className="space-y-2">
            <Label htmlFor="model_name">模型名称 *</Label>
            <Input
              id="model_name"
              placeholder="例如: ep-20241022000000-xxxxx 或 qwen-plus"
              {...register('model_name', { required: true })}
            />
            <p className="text-sm text-muted-foreground">
              豆包使用类似 ep-xxxxx 的端点 ID，通义千问使用 qwen-plus 等
            </p>
          </div>

          {/* API Base */}
          <div className="space-y-2">
            <Label htmlFor="api_base">API 地址 *</Label>
            <Input
              id="api_base"
              placeholder="https://ark.cn-beijing.volces.com/api/v3"
              {...register('api_base', { required: true })}
            />
            <p className="text-sm text-muted-foreground">
              豆包: https://ark.cn-beijing.volces.com/api/v3
            </p>
          </div>

          {/* Test Result Alert */}
          {testResult && (
            <Alert variant={testResult.success ? 'default' : 'destructive'}>
              {testResult.success ? (
                <Check className="h-4 w-4" />
              ) : (
                <AlertCircle className="h-4 w-4" />
              )}
              <AlertTitle>
                {testResult.success ? '连接成功' : '连接失败'}
              </AlertTitle>
              <AlertDescription>{testResult.message}</AlertDescription>
            </Alert>
          )}
        </form>
      </CardContent>

      <CardFooter className="flex gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={handleTestConnection}
          disabled={isTesting}
        >
          {isTesting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          测试连接
        </Button>
        <Button
          type="submit"
          onClick={handleSubmit(onSubmit)}
          disabled={isSaving}
        >
          {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          保存设置
        </Button>
      </CardFooter>
    </Card>
  );
};
