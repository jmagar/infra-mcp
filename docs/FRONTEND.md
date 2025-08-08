# Infrastructor Frontend Implementation Plan

## 📊 Investigation Findings

### Available Data Types (14 Categories)
1. **Core Infrastructure**
   - `Device` - Device registry with SSH config, status, metadata
   - `Container` - Docker container status, stats, logs
   - `SystemMetrics` - CPU, memory, disk, network metrics
   - `VM` - Virtual machine status and resource usage

2. **Storage & Filesystem**
   - `ZFS` - Pools, datasets, snapshots, health checks
   - `DriveHealth` - SMART status, drive metrics
   - `Backup` - Backup schedules, status, history

3. **Networking & Configuration**
   - `ProxyConfig` - SWAG reverse proxy configurations
   - `Network` - Network interfaces, Docker networks
   - `ComposeDeployment` - Docker Compose modification/deployment

4. **System Management**
   - `Updates` - System updates, policies, compliance
   - `Logs` - System logs from multiple sources

### API Endpoints Analysis

#### Device Management (`/api/devices`)
- CRUD operations for device registry
- Status monitoring and SSH connectivity testing
- System metrics, drive health, logs, network ports
- Bulk import from SSH config files

#### Container Management (`/api/containers`)
- List, inspect, logs, stats for containers
- Lifecycle operations (start, stop, restart, remove)
- Execute commands inside containers
- Real-time resource monitoring

#### Proxy Configuration (`/api/proxies`)
- List and manage SWAG reverse proxy configs
- Real-time sync with configuration files
- Access templates and sample configurations
- Raw configuration file content delivery

#### ZFS Management (`/api/zfs`) - 16 endpoints
- Pool operations (list, status, health)
- Dataset management (list, properties, create)
- Snapshot operations (create, clone, send, receive, diff)
- Health monitoring (ARC stats, events, analysis)

#### Compose Deployment (`/api/compose`)
- Modify compose files for target devices
- Deploy with backup and health checks
- Port and network scanning
- Combined modify-and-deploy operations

#### Monitoring (`/api/monitoring`)
- Detailed system metrics
- Polling status
- Performance metrics
- Dashboard data aggregation

#### WebSocket (`/ws/stream`)
- Real-time metric streaming
- Live container stats
- Event notifications
- System alerts

## 🧩 Component Library Requirements

### Core UI Components

#### Data Display Components
- **MetricCard** - Display single metric with trend
- **MetricChart** - Time-series charts (CPU, memory, etc.)
- **StatusBadge** - Online/offline/warning status indicators
- **ResourceBar** - Usage bars for CPU, memory, disk
- **LogViewer** - Scrollable log display with filters
- **JsonViewer** - Formatted JSON display for configs

#### Table Components
- **DataTable** - Sortable, filterable, paginated tables
- **ExpandableRow** - Row with expandable details
- **SelectableTable** - Multi-select with bulk actions
- **VirtualizedTable** - For large datasets

#### Form Components
- **DeviceForm** - Add/edit device with validation
- **ContainerActionForm** - Container operations
- **ComposeEditor** - Docker Compose YAML editor
- **ProxyConfigEditor** - Nginx config editor

#### Navigation Components
- **Sidebar** - Main navigation with collapsible sections
- **Breadcrumbs** - Hierarchical navigation
- **TabNavigation** - Sub-page navigation
- **CommandPalette** - Quick actions (Cmd+K)

#### Real-time Components
- **LiveMetricDisplay** - WebSocket-connected metrics
- **NotificationToast** - Real-time alerts
- **ConnectionStatus** - WebSocket connection indicator
- **AutoRefresh** - Configurable refresh intervals

### Composite Components

#### Device Components
- **DeviceCard** - Summary card with status and metrics
- **DeviceList** - Grid/list view of all devices
- **DeviceDetails** - Full device information panel
- **DeviceMetrics** - Real-time metrics dashboard

#### Container Components
- **ContainerCard** - Container status and controls
- **ContainerStats** - Resource usage charts
- **ContainerLogs** - Log viewer with search
- **ContainerTerminal** - Execute commands UI

#### ZFS Components
- **PoolStatus** - Pool health and usage
- **DatasetTree** - Hierarchical dataset view
- **SnapshotManager** - Create, clone, manage snapshots
- **ZFSHealthDashboard** - Comprehensive health overview

## 📄 Page Structure

### Primary Navigation Pages

#### 1. Dashboard (`/`)
- System overview cards
- Critical alerts panel
- Recent activity feed
- Quick actions toolbar
- Real-time metrics summary

#### 2. Devices (`/devices`)
- Device grid/list toggle
- Add device button
- Bulk import option
- Filter by status/type/location
- Device details modal/drawer

#### 3. Containers (`/containers`)
- Container list grouped by device
- Status filters (running, stopped, all)
- Quick actions (start, stop, restart)
- Container details with tabs:
  - Overview
  - Logs
  - Stats
  - Exec

#### 4. Storage (`/storage`)
- Sub-navigation tabs:
  - ZFS Pools
  - Datasets
  - Snapshots
  - Drive Health
- Storage usage overview
- Health status indicators

#### 5. Networking (`/networking`)
- Proxy configurations
- Network interfaces
- Docker networks
- Port usage map

#### 6. Deployments (`/deployments`)
- Compose file management
- Deployment history
- Template library
- Port scanner tool

#### 7. Monitoring (`/monitoring`)
- Real-time metrics dashboard
- Custom metric queries
- Alert configuration
- Performance analysis

#### 8. System (`/system`)
- Updates management
- Backup schedules
- System logs
- VM monitoring

#### 9. Settings (`/settings`)
- Notification preferences
- Theme configuration
- System preferences

## 🚀 Implementation Phases

### Phase 1: Foundation (Week 1-2)
**Priority: Core infrastructure and basic device management**

1. **Layout & Navigation**
   - App shell with sidebar
   - Route configuration
   - Error boundaries

2. **Device Management**
   - Device list page
   - Add/edit device forms
   - Device status monitoring
   - Basic device details

3. **Core Components**
   - DataTable component
   - StatusBadge component
   - MetricCard component
   - Form components

4. **API Integration**
   - Axios client setup (no auth needed - handled by reverse proxy)
   - API hooks (useDevices, etc.)
   - Error handling
   - Loading states

### Phase 2: Container Management (Week 3-4)
**Priority: Docker container operations**

1. **Container Pages**
   - Container list view
   - Container details
   - Container logs viewer
   - Container stats charts

2. **Container Components**
   - ContainerCard
   - ContainerStats
   - LogViewer
   - Container action buttons

3. **Real-time Features**
   - WebSocket connection
   - Live container stats
   - Auto-refresh toggles

### Phase 3: Monitoring & Metrics (Week 5-6)
**Priority: System monitoring and alerting**

1. **Dashboard**
   - Overview dashboard
   - Metric charts
   - Alert notifications
   - Activity feed

2. **Monitoring Pages**
   - Metrics explorer
   - Custom dashboards
   - Alert rules

3. **Chart Components**
   - Time-series charts
   - Resource gauges
   - Heatmaps

### Phase 4: Advanced Features (Week 7-8)
**Priority: ZFS, proxy, and deployment tools**

1. **Storage Management**
   - ZFS pool management
   - Dataset browser
   - Snapshot interface
   - Drive health monitoring

2. **Proxy Configuration**
   - Config editor
   - Template library
   - Sync status

3. **Deployment Tools**
   - Compose editor
   - Deployment wizard
   - Port scanner

### Phase 5: Polish & Optimization (Week 9-10)
**Priority: UX improvements and performance**

1. **User Experience**
   - Command palette
   - Keyboard shortcuts
   - Drag-and-drop
   - Bulk operations

2. **Performance**
   - Code splitting
   - Virtual scrolling
   - Image optimization
   - Bundle size reduction

3. **Polish**
   - Dark mode
   - Responsive design
   - Accessibility
   - Documentation

## 🎯 Component Priority Matrix

### Must Have (P0)
- Device list and management
- Container list and controls
- Basic monitoring dashboard
- Error handling

### Should Have (P1)
- Real-time metrics
- Log viewer
- ZFS management
- Proxy configuration
- Deployment tools

### Nice to Have (P2)
- Command palette
- Custom dashboards
- Backup management
- Update management
- VM monitoring

### Future Enhancements (P3)
- Mobile app
- CLI integration
- Terraform integration
- Ansible playbooks
- Multi-tenancy

## 🔧 Technical Implementation Details

### State Management Structure
```typescript
// Zustand stores
- useDeviceStore     // Device data and operations
- useContainerStore  // Container data and operations
- useMetricsStore    // Real-time metrics
- useWebSocketStore  // WebSocket connection state
- useUIStore         // UI preferences and settings
```

### API Hook Patterns
```typescript
// Custom hooks for data fetching
- useDevices()       // List devices with filters
- useDevice(id)      // Single device details
- useContainers()    // List containers
- useMetrics()       // Real-time metrics
- useWebSocket()     // WebSocket connection
```

### Route Structure
```typescript
const routes = [
  { path: '/', component: Dashboard },
  { path: '/devices', component: DeviceList },
  { path: '/devices/:id', component: DeviceDetails },
  { path: '/containers', component: ContainerList },
  { path: '/containers/:device/:name', component: ContainerDetails },
  { path: '/storage/zfs', component: ZFSManager },
  { path: '/networking/proxy', component: ProxyConfig },
  { path: '/deployments', component: ComposeDeployment },
  { path: '/monitoring', component: Monitoring },
  { path: '/system/updates', component: Updates },
  { path: '/settings', component: Settings },
];
```

## 📈 Success Metrics

### Performance Targets
- Initial load: < 3 seconds
- Time to interactive: < 5 seconds
- API response time: < 500ms
- WebSocket latency: < 100ms

### User Experience Goals
- Device status visible within 2 clicks
- Container operations within 1 click
- Real-time updates without refresh
- Mobile-responsive design

### Code Quality Standards
- TypeScript coverage: 100%
- Test coverage: > 80%
- Bundle size: < 500KB gzipped
- Lighthouse score: > 90

## 🗓️ Timeline Summary

**Total Duration: 10 weeks**

- **Weeks 1-2**: Foundation and device management
- **Weeks 3-4**: Container management and real-time features
- **Weeks 5-6**: Monitoring and metrics dashboard
- **Weeks 7-8**: Advanced features (ZFS, proxy, deployments)
- **Weeks 9-10**: Polish, optimization, and testing

## 📝 Next Steps

1. **Immediate Actions**
   - Complete dashboard layout component
   - Implement device list page
   - Set up WebSocket connection
   - Create reusable data table component

2. **Short Term (This Week)**
   - Build out device CRUD operations
   - Add container list view
   - Create status monitoring components
   - Set up error boundaries

3. **Medium Term (Next 2 Weeks)**
   - Complete container management features
   - Add real-time metrics streaming
   - Build monitoring dashboard
   - Implement log viewer

4. **Long Term (Month)**
   - ZFS management interface
   - Proxy configuration editor
   - Deployment automation tools
   - System update management

## 🔐 Authentication & Security

**Note**: Authentication is handled by reverse proxy with 2FA, so the frontend does not need to implement:
- Login/logout UI components
- Token management and storage
- Protected route logic
- Authentication interceptors
- User session management

The application will run behind a secured reverse proxy that handles all authentication concerns, allowing the frontend to focus purely on infrastructure management functionality.

---

*This plan is based on thorough analysis of the available API endpoints, data types, and infrastructure requirements. It provides a clear roadmap for building a comprehensive web UI for the Infrastructor platform.*