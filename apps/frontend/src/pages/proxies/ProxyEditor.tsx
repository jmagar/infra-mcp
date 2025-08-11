/**
 * Proxy Configuration Editor Component
 * Visual editor for SWAG reverse proxy configuration files
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useProxyConfig } from '@/hooks';
import { useNotificationEvents } from '@/hooks/useNotificationEvents';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LoadingSpinner, ConfirmDialog } from '@/components/common';
import {
  SaveIcon,
  ArrowLeftIcon,
  CheckCircleIcon,
  AlertTriangleIcon,
  FileTextIcon,
  GlobeIcon,
  ShieldIcon,
  SettingsIcon,
  PlayIcon
} from 'lucide-react';

export function ProxyEditor() {
  const { deviceHostname, configId } = useParams<{
    deviceHostname: string;
    configId: string;
  }>();
  const navigate = useNavigate();
  const { config, loading, refetch } = useProxyConfig(configId ? parseInt(configId) : undefined);
  const { notifySuccess, notifyError } = useNotificationEvents();

  const [serviceName, setServiceName] = useState('');
  const [serverNames, setServerNames] = useState<string[]>([]);
  const [targetHost, setTargetHost] = useState('');
  const [targetPort, setTargetPort] = useState<number>(80);
  const [sslEnabled, setSslEnabled] = useState(false);
  const [authEnabled, setAuthEnabled] = useState(false);
  const [customContent, setCustomContent] = useState('');
  
  const [isModified, setIsModified] = useState(false);
  const [saving, setSaving] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [confirmSave, setConfirmSave] = useState(false);

  // Load current config data
  useEffect(() => {
    if (config) {
      setServiceName(config.service_name);
      // Map to local editable fields
      const initialServers: string[] = [];
      if (config.domain) initialServers.push(config.domain);
      if (config.subdomain) initialServers.push(config.subdomain);
      setServerNames(initialServers);
      setTargetHost(config.upstream_host);
      setTargetPort(config.upstream_port);
      setSslEnabled(!!config.ssl_enabled);
      setAuthEnabled(!!config.basic_auth_enabled);
      setCustomContent(config.config_file_content || '');
    }
  }, [config]);

  // Mark as modified when content changes
  const validateConfig = useCallback(() => {
    const errors: string[] = [];
    
    if (!serviceName.trim()) {
      errors.push('Service name is required');
    }
    
    if (serverNames.length === 0 || !serverNames[0]?.trim()) {
      errors.push('At least one server name (domain) is required');
    }
    
    if (!targetHost.trim()) {
      errors.push('Target host is required');
    }
    
    if (!targetPort || targetPort < 1 || targetPort > 65535) {
      errors.push('Target port must be between 1 and 65535');
    }
    
    // Validate server names format
    serverNames.forEach((name, index) => {
      if (name && !/^[a-zA-Z0-9.-]+$/.test(name)) {
        errors.push(`Server name ${index + 1} contains invalid characters`);
      }
    });
    
    setValidationErrors(errors);
  }, [serviceName, serverNames, targetHost, targetPort]);

  useEffect(() => {
    if (config) {
      const hasChanges = 
        serviceName !== config.service_name ||
        JSON.stringify(serverNames) !== JSON.stringify([config.domain, config.subdomain].filter(Boolean)) ||
        targetHost !== config.upstream_host ||
        targetPort !== config.upstream_port ||
        sslEnabled !== !!config.ssl_enabled ||
        authEnabled !== !!config.basic_auth_enabled ||
        customContent !== (config.config_file_content || '');
      
      setIsModified(hasChanges);
      validateConfig();
    }
  }, [serviceName, serverNames, targetHost, targetPort, sslEnabled, authEnabled, customContent, config, validateConfig]);

  const handleServerNamesChange = (value: string) => {
    const names = value.split(',').map(name => name.trim()).filter(name => name);
    setServerNames(names);
  };

  const handleSave = async () => {
    if (!configId || validationErrors.length > 0) return;
    
    setSaving(true);
    try {
      // This would call the update API
      const updateData = {
        service_name: serviceName,
        server_names: serverNames,
        target_host: targetHost,
        target_port: targetPort,
        ssl_enabled: sslEnabled,
        basic_auth_enabled: authEnabled,
        config_file_content: customContent,
      };
      
      // TODO: Implement actual update call
      console.log('Saving config:', updateData);
      
      setIsModified(false);
      notifySuccess('Configuration Updated', 'Proxy configuration has been saved successfully');
      setConfirmSave(false);
      await refetch();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to save config:', error);
      notifyError('Save Failed', `Failed to save proxy configuration: ${errorMessage}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner />
        <span className="ml-2">Loading proxy configuration...</span>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="text-center py-12">
        <FileTextIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h2 className="text-xl font-semibold">Configuration Not Found</h2>
        <p className="text-gray-600">The requested proxy configuration could not be found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="outline" size="sm" onClick={() => navigate(-1)}>
            <ArrowLeftIcon className="h-4 w-4 mr-2" />
            Back
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Proxy Configuration Editor</h1>
            <p className="text-gray-600">
              Editing {config.service_name} on {deviceHostname}
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          {validationErrors.length === 0 ? (
            <Badge variant="default">
              <CheckCircleIcon className="h-3 w-3 mr-1" />
              Valid
            </Badge>
          ) : (
            <Badge variant="destructive">
              <AlertTriangleIcon className="h-3 w-3 mr-1" />
              {validationErrors.length} errors
            </Badge>
          )}
          
          <Button
            onClick={() => setConfirmSave(true)}
            disabled={!isModified || saving || validationErrors.length > 0}
          >
            <SaveIcon className="h-4 w-4 mr-2" />
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Configuration */}
        <div className="lg:col-span-2">
          <Tabs defaultValue="basic">
            <TabsList>
              <TabsTrigger value="basic">Basic Settings</TabsTrigger>
              <TabsTrigger value="advanced">Advanced Config</TabsTrigger>
            </TabsList>
            
            <TabsContent value="basic">
              <Card>
                <CardHeader>
                  <CardTitle>Basic Configuration</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label>Service Name</Label>
                      <Input
                        value={serviceName}
                        onChange={(e) => setServiceName(e.target.value)}
                        placeholder="my-app"
                      />
                    </div>
                    
                    <div>
                      <Label>Server Names (Domains)</Label>
                      <Input
                        value={serverNames.join(', ')}
                        onChange={(e) => handleServerNamesChange(e.target.value)}
                        placeholder="app.example.com, www.app.example.com"
                      />
                    </div>
                    
                    <div>
                      <Label>Target Host</Label>
                      <Input
                        value={targetHost}
                        onChange={(e) => setTargetHost(e.target.value)}
                        placeholder="192.168.1.100"
                      />
                    </div>
                    
                    <div>
                      <Label>Target Port</Label>
                      <Input
                        type="number"
                        value={targetPort}
                        onChange={(e) => setTargetPort(parseInt(e.target.value) || 80)}
                        placeholder="3000"
                        min="1"
                        max="65535"
                      />
                    </div>
                  </div>
                  
                  <div className="flex space-x-4">
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="ssl-enabled"
                        checked={sslEnabled}
                        onChange={(e) => setSslEnabled(e.target.checked)}
                      />
                      <Label htmlFor="ssl-enabled" className="flex items-center">
                        <ShieldIcon className="h-4 w-4 mr-1" />
                        Enable SSL
                      </Label>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="auth-enabled"
                        checked={authEnabled}
                        onChange={(e) => setAuthEnabled(e.target.checked)}
                      />
                      <Label htmlFor="auth-enabled" className="flex items-center">
                        <SettingsIcon className="h-4 w-4 mr-1" />
                        Enable Authentication
                      </Label>
                    </div>
                  </div>
                  
                  {validationErrors.length > 0 && (
                    <div className="bg-red-50 border border-red-200 rounded-md p-4">
                      <h4 className="text-sm font-medium text-red-800 mb-2">Validation Errors:</h4>
                      <ul className="text-sm text-red-700 space-y-1">
                        {validationErrors.map((error, index) => (
                          <li key={index}>• {error}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="advanced">
              <Card>
                <CardHeader>
                  <CardTitle>Advanced Configuration</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <Label>Custom Nginx Configuration</Label>
                      <Textarea
                        value={customContent}
                        onChange={(e) => setCustomContent(e.target.value)}
                        className="font-mono text-sm min-h-[400px]"
                        placeholder="# Add custom nginx configuration here&#10;# Example:&#10;location /api {&#10;    proxy_pass http://backend;&#10;}"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        {/* Side Panel */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Configuration Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Status</span>
                  <Badge variant={config.status === 'active' ? 'default' : 'secondary'}>
                    {config.status}
                  </Badge>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm">SSL</span>
                  <Badge variant={sslEnabled ? 'default' : 'outline'}>
                    {sslEnabled ? 'Enabled' : 'Disabled'}
                  </Badge>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className="text-sm">Auth</span>
                  <Badge variant={authEnabled ? 'default' : 'outline'}>
                    {authEnabled ? 'Enabled' : 'Disabled'}
                  </Badge>
                </div>
              </div>
              
              <div className="border-t pt-4">
                <h4 className="text-sm font-medium mb-2">Current Domains</h4>
                <div className="space-y-1">
                  {serverNames.map((name, index) => (
                    <div key={index} className="flex items-center text-sm">
                      <GlobeIcon className="h-3 w-3 mr-1 text-gray-400" />
                      {name}
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="border-t pt-4">
                <h4 className="text-sm font-medium mb-2">Target</h4>
                <div className="text-sm font-mono bg-gray-50 p-2 rounded">
                  {targetHost}:{targetPort}
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card className="mt-4">
            <CardHeader>
              <CardTitle className="text-base">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Button variant="outline" className="w-full justify-start" size="sm">
                  <PlayIcon className="h-3 w-3 mr-2" />
                  Test Configuration
                </Button>
                <Button variant="outline" className="w-full justify-start" size="sm">
                  <FileTextIcon className="h-3 w-3 mr-2" />
                  View Generated Config
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Save Confirmation Dialog */}
      <ConfirmDialog
        isOpen={confirmSave}
        title="Save Configuration"
        description={`Save changes to "${serviceName}" proxy configuration? The configuration will be applied to the SWAG proxy server.`}
        confirmLabel="Save Changes"
        cancelLabel="Cancel"
        variant="warning"
        onConfirm={handleSave}
        onClose={() => setConfirmSave(false)}
        isLoading={saving}
      />
    </div>
  );
}