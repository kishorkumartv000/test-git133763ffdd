import os
import requests
import tempfile
import time
from github import Github, GithubException

def main():
    # Load configuration
    token = os.getenv('GITHUB_TOKEN')
    target_account = os.getenv('TARGET_ACCOUNT')
    operation = os.getenv('OPERATION')
    repo_name = os.getenv('REPO_NAME')
    tag_name = os.getenv('TAG_NAME')
    release_title = os.getenv('RELEASE_TITLE')
    asset_url = os.getenv('ASSET_URL')
    actions_enabled = os.getenv('ACTIONS_ENABLED')
    allow_all_actions = os.getenv('ALLOW_ALL_ACTIONS')
    allow_reusable_workflows = os.getenv('ALLOW_REUSABLE_WORKFLOWS')
    
    # Validate inputs
    if not token:
        raise ValueError("Missing GITHUB_TOKEN")
    if not target_account:
        raise ValueError("Missing TARGET_ACCOUNT")
    
    g = Github(token)
    current_user = g.get_user()  # Get authenticated user
    
    try:
        # Get target user/org
        try:
            target = g.get_organization(target_account)
            is_org = True
        except GithubException:
            target = g.get_user(target_account)
            is_org = False
        
        # Perform operations
        if operation == "list_repos":
            print(f"Repositories for {target.login}:")
            for repo in target.get_repos():
                visibility = "🔒 PRIVATE" if repo.private else "🌍 PUBLIC"
                print(f"- {visibility}: {repo.name} (URL: {repo.html_url})")
                
        elif operation == "create_repo" and repo_name:
            try:
                if is_org:
                    # Create in organization
                    repo = target.create_repo(
                        name=repo_name,
                        private=True,
                        auto_init=True
                    )
                else:
                    # Create in user account (must be current user)
                    if target.login.lower() != current_user.login.lower():
                        raise ValueError(f"Cannot create repo in another user's account: {target.login}")
                    
                    repo = current_user.create_repo(
                        name=repo_name,
                        private=True,
                        auto_init=True
                    )
                
                print(f"✅ Created repository: {repo.html_url}")
                print(f"   - Visibility: {'Private' if repo.private else 'Public'}")
                print(f"   - Owner: {repo.owner.login}")
                
            except ValueError as ve:
                print(f"❌ {str(ve)}")
            except GithubException as ge:
                print(f"❌ GitHub API error: {ge.data.get('message', str(ge))}")
                
        elif operation == "delete_repo" and repo_name:
            try:
                repo = target.get_repo(repo_name)
                repo.delete()
                print(f"✅ Deleted repository: {repo_name}")
            except GithubException as e:
                print(f"❌ Error deleting repo: {e.data.get('message', str(e))}")
                
        elif operation == "toggle_visibility" and repo_name:
            try:
                repo = target.get_repo(repo_name)
                new_visibility = not repo.private
                repo.edit(private=new_visibility)
                
                status = "PRIVATE" if new_visibility else "PUBLIC"
                print(f"✅ Visibility changed for {repo_name}")
                print(f"   - New status: {status}")
                print(f"   - URL: {repo.html_url}")
            except GithubException as e:
                print(f"❌ Error changing visibility: {e.data.get('message', str(e))}")
                
        elif operation == "create_release" and repo_name and tag_name and release_title:
            try:
                repo = target.get_repo(repo_name)
                
                # Create new release
                release = repo.create_git_release(
                    tag=tag_name,
                    name=release_title,
                    message=f"Release {tag_name}: {release_title}",
                    draft=False
                )
                print(f"✅ Created release: {release.title} ({tag_name})")
                print(f"   - URL: {release.html_url}")
                
                # Handle asset if URL provided
                if asset_url:
                    try:
                        # Download asset
                        response = requests.get(asset_url, stream=True)
                        response.raise_for_status()
                        
                        # Get filename from URL if not specified
                        filename = os.path.basename(asset_url)
                        
                        # Create temp file
                        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                            for chunk in response.iter_content(chunk_size=8192):
                                temp_file.write(chunk)
                            temp_path = temp_file.name
                        
                        # Upload asset to release
                        print(f"⬇️ Downloaded asset: {filename} ({response.headers.get('Content-Length', '?')} bytes)")
                        release.upload_asset(
                            path=temp_path,
                            name=filename,
                            content_type=response.headers.get('Content-Type', 'application/octet-stream')
                        )
                        print(f"⬆️ Uploaded asset: {filename}")
                        
                        # Cleanup temp file
                        os.unlink(temp_path)
                        
                    except Exception as e:
                        print(f"⚠️ Error processing asset: {str(e)}")
                
            except GithubException as e:
                print(f"❌ Error creating release: {e.data.get('message', str(e))}")
                
        elif operation == "set_actions_permissions" and repo_name:
            try:
                repo = target.get_repo(repo_name)
                
                # Build new permissions object
                new_permissions = {}
                
                # Actions enabled/disabled
                if actions_enabled is not None:
                    enabled = actions_enabled.lower() == "true"
                    new_permissions["enabled"] = enabled
                    status = "🟢 ENABLED" if enabled else "🔴 DISABLED"
                    print(f"Set Actions: {status}")
                
                # Only set other permissions if actions are enabled
                if actions_enabled is None or actions_enabled.lower() == "true":
                    # All actions configuration
                    if allow_all_actions is not None:
                        allow_all = allow_all_actions.lower() == "true"
                        new_permissions["allowed_actions"] = "all" if allow_all else "selected"
                        status = "✅ ALLOWED" if allow_all else "🚫 RESTRICTED"
                        print(f"All Actions: {status}")
                    
                    # Reusable workflows configuration
                    if allow_reusable_workflows is not None:
                        allow_reusable = allow_reusable_workflows.lower() == "true"
                        # For reusable workflows, we need to set allowed_actions to "selected"
                        if allow_reusable:
                            new_permissions["allowed_actions"] = "selected"
                        new_permissions["enabled_repositories"] = "all" if allow_reusable else "none"
                        status = "✅ ALLOWED" if allow_reusable else "🚫 BLOCKED"
                        print(f"Reusable Workflows: {status}")
                
                # Update permissions if we have changes
                if new_permissions:
                    repo.edit(**new_permissions)
                    print(f"✅ Updated Actions permissions for {repo_name}")
                else:
                    print("⚠️ No changes specified for Actions permissions")
                    
                # Print current settings
                print("\nCurrent Actions Settings:")
                print(f"- Enabled: {'🟢 YES' if repo.allow_auto_merge else '🔴 NO'}")  # Workaround for permissions
                
                # For PyGithub versions that support get_actions_permissions
                try:
                    updated = repo.get_actions_permissions()
                    print(f"- All Actions: {'✅ ALLOWED' if updated.allowed_actions == 'all' else '🚫 RESTRICTED'}")
                    print(f"- Reusable Workflows: {'✅ ALLOWED' if updated.enabled_repositories == 'all' else '🚫 BLOCKED'}")
                except AttributeError:
                    print("⚠️ Could not retrieve detailed actions settings. PyGithub version might be outdated.")
                    print("   Please ensure you're using PyGithub v1.55 or later")
                
            except GithubException as e:
                print(f"❌ Error setting Actions permissions: {e.data.get('message', str(e))}")
                
        elif operation == "run_workflow" and repo_name:
            try:
                repo = target.get_repo(repo_name)
                
                # Get all workflows in the repository
                workflows = list(repo.get_workflows())
                
                if not workflows:
                    print("❌ No workflows found in repository")
                    print("   Please create a workflow in .github/workflows/ directory")
                    return
                
                # Find active workflows
                active_workflows = [wf for wf in workflows if wf.state == "active"]
                
                if not active_workflows:
                    # If no active workflows, show available workflows
                    print("❌ No active workflows found. Available workflows:")
                    for i, wf in enumerate(workflows, 1):
                        state_emoji = "🟢" if wf.state == "active" else "🔴"
                        print(f"   {i}. {state_emoji} {wf.name} (state: {wf.state})")
                    print("\n💡 To activate a workflow, go to repository Actions tab")
                    return
                
                # Use the first active workflow
                workflow = active_workflows[0]
                
                # Use repository's default branch
                ref = repo.default_branch
                
                # Trigger workflow dispatch
                workflow.create_dispatch(ref=ref)
                
                print(f"✅ Triggered workflow: {workflow.name}")
                print(f"   - Repository: {repo_name}")
                print(f"   - Using default branch: {ref}")
                print(f"   - Workflow file: {workflow.path}")
                print(f"   - Workflow URL: https://github.com/{repo.full_name}/actions/workflows/{os.path.basename(workflow.path)}")
                
                # Monitor workflow start
                print("\n⏳ Waiting for workflow to start...")
                time.sleep(3)
                
                # Get latest runs
                runs = workflow.get_runs()
                latest_run = runs[0] if runs.totalCount > 0 else None
                
                if latest_run:
                    print(f"   - Workflow ID: {latest_run.id}")
                    status_emoji = "🟢" if latest_run.status == "completed" else "🟡"
                    print(f"   - Status: {status_emoji} {latest_run.status.upper()}")
                    print(f"   - Run URL: {latest_run.html_url}")
                else:
                    print("⚠️ Workflow run not detected yet")
                    print("   Check repository Actions tab manually")
                
            except GithubException as e:
                print(f"❌ Error triggering workflow: {e.data.get('message', str(e))}")
                if "Not Found" in str(e):
                    print("   Make sure the workflow file exists in .github/workflows/")
                
        elif operation == "cancel_workflows" and repo_name:
            try:
                repo = target.get_repo(repo_name)
                
                # Get only currently running workflows
                runs = repo.get_workflow_runs(status="in_progress")
                total_runs = runs.totalCount
                
                if total_runs == 0:
                    print("✅ No currently running workflows found")
                    return
                
                print(f"Found {total_runs} currently running workflow(s):")
                canceled_count = 0
                
                for run in runs:
                    # Get workflow details
                    workflow = repo.get_workflow(run.workflow_id)
                    
                    print(f"\n⏳ Canceling: {workflow.name} (ID: {run.id})")
                    print(f"   - Started: {run.created_at}")
                    print(f"   - URL: {run.html_url}")
                    
                    # Cancel the run
                    try:
                        run.cancel()
                        print("   🛑 Cancel request sent")
                        
                        # Verify cancellation
                        time.sleep(1)
                        run.update()
                        if run.status == "completed":
                            print("   ✅ Successfully canceled")
                            canceled_count += 1
                        else:
                            print(f"   ⚠️ Still running: {run.status}")
                    except GithubException as e:
                        print(f"   ❌ Failed to cancel: {e.data.get('message', str(e))}")
                
                print(f"\n✅ Canceled {canceled_count}/{total_runs} running workflows")
                
            except GithubException as e:
                print(f"❌ Error canceling workflows: {e.data.get('message', str(e))}")
                
        else:
            supported_ops = [
                "list_repos", 
                "create_repo", 
                "delete_repo",
                "toggle_visibility",
                "create_release",
                "set_actions_permissions",
                "run_workflow",
                "cancel_workflows"
            ]
            print(f"❌ Unsupported operation: {operation}")
            print(f"   Supported operations: {', '.join(supported_ops)}")
            
    except GithubException as e:
        print(f"⚠️ GitHub API error: {e.data.get('message', str(e))}")
    except Exception as e:
        print(f"⚠️ Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
