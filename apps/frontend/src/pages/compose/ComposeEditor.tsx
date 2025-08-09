/**
 * Docker Compose Editor Component
 * Visual editor for docker-compose.yml files with validation and deployment
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useCompose } from '@/hooks/useCompose';
import { useDevices } from '@/hooks/useDevices';
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
  FileTextIcon,
  SaveIcon,
  PlayIcon,
  EyeIcon,
  NetworkIcon,
  ZapIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  ArrowLeftIcon,
  SettingsIcon,
  ServerIcon
} from 'lucide-react';

export function ComposeEditor() {
  const { deviceHostname, stackName } = useParams<{
    deviceHostname: string;
    stackName: string;
  }>();
  const navigate = useNavigate();
  const { composeStacks, loading, modifyStack, deployStack, scanPorts, scanNetworks } = useCompose();
  const { devices } = useDevices();
  const { notifyComposeAction } = useNotificationEvents();

  const [content, setContent] = useState('');
  const [deployPath, setDeployPath] = useState('');
  const [targetDevice, setTargetDevice] = useState(deviceHostname || '');
  const [isModified, setIsModified] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [availablePorts, setAvailablePorts] = useState<number[]>([]);
  const [availableNetworks, setAvailableNetworks] = useState<string[]>([]);
  const [scanningResources, setScanningResources] = useState(false);

  const [confirmDeploy, setConfirmDeploy] = useState(false);

  // Load current stack data
  useEffect(() => {
    if (stackName && composeStacks.length > 0) {
      const currentStack = composeStacks.find(
        s => s.name === stackName && s.device_hostname === deviceHostname
      );
      
      if (currentStack) {
        setContent(currentStack.compose_content || '');
        setDeployPath(currentStack.path || '');
        setTargetDevice(currentStack.device_hostname);
      }
    }
  }, [stackName, deviceHostname, composeStacks]);

  // Mark as modified when content changes
  useEffect(() => {
    if (content) {
      setIsModified(true);
      validateCompose(content);
    }
  }, [content, deployPath, targetDevice]);

  const validateCompose = (yamlContent: string) => {
    const errors: string[] = [];
    
    // Basic YAML structure validation
    if (!yamlContent.trim()) {
      errors.push('Compose file cannot be empty');
      setValidationErrors(errors);
      return;
    }
    
    try {
      // Check for required fields
      if (!yamlContent.includes('version:')) {
        errors.push('Missing "version" field in compose file');
      }
      if (!yamlContent.includes('services:')) {
        errors.push('Missing "services" section in compose file');
      }
      
      // Check for common issues
      if (yamlContent.includes('image:') && !yamlContent.match(/image:\s*\S+/)) {
        errors.push('Service image appears to be empty');
      }
      
    } catch (error) {
      errors.push('Invalid YAML syntax');
    }
    
    setValidationErrors(errors);
  };

  const handleSave = async () => {
    if (!stackName || !deviceHostname) return;
    
    setSaving(true);
    try {
      await modifyStack(deviceHostname, stackName, content, targetDevice);
      setIsModified(false);
      notifyComposeAction('modify', stackName, targetDevice, true);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to save compose:', error);
      notifyComposeAction('modify', stackName, targetDevice, false, errorMessage);
    } finally {
      setSaving(false);
    }
  };

  const handleDeploy = async () => {
    if (!stackName) return;
    
    setDeploying(true);
    try {
      await deployStack(targetDevice, stackName, content, deployPath);
      setIsModified(false);
      notifyComposeAction('deploy', stackName, targetDevice, true);
      setConfirmDeploy(false);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Failed to deploy compose:', error);
      notifyComposeAction('deploy', stackName, targetDevice, false, errorMessage);
    } finally {
      setDeploying(false);
    }
  };

  const handleScanResources = async () => {
    if (!targetDevice) return;
    
    setScanningResources(true);
    try {
      const [portsResponse, networksResponse] = await Promise.all([
        scanPorts(targetDevice),
        scanNetworks(targetDevice)
      ]);
      
      setAvailablePorts(portsResponse.data.available_ports || []);
      setAvailableNetworks(networksResponse.data.networks || []);
    } catch (error) {
      console.error('Failed to scan resources:', error);
    } finally {
      setScanningResources(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner />
        <span className="ml-2">Loading compose editor...</span>
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
            <h1 className="text-2xl font-bold">Compose Editor</h1>
            <p className="text-gray-600">
              Editing {stackName} on {deviceHostname}
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
            variant="outline"
            onClick={handleSave}
            disabled={!isModified || saving || validationErrors.length > 0}
          >
            <SaveIcon className="h-4 w-4 mr-2" />
            {saving ? 'Saving...' : 'Save'}
          </Button>
          
          <Button
            onClick={() => setConfirmDeploy(true)}
            disabled={validationErrors.length > 0 || deploying}
          >
            <PlayIcon className="h-4 w-4 mr-2" />
            {deploying ? 'Deploying...' : 'Deploy'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Editor */}
        <div className="lg:col-span-3">
          <Card>
            <CardHeader>
              <CardTitle>Docker Compose Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label>Target Device</Label>
                    <select
                      value={targetDevice}
                      onChange={(e) => setTargetDevice(e.target.value)}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    >
                      {devices?.map(device => (
                        <option key={device.hostname} value={device.hostname}>
                          {device.hostname}
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <Label>Deployment Path (optional)</Label>
                    <Input
                      value={deployPath}
                      onChange={(e) => setDeployPath(e.target.value)}
                      placeholder="/opt/docker/my-app"
                    />
                  </div>
                </div>
                
                <div>
                  <Label>Docker Compose Content</Label>
                  <Textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    className="font-mono text-sm min-h-[600px]"
                    placeholder="version: '3.8'&#10;services:&#10;  app:&#10;    image: nginx&#10;    ports:&#10;      - '80:80'"
                  />
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
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Side Panel */}
        <div className="lg:col-span-1">
          <Tabs defaultValue="resources">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="resources">Resources</TabsTrigger>
              <TabsTrigger value="help">Help</TabsTrigger>
            </TabsList>
            
            <TabsContent value="resources" className="space-y-4">
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">Available Resources</CardTitle>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleScanResources}
                      disabled={scanningResources}
                    >
                      <SettingsIcon className="h-3 w-3 mr-1" />
                      {scanningResources ? 'Scanning...' : 'Scan'}
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <h4 className="text-sm font-medium flex items-center">
                      <ZapIcon className="h-3 w-3 mr-1" />
                      Available Ports
                    </h4>
                    <div className="mt-2">
                      {availablePorts.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {availablePorts.slice(0, 10).map(port => (
                            <Badge key={port} variant="outline" className="text-xs">
                              {port}
                            </Badge>
                          ))}
                          {availablePorts.length > 10 && (
                            <Badge variant="outline" className="text-xs">
                              +{availablePorts.length - 10}
                            </Badge>
                          )}
                        </div>
                      ) : (
                        <p className="text-xs text-gray-500">
                          Click scan to find available ports
                        </p>
                      )}
                    </div>
                  </div>
                  
                  <div>
                    <h4 className="text-sm font-medium flex items-center">
                      <NetworkIcon className="h-3 w-3 mr-1" />
                      Docker Networks
                    </h4>
                    <div className="mt-2">
                      {availableNetworks.length > 0 ? (
                        <div className="space-y-1">
                          {availableNetworks.slice(0, 5).map(network => (
                            <Badge key={network} variant="outline" className="text-xs block">
                              {network}
                            </Badge>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-gray-500">
                          Click scan to find available networks
                        </p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="help">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Quick Reference</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4 text-xs">
                    <div>
                      <h4 className="font-medium">Basic Structure</h4>
                      <pre className="mt-1 bg-gray-50 p-2 rounded text-xs">
{`version: '3.8'
services:
  app:
    image: nginx
    ports:
      - "80:80"`}
                      </pre>
                    </div>
                    
                    <div>
                      <h4 className="font-medium">Common Patterns</h4>
                      <ul className="mt-1 space-y-1 text-gray-600">
                        <li>• Use environment variables</li>
                        <li>• Define volumes for persistence</li>
                        <li>• Set restart policies</li>
                        <li>• Configure networks</li>
                      </ul>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Deploy Confirmation Dialog */}
      <ConfirmDialog
        isOpen={confirmDeploy}
        title="Deploy Compose Stack"
        description={`Deploy "${stackName}" to ${targetDevice}? This will stop existing containers and start the updated configuration.`}
        confirmText="Deploy Stack"
        cancelText="Cancel"
        variant="default"
        onConfirm={handleDeploy}
        onCancel={() => setConfirmDeploy(false)}
        isLoading={deploying}
      />
    </div>
  );
}