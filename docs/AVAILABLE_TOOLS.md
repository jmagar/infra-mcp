# Available MCP Tools

## Core Claude Code Tools
- **Task** - Launch specialized agents for complex, multi-step tasks
- **Bash** - Execute bash commands in a persistent shell session
- **Glob** - Fast file pattern matching with glob patterns
- **Grep** - Powerful search using ripgrep with regex support
- **LS** - List files and directories
- **ExitPlanMode** - Exit planning mode after presenting implementation plan
- **Read** - Read files from the local filesystem
- **Edit** - Perform exact string replacements in files
- **MultiEdit** - Make multiple edits to a single file in one operation
- **Write** - Write files to the local filesystem
- **NotebookRead** - Read Jupyter notebook (.ipynb) files
- **NotebookEdit** - Edit Jupyter notebook cells
- **WebFetch** - Fetch and analyze web content with AI processing
- **TodoWrite** - Create and manage structured task lists
- **WebSearch** - Search the web for up-to-date information
- **ListMcpResourcesTool** - List available resources from MCP servers
- **ReadMcpResourceTool** - Read specific resources from MCP servers

## GitHub Chat MCP Server
- **mcp__github-chat__index_repository** - Index GitHub repository for codebase analysis
- **mcp__github-chat__query_repository** - Ask questions about indexed GitHub repositories

## SearXNG MCP Server
- **mcp__searxng__search** - Aggregate web search across Google, Bing, Brave, DuckDuckGo

## Gemini Coding MCP Server
- **mcp__gemini-coding__consult_gemini** - Start/continue conversations with Gemini for complex coding problems
- **mcp__gemini-coding__get_gemini_requests** - Get files and searches requested by Gemini
- **mcp__gemini-coding__list_sessions** - List active Gemini consultation sessions
- **mcp__gemini-coding__end_session** - End specific Gemini consultation sessions

## Sequential Thinking MCP Server
- **mcp__sequential-thinking__sequentialthinking_tools** - Dynamic problem-solving through structured thoughts

## YouTube Vision MCP Server
- **mcp__youtube-vision__summarize_youtube_video** - Generate summaries of YouTube videos
- **mcp__youtube-vision__ask_about_youtube_video** - Answer questions about YouTube video content
- **mcp__youtube-vision__extract_key_moments** - Extract timestamps and key moments
- **mcp__youtube-vision__list_supported_models** - List available Gemini models for video analysis

## DeepWiki MCP Server
- **mcp__mcp-deepwiki__deepwiki_fetch** - Fetch deepwiki.com repositories and return as Markdown

## GitHub MCP Server
- **mcp__github__add_issue_comment** - Add comments to issues
- **mcp__github__add_pull_request_review_comment_to_pending_review** - Add review comments to pending review
- **mcp__github__assign_copilot_to_issue** - Assign GitHub Copilot to issues for automated assistance
- **mcp__github__cancel_workflow_run** - Cancel running workflow executions
- **mcp__github__create_and_submit_pull_request_review** - Create and submit PR reviews without comments
- **mcp__github__create_branch** - Create new branches in repositories
- **mcp__github__create_issue** - Create new issues in repositories
- **mcp__github__create_or_update_file** - Create or update single files in repositories
- **mcp__github__create_pending_pull_request_review** - Create pending review for pull requests
- **mcp__github__create_pull_request** - Create new pull requests
- **mcp__github__create_repository** - Create new GitHub repositories
- **mcp__github__delete_file** - Delete files from repositories
- **mcp__github__delete_pending_pull_request_review** - Delete pending pull request reviews
- **mcp__github__delete_workflow_run_logs** - Delete logs for workflow runs
- **mcp__github__dismiss_notification** - Mark notifications as read or done
- **mcp__github__download_workflow_run_artifact** - Get download URL for workflow artifacts
- **mcp__github__fork_repository** - Fork repositories to your account or organization
- **mcp__github__get_code_scanning_alert** - Get details of code scanning alerts
- **mcp__github__get_commit** - Get details for specific commits
- **mcp__github__get_file_contents** - Get file or directory contents from repositories
- **mcp__github__get_issue** - Get details of specific issues
- **mcp__github__get_issue_comments** - Get comments for specific issues
- **mcp__github__get_job_logs** - Download logs for workflow jobs (supports failed jobs only)
- **mcp__github__get_me** - Get details of authenticated GitHub user
- **mcp__github__get_notification_details** - Get detailed information for specific notifications
- **mcp__github__get_pull_request** - Get details of specific pull requests
- **mcp__github__get_pull_request_comments** - Get comments for specific pull requests
- **mcp__github__get_pull_request_diff** - Get diff of pull requests
- **mcp__github__get_pull_request_files** - Get files changed in pull requests
- **mcp__github__get_pull_request_reviews** - Get reviews for specific pull requests
- **mcp__github__get_pull_request_status** - Get status of specific pull requests
- **mcp__github__get_secret_scanning_alert** - Get details of secret scanning alerts
- **mcp__github__get_tag** - Get details about specific git tags
- **mcp__github__get_workflow_run** - Get details of specific workflow runs
- **mcp__github__get_workflow_run_logs** - Download all logs for workflow runs (EXPENSIVE)
- **mcp__github__get_workflow_run_usage** - Get usage metrics for workflow runs
- **mcp__github__list_branches** - List branches in repositories
- **mcp__github__list_code_scanning_alerts** - List code scanning alerts in repositories
- **mcp__github__list_commits** - List commits of branches in repositories
- **mcp__github__list_issues** - List issues in repositories
- **mcp__github__list_notifications** - List GitHub notifications for authenticated user
- **mcp__github__list_pull_requests** - List pull requests in repositories
- **mcp__github__list_secret_scanning_alerts** - List secret scanning alerts in repositories
- **mcp__github__list_tags** - List git tags in repositories
- **mcp__github__list_workflow_jobs** - List jobs for specific workflow runs
- **mcp__github__list_workflow_run_artifacts** - List artifacts for workflow runs
- **mcp__github__list_workflow_runs** - List workflow runs for specific workflows
- **mcp__github__list_workflows** - List workflows in repositories
- **mcp__github__manage_notification_subscription** - Manage notification subscriptions (ignore/watch/delete)
- **mcp__github__manage_repository_notification_subscription** - Manage repository notification subscriptions
- **mcp__github__mark_all_notifications_read** - Mark all notifications as read
- **mcp__github__merge_pull_request** - Merge pull requests in repositories
- **mcp__github__push_files** - Push multiple files to repositories in single commit
- **mcp__github__request_copilot_review** - Request GitHub Copilot code review for pull requests
- **mcp__github__rerun_failed_jobs** - Re-run only failed jobs in workflow runs
- **mcp__github__rerun_workflow_run** - Re-run entire workflow runs
- **mcp__github__run_workflow** - Run Actions workflows by ID or filename
- **mcp__github__search_code** - Search for code across GitHub repositories
- **mcp__github__search_issues** - Search for issues in GitHub repositories
- **mcp__github__search_orgs** - Search for GitHub organizations
- **mcp__github__search_pull_requests** - Search for pull requests in GitHub repositories
- **mcp__github__search_repositories** - Search for GitHub repositories
- **mcp__github__search_users** - Search for GitHub users
- **mcp__github__submit_pending_pull_request_review** - Submit pending pull request reviews
- **mcp__github__update_issue** - Update existing issues in repositories
- **mcp__github__update_pull_request** - Update existing pull requests
- **mcp__github__update_pull_request_branch** - Update pull request branch with latest changes

## Context7 MCP Server
- **mcp__context7__resolve-library-id** - Resolve package names to Context7-compatible library IDs
- **mcp__context7__get-library-docs** - Fetch up-to-date documentation for libraries

## Prompt Kit MCP Server
- **mcp__prompt-kit__init** - Initialize new project using registry style structure
- **mcp__prompt-kit__get_items** - List all available items in the registry
- **mcp__prompt-kit__get_item** - Get specific item from the registry
- **mcp__prompt-kit__add_item** - Add item from the registry to project

## Gotify MCP Server
- **mcp__gotify-mcp__create_message** - Send new messages to Gotify using app token
- **mcp__gotify-mcp__get_messages** - Retrieve messages using client token
- **mcp__gotify-mcp__delete_message** - Delete specific messages by ID
- **mcp__gotify-mcp__create_application** - Create new Gotify applications
- **mcp__gotify-mcp__get_applications** - List all Gotify applications
- **mcp__gotify-mcp__update_application** - Update existing application details
- **mcp__gotify-mcp__delete_application** - Delete applications by ID
- **mcp__gotify-mcp__create_client** - Create new Gotify clients
- **mcp__gotify-mcp__get_clients** - List all Gotify clients
- **mcp__gotify-mcp__get_health** - Check Gotify server health status
- **mcp__gotify-mcp__get_version** - Get Gotify server version information

## Tailscale MCP Server
- **mcp__tailscale__list_devices** - List all devices in Tailscale network
- **mcp__tailscale__device_action** - Perform actions on devices (authorize/deauthorize/delete/expire-key)
- **mcp__tailscale__manage_routes** - Enable or disable routes for devices
- **mcp__tailscale__get_network_status** - Get current network status from Tailscale CLI
- **mcp__tailscale__connect_network** - Connect to the Tailscale network
- **mcp__tailscale__disconnect_network** - Disconnect from the Tailscale network
- **mcp__tailscale__ping_peer** - Ping peer devices in network
- **mcp__tailscale__get_version** - Get Tailscale version information
- **mcp__tailscale__manage_acl** - Manage Access Control Lists (get/update/validate)
- **mcp__tailscale__manage_dns** - Manage DNS configuration (nameservers/preferences/searchpaths)
- **mcp__tailscale__manage_keys** - Manage authentication keys (list/create/delete)
- **mcp__tailscale__manage_network_lock** - Manage network lock for enhanced security
- **mcp__tailscale__manage_policy_file** - Manage policy files and test ACL access rules
- **mcp__tailscale__get_tailnet_info** - Get detailed Tailscale network information
- **mcp__tailscale__manage_file_sharing** - Manage file sharing settings
- **mcp__tailscale__manage_exit_nodes** - Manage exit nodes and routing
- **mcp__tailscale__manage_webhooks** - Manage webhooks for event notifications
- **mcp__tailscale__manage_device_tags** - Manage device tags for organization and ACL targeting

## Favicon Generator MCP Server
- **mcp__favicon-generator__generate_favicon_from_png** - Generate complete favicon set from PNG image
- **mcp__favicon-generator__generate_favicon_from_url** - Download image from URL and generate favicon set

## Playwright MCP Server
- **mcp__playwright__browser_close** - Close the browser page
- **mcp__playwright__browser_resize** - Resize the browser window
- **mcp__playwright__browser_console_messages** - Get all console messages
- **mcp__playwright__browser_handle_dialog** - Handle browser dialogs
- **mcp__playwright__browser_evaluate** - Execute JavaScript on page or element
- **mcp__playwright__browser_file_upload** - Upload files to web forms
- **mcp__playwright__browser_install** - Install browser binaries
- **mcp__playwright__browser_press_key** - Press keyboard keys
- **mcp__playwright__browser_type** - Type text into editable elements
- **mcp__playwright__browser_navigate** - Navigate to URLs
- **mcp__playwright__browser_navigate_back** - Go back to previous page
- **mcp__playwright__browser_navigate_forward** - Go forward to next page
- **mcp__playwright__browser_network_requests** - Get all network requests since page load
- **mcp__playwright__browser_take_screenshot** - Take screenshots of current page
- **mcp__playwright__browser_snapshot** - Capture accessibility snapshot (better than screenshot)
- **mcp__playwright__browser_click** - Perform clicks on web page elements
- **mcp__playwright__browser_drag** - Perform drag and drop between elements
- **mcp__playwright__browser_hover** - Hover over elements on page
- **mcp__playwright__browser_select_option** - Select options in dropdowns
- **mcp__playwright__browser_tab_list** - List browser tabs
- **mcp__playwright__browser_tab_new** - Open new tabs
- **mcp__playwright__browser_tab_select** - Select tabs by index
- **mcp__playwright__browser_tab_close** - Close tabs
- **mcp__playwright__browser_wait_for** - Wait for text/conditions or specified time

## Deep Directory Tree MCP Server
- **mcp__deep-directory-tree__get_deep_directory_tree** - Get detailed directory tree structure

## Task Master AI MCP Server
- **mcp__task-master-ai__initialize_project** - Initialize Task Master project structure
- **mcp__task-master-ai__models** - Get/set AI model configurations and API key status
- **mcp__task-master-ai__rules** - Add/remove rule profiles from project
- **mcp__task-master-ai__parse_prd** - Parse Product Requirements Document into tasks
- **mcp__task-master-ai__analyze_project_complexity** - Analyze task complexity and generate expansion recommendations
- **mcp__task-master-ai__expand_task** - Expand tasks into subtasks for detailed implementation
- **mcp__task-master-ai__expand_all** - Expand all pending tasks into subtasks
- **mcp__task-master-ai__scope_up_task** - Increase complexity of tasks using AI
- **mcp__task-master-ai__scope_down_task** - Decrease complexity of tasks using AI
- **mcp__task-master-ai__get_tasks** - Get all tasks with optional filtering and subtasks
- **mcp__task-master-ai__get_task** - Get detailed information about specific tasks
- **mcp__task-master-ai__next_task** - Find next task to work on based on dependencies
- **mcp__task-master-ai__complexity_report** - Display complexity analysis report
- **mcp__task-master-ai__set_task_status** - Set status of tasks or subtasks
- **mcp__task-master-ai__generate** - Generate individual task files in tasks/ directory
- **mcp__task-master-ai__add_task** - Add new tasks using AI
- **mcp__task-master-ai__add_subtask** - Add subtasks to existing tasks
- **mcp__task-master-ai__update** - Update multiple upcoming tasks based on new context
- **mcp__task-master-ai__update_task** - Update single tasks with new information
- **mcp__task-master-ai__update_subtask** - Append timestamped information to subtasks
- **mcp__task-master-ai__remove_task** - Remove tasks or subtasks permanently
- **mcp__task-master-ai__remove_subtask** - Remove subtasks from parent tasks
- **mcp__task-master-ai__clear_subtasks** - Clear subtasks from specified tasks
- **mcp__task-master-ai__move_task** - Move tasks or subtasks to new positions
- **mcp__task-master-ai__add_dependency** - Add dependency relationships between tasks
- **mcp__task-master-ai__remove_dependency** - Remove dependencies from tasks
- **mcp__task-master-ai__validate_dependencies** - Check for dependency issues without changes
- **mcp__task-master-ai__fix_dependencies** - Fix invalid dependencies automatically
- **mcp__task-master-ai__response-language** - Get or set response language for project
- **mcp__task-master-ai__list_tags** - List all available tags with task counts
- **mcp__task-master-ai__add_tag** - Create new tags for organizing tasks
- **mcp__task-master-ai__delete_tag** - Delete existing tags and all their tasks
- **mcp__task-master-ai__use_tag** - Switch to different tag context
- **mcp__task-master-ai__rename_tag** - Rename existing tags
- **mcp__task-master-ai__copy_tag** - Copy existing tags with all tasks and metadata
- **mcp__task-master-ai__research** - Perform AI-powered research queries with project context

## Infrastructure MCP Server
- **mcp__infra__list_containers** - List Docker containers on specific devices
- **mcp__infra__get_container_info** - Get detailed information about specific containers
- **mcp__infra__get_container_logs** - Get logs from specific containers
- **mcp__infra__start_container** - Start containers on specific devices
- **mcp__infra__stop_container** - Stop containers on specific devices
- **mcp__infra__restart_container** - Restart containers on specific devices
- **mcp__infra__remove_container** - Remove containers on specific devices
- **mcp__infra__get_container_stats** - Get real-time resource usage for containers
- **mcp__infra__execute_in_container** - Execute commands inside containers
- **mcp__infra__get_drive_health** - Get S.M.A.R.T. drive health information and disk status
- **mcp__infra__get_drives_stats** - Get drive usage statistics and I/O performance metrics
- **mcp__infra__get_device_logs** - Get system logs from journald or traditional syslog
- **mcp__infra__list_devices** - List all registered infrastructure devices with filtering
- **mcp__infra__add_device** - Add new devices to infrastructure registry
- **mcp__infra__remove_device** - Remove devices from infrastructure registry
- **mcp__infra__edit_device** - Edit/update details of existing devices
- **mcp__infra__list_proxy_configs** - List SWAG reverse proxy configurations with sync check
- **mcp__infra__get_proxy_config** - Get specific proxy configuration with real-time content
- **mcp__infra__scan_proxy_configs** - Scan proxy directory and sync to database
- **mcp__infra__sync_proxy_config** - Sync specific proxy configuration with file system
- **mcp__infra__get_proxy_config_summary** - Get summary statistics for proxy configurations
- **mcp__infra__modify_compose_for_device** - Modify docker-compose for deployment on target device
- **mcp__infra__deploy_compose_to_device** - Deploy docker-compose to target device
- **mcp__infra__modify_and_deploy_compose** - Modify and deploy docker-compose in single operation
- **mcp__infra__scan_device_ports** - Scan for available ports on target device
- **mcp__infra__scan_docker_networks** - Scan Docker networks and provide recommendations
- **mcp__infra__generate_proxy_config** - Generate SWAG reverse proxy configuration for services
- **mcp__infra__list_zfs_pools** - List all ZFS pools on devices
- **mcp__infra__get_zfs_pool_status** - Get detailed status for specific ZFS pools
- **mcp__infra__list_zfs_datasets** - List ZFS datasets, optionally filtered by pool
- **mcp__infra__get_zfs_dataset_properties** - Get all properties for specific ZFS datasets
- **mcp__infra__list_zfs_snapshots** - List ZFS snapshots, optionally filtered by dataset
- **mcp__infra__create_zfs_snapshot** - Create new ZFS snapshots
- **mcp__infra__clone_zfs_snapshot** - Clone ZFS snapshots
- **mcp__infra__send_zfs_snapshot** - Send ZFS snapshots for replication/backup
- **mcp__infra__receive_zfs_snapshot** - Receive ZFS snapshot streams
- **mcp__infra__diff_zfs_snapshots** - Compare differences between ZFS snapshots
- **mcp__infra__check_zfs_health** - Comprehensive ZFS health check
- **mcp__infra__get_zfs_arc_stats** - Get ZFS ARC (Adaptive Replacement Cache) statistics
- **mcp__infra__monitor_zfs_events** - Monitor ZFS events and error messages
- **mcp__infra__generate_zfs_report** - Generate comprehensive ZFS reports
- **mcp__infra__analyze_snapshot_usage** - Analyze snapshot space usage and cleanup recommendations
- **mcp__infra__optimize_zfs_settings** - Analyze ZFS configuration and suggest optimizations
- **mcp__infra__get_device_info** - Get comprehensive device information including capabilities analysis
- **mcp__infra__import_devices_from_ssh_config** - Import devices from SSH configuration files

## PostgreSQL MCP Server
- **mcp__postgres__execute_query** - Execute SQL queries on PostgreSQL databases
- **mcp__postgres__list_databases** - List all databases on PostgreSQL server
- **mcp__postgres__list_schemas** - List schemas in specific databases
- **mcp__postgres__list_tables** - List tables in specific schemas
- **mcp__postgres__get_table_schema** - Get table structure and column information
- **mcp__postgres__list_objects** - List database objects (tables, views, functions, etc.)
- **mcp__postgres__get_object_details** - Get detailed information about database objects

## Code Graph MCP Server
- **mcp__code-graph-mcp__get_usage_guide** - Get usage guide for code analysis tools
- **mcp__code-graph-mcp__analyze_codebase** - Analyze entire codebase structure and dependencies
- **mcp__code-graph-mcp__find_definition** - Find definitions of functions, classes, variables
- **mcp__code-graph-mcp__find_references** - Find all references to code elements
- **mcp__code-graph-mcp__find_callers** - Find all callers of functions or methods
- **mcp__code-graph-mcp__find_callees** - Find all functions called by given functions
- **mcp__code-graph-mcp__complexity_analysis** - Analyze code complexity metrics
- **mcp__code-graph-mcp__dependency_analysis** - Analyze project dependencies
- **mcp__code-graph-mcp__project_statistics** - Get comprehensive project statistics

## Crawler MCP Server
- **mcp__crawler__scrape** - Scrape single web pages for content extraction
- **mcp__crawler__crawl** - Crawl websites with depth and filtering options
- **mcp__crawler__crawl_repo** - Crawl GitHub repositories for code analysis
- **mcp__crawler__crawl_dir** - Crawl local directories for file indexing
- **mcp__crawler__rag_query** - Query crawled content using RAG (Retrieval Augmented Generation)
- **mcp__crawler__list_sources** - List all crawled content sources
- **mcp__crawler__health_check** - Check crawler service health status
- **mcp__crawler__system_info** - Get crawler system information
- **mcp__crawler__service_status** - Get detailed service status information