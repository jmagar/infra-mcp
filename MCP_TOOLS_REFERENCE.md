# MCP Tools Reference

Complete list of all available MCP tools organized by server.

## Core Claude Code Tools

### Task Management & Agents
- `Task` - Launch specialized agents for complex tasks
  - Available agents: general-purpose, qa-engineer, systems-architect, research-specialist, orchestrator, backend-engineer, ui-ux-designer, infrastructure-engineer

### System Operations
- `Bash` - Execute shell commands with timeout and security measures
- `LS` - List files and directories with glob pattern filtering

### File Operations
- `Read` - Read files from filesystem (supports images, PDFs, notebooks)
- `Write` - Write files to filesystem
- `Edit` - Perform exact string replacements in files
- `MultiEdit` - Make multiple edits to a single file in one operation
- `NotebookRead` - Read Jupyter notebooks (.ipynb files)
- `NotebookEdit` - Edit Jupyter notebook cells

### Search & Discovery
- `Glob` - Fast file pattern matching with glob patterns
- `Grep` - Powerful search using ripgrep with regex support

### Planning & Organization
- `ExitPlanMode` - Exit planning mode when ready to code
- `TodoWrite` - Create and manage structured task lists

### Web & External Content
- `WebFetch` - Fetch and analyze web content with AI
- `WebSearch` - Search the web for current information

## Gemini Coding
- `mcp__gemini-coding__consult_gemini` - Start conversations with Gemini about coding problems
- `mcp__gemini-coding__get_gemini_requests` - Get files/searches Gemini has requested
- `mcp__gemini-coding__list_sessions` - List active Gemini consultation sessions
- `mcp__gemini-coding__end_session` - End specific Gemini consultation sessions

## GitHub Integration (50+ tools)

### Repository Management
- `mcp__github-chat__index_repository` - Index GitHub repos for analysis
- `mcp__github-chat__query_repository` - Ask questions about indexed GitHub repos
- `mcp__github__create_repository` - Create new GitHub repository
- `mcp__github__fork_repository` - Fork repository to your account

### Issues & Pull Requests
- `mcp__github__create_issue` - Create new issue
- `mcp__github__get_issue` - Get issue details
- `mcp__github__list_issues` - List repository issues
- `mcp__github__update_issue` - Update existing issue
- `mcp__github__add_issue_comment` - Add comment to issue
- `mcp__github__get_issue_comments` - Get issue comments
- `mcp__github__create_pull_request` - Create new pull request
- `mcp__github__get_pull_request` - Get pull request details
- `mcp__github__list_pull_requests` - List repository pull requests
- `mcp__github__update_pull_request` - Update existing pull request
- `mcp__github__merge_pull_request` - Merge pull request
- `mcp__github__get_pull_request_diff` - Get pull request diff
- `mcp__github__get_pull_request_files` - Get files changed in PR
- `mcp__github__get_pull_request_comments` - Get PR comments
- `mcp__github__get_pull_request_reviews` - Get PR reviews
- `mcp__github__get_pull_request_status` - Get PR status
- `mcp__github__update_pull_request_branch` - Update PR branch

### Reviews & Comments
- `mcp__github__create_pending_pull_request_review` - Create pending PR review
- `mcp__github__add_pull_request_review_comment_to_pending_review` - Add review comment
- `mcp__github__submit_pending_pull_request_review` - Submit pending review
- `mcp__github__delete_pending_pull_request_review` - Delete pending review
- `mcp__github__create_and_submit_pull_request_review` - Create and submit review
- `mcp__github__request_copilot_review` - Request Copilot code review

### Files & Content
- `mcp__github__get_file_contents` - Get file/directory contents
- `mcp__github__create_or_update_file` - Create or update single file
- `mcp__github__delete_file` - Delete file from repository
- `mcp__github__push_files` - Push multiple files in single commit

### Branches & Commits
- `mcp__github__create_branch` - Create new branch
- `mcp__github__list_branches` - List repository branches
- `mcp__github__get_commit` - Get commit details
- `mcp__github__list_commits` - List repository commits
- `mcp__github__list_tags` - List git tags
- `mcp__github__get_tag` - Get tag details

### Workflows & Actions
- `mcp__github__list_workflows` - List repository workflows
- `mcp__github__list_workflow_runs` - List workflow runs
- `mcp__github__get_workflow_run` - Get workflow run details
- `mcp__github__list_workflow_jobs` - List workflow jobs
- `mcp__github__get_job_logs` - Get job logs
- `mcp__github__get_workflow_run_logs` - Get workflow run logs
- `mcp__github__get_workflow_run_usage` - Get workflow run usage
- `mcp__github__run_workflow` - Run workflow
- `mcp__github__cancel_workflow_run` - Cancel workflow run
- `mcp__github__rerun_workflow_run` - Re-run workflow run
- `mcp__github__rerun_failed_jobs` - Re-run failed jobs
- `mcp__github__list_workflow_run_artifacts` - List workflow artifacts
- `mcp__github__download_workflow_run_artifact` - Download workflow artifact
- `mcp__github__delete_workflow_run_logs` - Delete workflow logs

### Security & Scanning
- `mcp__github__list_code_scanning_alerts` - List code scanning alerts
- `mcp__github__get_code_scanning_alert` - Get code scanning alert details
- `mcp__github__list_secret_scanning_alerts` - List secret scanning alerts
- `mcp__github__get_secret_scanning_alert` - Get secret scanning alert details

### Notifications & User
- `mcp__github__get_me` - Get authenticated user details
- `mcp__github__list_notifications` - List GitHub notifications
- `mcp__github__get_notification_details` - Get notification details
- `mcp__github__dismiss_notification` - Dismiss notification
- `mcp__github__mark_all_notifications_read` - Mark all notifications as read
- `mcp__github__manage_notification_subscription` - Manage notification subscriptions
- `mcp__github__manage_repository_notification_subscription` - Manage repo notifications

### Search
- `mcp__github__search_code` - Search for code across repositories
- `mcp__github__search_issues` - Search for issues
- `mcp__github__search_pull_requests` - Search for pull requests
- `mcp__github__search_repositories` - Search for repositories
- `mcp__github__search_users` - Search for users
- `mcp__github__search_orgs` - Search for organizations

### Copilot Integration
- `mcp__github__assign_copilot_to_issue` - Assign Copilot to issue

## Search & Web Tools

### Web Search
- `mcp__searxng__search` - Aggregate search across Google, Bing, DuckDuckGo, Brave

### YouTube Analysis
- `mcp__youtube-vision__summarize_youtube_video` - Generate video summaries
- `mcp__youtube-vision__ask_about_youtube_video` - Ask questions about video content
- `mcp__youtube-vision__extract_key_moments` - Extract key timestamps and descriptions
- `mcp__youtube-vision__list_supported_models` - List available Gemini models

## Sequential Thinking
- `mcp__sequential-thinking__sequentialthinking_tools` - Dynamic problem-solving through structured thoughts with tool recommendations

## Documentation & Libraries

### DeepWiki
- `mcp__mcp-deepwiki__deepwiki_fetch` - Fetch documentation from deepwiki.com repositories

### Context7 (Library Documentation)
- `mcp__context7__resolve-library-id` - Resolve package names to Context7 library IDs
- `mcp__context7__get-library-docs` - Get up-to-date library documentation

### Prompt Kit
- `mcp__prompt-kit__init` - Initialize new project structure
- `mcp__prompt-kit__get_items` - List available registry items
- `mcp__prompt-kit__get_item` - Get specific registry item
- `mcp__prompt-kit__add_item` - Add item from registry

## Notifications & Communication

### Gotify (10 tools)
- `mcp__gotify-mcp__create_message` - Send messages with app token
- `mcp__gotify-mcp__get_messages` - Retrieve messages
- `mcp__gotify-mcp__delete_message` - Delete specific message
- `mcp__gotify-mcp__create_application` - Create new application
- `mcp__gotify-mcp__get_applications` - List all applications
- `mcp__gotify-mcp__update_application` - Update application details
- `mcp__gotify-mcp__delete_application` - Delete application
- `mcp__gotify-mcp__create_client` - Create new client
- `mcp__gotify-mcp__get_clients` - List all clients
- `mcp__gotify-mcp__get_health` - Check server health
- `mcp__gotify-mcp__get_version` - Get server version

## Network Management

### Tailscale (15+ tools)
- `mcp__tailscale__list_devices` - List all devices in network
- `mcp__tailscale__device_action` - Perform device actions (authorize, deauthorize, delete, expire-key)
- `mcp__tailscale__manage_routes` - Enable/disable device routes
- `mcp__tailscale__get_network_status` - Get current network status
- `mcp__tailscale__connect_network` - Connect to Tailscale network
- `mcp__tailscale__disconnect_network` - Disconnect from network
- `mcp__tailscale__ping_peer` - Ping peer devices
- `mcp__tailscale__get_version` - Get Tailscale version
- `mcp__tailscale__manage_acl` - Manage Access Control Lists
- `mcp__tailscale__manage_dns` - Manage DNS configuration
- `mcp__tailscale__manage_keys` - Manage authentication keys
- `mcp__tailscale__manage_network_lock` - Manage network lock (key authority)
- `mcp__tailscale__manage_policy_file` - Manage policy files and test ACL rules
- `mcp__tailscale__get_tailnet_info` - Get detailed network information
- `mcp__tailscale__manage_file_sharing` - Manage file sharing settings
- `mcp__tailscale__manage_exit_nodes` - Manage exit nodes and routing
- `mcp__tailscale__manage_webhooks` - Manage webhooks for notifications
- `mcp__tailscale__manage_device_tags` - Manage device tags for organization

## Web Crawling & RAG

### Crawler (11 tools)
- `mcp__crawler__scrape` - Extract content from single URL
- `mcp__crawler__crawl` - Crawl multiple pages from website
- `mcp__crawler__crawl_repo` - Crawl and index entire repository
- `mcp__crawler__crawl_dir` - Crawl files in directory
- `mcp__crawler__rag_query` - Query crawled content using RAG
- `mcp__crawler__list_sources` - List all crawled sources
- `mcp__crawler__health_check` - Check system health status
- `mcp__crawler__system_info` - Get system information
- `mcp__crawler__service_status` - Check external service status

## Code Analysis

### Code Graph (10 tools)
- `mcp__code-graph-mcp__get_usage_guide` - Get tool usage guidance
- `mcp__code-graph-mcp__analyze_codebase` - Comprehensive codebase analysis
- `mcp__code-graph-mcp__find_definition` - Find symbol definitions
- `mcp__code-graph-mcp__find_references` - Find symbol references
- `mcp__code-graph-mcp__find_callers` - Find function callers
- `mcp__code-graph-mcp__find_callees` - Find function callees
- `mcp__code-graph-mcp__complexity_analysis` - Analyze code complexity
- `mcp__code-graph-mcp__dependency_analysis` - Analyze module dependencies
- `mcp__code-graph-mcp__project_statistics` - Get project statistics

## Browser Automation

### Playwright (25+ tools)
- `mcp__playwright__browser_navigate` - Navigate to URL
- `mcp__playwright__browser_navigate_back` - Go back to previous page
- `mcp__playwright__browser_navigate_forward` - Go forward to next page
- `mcp__playwright__browser_snapshot` - Capture accessibility snapshot
- `mcp__playwright__browser_take_screenshot` - Take page screenshot
- `mcp__playwright__browser_click` - Perform click on web page
- `mcp__playwright__browser_type` - Type text into elements
- `mcp__playwright__browser_press_key` - Press keyboard keys
- `mcp__playwright__browser_hover` - Hover over elements
- `mcp__playwright__browser_drag` - Perform drag and drop
- `mcp__playwright__browser_select_option` - Select dropdown options
- `mcp__playwright__browser_file_upload` - Upload files
- `mcp__playwright__browser_evaluate` - Evaluate JavaScript
- `mcp__playwright__browser_wait_for` - Wait for conditions
- `mcp__playwright__browser_handle_dialog` - Handle dialogs
- `mcp__playwright__browser_resize` - Resize browser window
- `mcp__playwright__browser_close` - Close browser
- `mcp__playwright__browser_install` - Install browser
- `mcp__playwright__browser_console_messages` - Get console messages
- `mcp__playwright__browser_network_requests` - Get network requests
- `mcp__playwright__browser_tab_list` - List browser tabs
- `mcp__playwright__browser_tab_new` - Open new tab
- `mcp__playwright__browser_tab_select` - Select tab by index
- `mcp__playwright__browser_tab_close` - Close tab

## Project Management

### Deep Directory Tree
- `mcp__deep-directory-tree__get_deep_directory_tree` - Get comprehensive directory structure

### Task Master AI (30+ tools)

#### Project Setup
- `mcp__task-master-ai__initialize_project` - Initialize Task Master project
- `mcp__task-master-ai__models` - Manage AI model configurations
- `mcp__task-master-ai__rules` - Add/remove rule profiles
- `mcp__task-master-ai__parse_prd` - Parse PRD to generate tasks

#### Task Management
- `mcp__task-master-ai__get_tasks` - Get all tasks with filtering
- `mcp__task-master-ai__get_task` - Get specific task details
- `mcp__task-master-ai__next_task` - Find next available task
- `mcp__task-master-ai__add_task` - Add new task with AI
- `mcp__task-master-ai__add_subtask` - Add subtask to existing task
- `mcp__task-master-ai__update_task` - Update specific task
- `mcp__task-master-ai__update_subtask` - Update subtask
- `mcp__task-master-ai__update` - Update multiple tasks from ID
- `mcp__task-master-ai__remove_task` - Remove task/subtask
- `mcp__task-master-ai__remove_subtask` - Remove subtask from parent
- `mcp__task-master-ai__clear_subtasks` - Clear subtasks from tasks
- `mcp__task-master-ai__move_task` - Move task to new position
- `mcp__task-master-ai__set_task_status` - Set task status
- `mcp__task-master-ai__generate` - Generate task files

#### Analysis & Planning
- `mcp__task-master-ai__analyze_project_complexity` - Analyze task complexity
- `mcp__task-master-ai__complexity_report` - Display complexity report
- `mcp__task-master-ai__expand_task` - Expand task into subtasks
- `mcp__task-master-ai__expand_all` - Expand all pending tasks

#### Dependencies
- `mcp__task-master-ai__add_dependency` - Add task dependency
- `mcp__task-master-ai__remove_dependency` - Remove task dependency
- `mcp__task-master-ai__validate_dependencies` - Check dependency issues
- `mcp__task-master-ai__fix_dependencies` - Fix invalid dependencies

#### Organization
- `mcp__task-master-ai__list_tags` - List available tags
- `mcp__task-master-ai__add_tag` - Create new tag
- `mcp__task-master-ai__delete_tag` - Delete existing tag
- `mcp__task-master-ai__use_tag` - Switch to different tag
- `mcp__task-master-ai__rename_tag` - Rename existing tag
- `mcp__task-master-ai__copy_tag` - Copy tag with all tasks

#### Configuration
- `mcp__task-master-ai__response-language` - Set response language

#### Research
- `mcp__task-master-ai__research` - AI-powered research with project context

---

**Total Tools Available**: 200+ tools across 15+ MCP servers

**Categories**:
- **Development**: Code analysis, file operations, Git/GitHub integration
- **Infrastructure**: Network management, system monitoring, containerization
- **Web & Content**: Crawling, search, browser automation, documentation
- **Project Management**: Task tracking, planning, complexity analysis
- **Communication**: Notifications, messaging, collaboration
- **AI & Analysis**: Code intelligence, research, problem-solving