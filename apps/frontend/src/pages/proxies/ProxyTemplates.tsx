/**
 * Proxy Templates Component
 * Browse and apply pre-built proxy configuration templates
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
// import { useProxyTemplates } from '@/hooks'; // TODO: Implement when backend is ready
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { LoadingSpinner, ConfirmDialog } from '@/components/common';
import { DynamicFormModal } from '@/components/common/DynamicFormModal';
import {
  FileTextIcon,
  SearchIcon,
  PlayIcon,
  EyeIcon,
  ArrowLeftIcon,
  TagIcon,
  BookOpenIcon,
  SettingsIcon,
  ShieldIcon,
  GlobeIcon
} from 'lucide-react';

interface ProxyTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  config_content: string;
  ssl_enabled: boolean;
  auth_enabled: boolean;
  requires_config: boolean;
  config_fields?: {
    name: string;
    label: string;
    type: string;
    required: boolean;
    placeholder?: string;
  }[];
}

export function ProxyTemplates() {
  const navigate = useNavigate();
  // const { templates, loading } = useProxyTemplates(); // TODO: Implement when backend is ready
  const templates: any[] = []; // Mock empty array for now
  const loading = false;
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [selectedTemplate, setSelectedTemplate] = useState<ProxyTemplate | null>(null);
  const [previewModal, setPreviewModal] = useState(false);
  const [applyModal, setApplyModal] = useState<{
    isOpen: boolean;
    isLoading: boolean;
  }>({
    isOpen: false,
    isLoading: false,
  });

  // Mock templates data for now (until backend is ready)
  const mockTemplates: ProxyTemplate[] = [
    {
      id: '1',
      name: 'Basic Web Application',
      description: 'Simple reverse proxy for web applications with optional SSL',
      category: 'Web Apps',
      tags: ['basic', 'web', 'ssl'],
      config_content: `server {
    listen 443 ssl http2;
    server_name {{DOMAIN}};
    
    location / {
        proxy_pass http://{{TARGET_HOST}}:{{TARGET_PORT}};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}`,
      ssl_enabled: true,
      auth_enabled: false,
      requires_config: true,
      config_fields: [
        { name: 'domain', label: 'Domain', type: 'text', required: true, placeholder: 'app.example.com' },
        { name: 'target_host', label: 'Target Host', type: 'text', required: true, placeholder: '192.168.1.100' },
        { name: 'target_port', label: 'Target Port', type: 'text', required: true, placeholder: '3000' },
      ]
    },
    {
      id: '2',
      name: 'API Gateway',
      description: 'API proxy with rate limiting and authentication',
      category: 'APIs',
      tags: ['api', 'auth', 'rate-limiting'],
      config_content: `server {
    listen 443 ssl http2;
    server_name {{DOMAIN}};
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    location /api {
        limit_req zone=api burst=20 nodelay;
        auth_basic "API Access";
        auth_basic_user_file /config/nginx/.htpasswd;
        
        proxy_pass http://{{TARGET_HOST}}:{{TARGET_PORT}};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}`,
      ssl_enabled: true,
      auth_enabled: true,
      requires_config: true,
      config_fields: [
        { name: 'domain', label: 'API Domain', type: 'text', required: true, placeholder: 'api.example.com' },
        { name: 'target_host', label: 'Backend Host', type: 'text', required: true, placeholder: '192.168.1.200' },
        { name: 'target_port', label: 'Backend Port', type: 'text', required: true, placeholder: '8080' },
      ]
    },
    {
      id: '3',
      name: 'Static Website',
      description: 'Host static files with caching and compression',
      category: 'Static',
      tags: ['static', 'cache', 'gzip'],
      config_content: `server {
    listen 443 ssl http2;
    server_name {{DOMAIN}};
    
    root /config/www/{{SITE_NAME}};
    index index.html;
    
    # Enable gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    
    # Cache static assets
    location ~* \\.(jpg|jpeg|png|gif|ico|css|js)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location / {
        try_files $uri $uri/ =404;
    }
}`,
      ssl_enabled: true,
      auth_enabled: false,
      requires_config: true,
      config_fields: [
        { name: 'domain', label: 'Domain', type: 'text', required: true, placeholder: 'site.example.com' },
        { name: 'site_name', label: 'Site Directory Name', type: 'text', required: true, placeholder: 'my-site' },
      ]
    },
    {
      id: '4',
      name: 'Docker Registry',
      description: 'Secure proxy for Docker registry with authentication',
      category: 'Development',
      tags: ['docker', 'registry', 'auth'],
      config_content: `server {
    listen 443 ssl http2;
    server_name {{DOMAIN}};
    
    client_max_body_size 0;
    chunked_transfer_encoding on;
    
    auth_basic "Docker Registry";
    auth_basic_user_file /config/nginx/.htpasswd;
    
    location / {
        proxy_pass http://{{TARGET_HOST}}:{{TARGET_PORT}};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }
}`,
      ssl_enabled: true,
      auth_enabled: true,
      requires_config: true,
      config_fields: [
        { name: 'domain', label: 'Registry Domain', type: 'text', required: true, placeholder: 'registry.example.com' },
        { name: 'target_host', label: 'Registry Host', type: 'text', required: true, placeholder: '192.168.1.150' },
        { name: 'target_port', label: 'Registry Port', type: 'text', required: true, placeholder: '5000' },
      ]
    },
  ];

  // Use mock data for now
  const allTemplates = templates.length > 0 ? templates : mockTemplates;

  // Filter templates based on search and category
  const filteredTemplates = allTemplates.filter(template => {
    if (categoryFilter !== 'all' && template.category !== categoryFilter) return false;
    if (searchTerm && !template.name.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !template.description.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !template.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))) return false;
    return true;
  });

  // Get unique categories
  const categories = [...new Set(allTemplates.map(t => t.category))];

  const handlePreviewTemplate = (template: ProxyTemplate) => {
    setSelectedTemplate(template);
    setPreviewModal(true);
  };

  const handleApplyTemplate = (template: ProxyTemplate) => {
    setSelectedTemplate(template);
    setApplyModal({ isOpen: true, isLoading: false });
  };

  const handleCreateFromTemplate = async (data: Record<string, string>) => {
    if (!selectedTemplate) return;
    
    setApplyModal(prev => ({ ...prev, isLoading: true }));
    
    try {
      // Replace template variables with user inputs
      let configContent = selectedTemplate.config_content;
      Object.entries(data).forEach(([key, value]) => {
        const placeholder = `{{${key.toUpperCase()}}}`;
        configContent = configContent.replace(new RegExp(placeholder, 'g'), value);
      });
      
      // TODO: Create new proxy config with template data
      console.log('Creating config from template:', {
        template: selectedTemplate,
        data,
        finalConfig: configContent
      });
      
      setApplyModal({ isOpen: false, isLoading: false });
      navigate('/proxies');
    } catch (error) {
      console.error('Failed to create config from template:', error);
      setApplyModal(prev => ({ ...prev, isLoading: false }));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner />
        <span className="ml-2">Loading proxy templates...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="outline" size="sm" onClick={() => navigate('/proxies')}>
            <ArrowLeftIcon className="h-4 w-4 mr-2" />
            Back to Configs
          </Button>
          <div>
            <h1 className="text-2xl font-bold">Proxy Templates</h1>
            <p className="text-gray-600">
              Choose from pre-built configurations for common use cases
            </p>
          </div>
        </div>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Find Templates</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <Label htmlFor="search" className="text-xs">Search Templates</Label>
              <Input
                id="search"
                placeholder="Search by name, description, or tags..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="mt-1"
              />
            </div>
            
            <div>
              <Label className="text-xs">Category</Label>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="flex h-10 w-40 rounded-md border border-input bg-background px-3 py-2 text-sm mt-1"
              >
                <option value="all">All Categories</option>
                {categories.map(category => (
                  <option key={category} value={category}>{category}</option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Templates Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {filteredTemplates.map((template) => (
          <Card key={template.id} className="flex flex-col">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-lg">{template.name}</CardTitle>
                  <Badge variant="outline" className="mt-1 text-xs">
                    {template.category}
                  </Badge>
                </div>
                <FileTextIcon className="h-5 w-5 text-gray-400" />
              </div>
            </CardHeader>
            
            <CardContent className="flex-1 flex flex-col">
              <p className="text-sm text-gray-600 mb-4 flex-1">
                {template.description}
              </p>
              
              {/* Features */}
              <div className="flex flex-wrap gap-1 mb-4">
                {template.ssl_enabled && (
                  <Badge variant="secondary" className="text-xs">
                    <ShieldIcon className="h-2 w-2 mr-1" />
                    SSL
                  </Badge>
                )}
                {template.auth_enabled && (
                  <Badge variant="secondary" className="text-xs">
                    <SettingsIcon className="h-2 w-2 mr-1" />
                    Auth
                  </Badge>
                )}
              </div>
              
              {/* Tags */}
              <div className="flex flex-wrap gap-1 mb-4">
                {template.tags.map((tag) => (
                  <Badge key={tag} variant="outline" className="text-xs">
                    <TagIcon className="h-2 w-2 mr-1" />
                    {tag}
                  </Badge>
                ))}
              </div>
              
              {/* Actions */}
              <div className="flex space-x-2 pt-2 border-t">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handlePreviewTemplate(template)}
                  className="flex-1"
                >
                  <EyeIcon className="h-3 w-3 mr-1" />
                  Preview
                </Button>
                <Button
                  size="sm"
                  onClick={() => handleApplyTemplate(template)}
                  className="flex-1"
                >
                  <PlayIcon className="h-3 w-3 mr-1" />
                  Use Template
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredTemplates.length === 0 && (
        <div className="text-center py-12">
          <BookOpenIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold">No Templates Found</h2>
          <p className="text-gray-600">Try adjusting your search terms or category filter.</p>
        </div>
      )}

      {/* Preview Modal */}
      {selectedTemplate && (
        <ConfirmDialog
          isOpen={previewModal}
          title={`Preview: ${selectedTemplate.name}`}
          description={
            <div className="space-y-4 text-left">
              <p>{selectedTemplate.description}</p>
              <div>
                <h4 className="font-medium mb-2">Configuration:</h4>
                <pre className="bg-gray-50 p-3 rounded text-xs font-mono overflow-x-auto max-h-64">
                  {selectedTemplate.config_content}
                </pre>
              </div>
            </div>
          }
          confirmText="Use This Template"
          cancelText="Close"
          onConfirm={() => {
            setPreviewModal(false);
            handleApplyTemplate(selectedTemplate);
          }}
          onCancel={() => setPreviewModal(false)}
        />
      )}

      {/* Apply Template Modal */}
      {selectedTemplate && (
        <DynamicFormModal
          isOpen={applyModal.isOpen}
          title={`Create from Template: ${selectedTemplate.name}`}
          description="Configure the template parameters for your specific use case"
          onClose={() => setApplyModal({ isOpen: false, isLoading: false })}
          onSubmit={handleCreateFromTemplate}
          isLoading={applyModal.isLoading}
          size="lg"
          fields={[
            {
              name: 'service_name',
              label: 'Service Name',
              type: 'text',
              placeholder: selectedTemplate.name.toLowerCase().replace(/\s+/g, '-'),
              required: true,
            },
            {
              name: 'device',
              label: 'Target Device',
              type: 'select',
              options: [
                { value: 'server1', label: 'server1' },
                { value: 'server2', label: 'server2' }
              ],
              required: true,
            },
            ...(selectedTemplate.config_fields || []),
          ]}
        />
      )}
    </div>
  );
}