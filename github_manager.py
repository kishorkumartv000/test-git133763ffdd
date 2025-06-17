import os
import requests
import tempfile
import time
import re
import shutil
import subprocess
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
    source_url = os.getenv('SOURCE_URL')
    
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
            try:
                print(f"📂 All repositories for {target.login}:")
                private_repos = []
                public_repos = []
                
                # FIXED: Fetch ALL repositories including private ones
                if is_org:
                    repos = target.get_repos(affiliation="owner", visibility="all")
                else:
                    # For user accounts, use the current authenticated user
                    repos = current_user.get_repos(affiliation="owner", visibility="all")
                
                # Fetch and categorize repositories
                for repo in repos:
                    if repo.private:
                        private_repos.append(repo)
                    else:
                        public_repos.append(repo)
                
                # Print private repositories
                if private_repos:
                    print("\n🔒 PRIVATE REPOSITORIES:")
                    for repo in private_repos:
                        print(f"  - {repo.name}")
                        print(f"    URL: {repo.html_url}")
                        print(f"    Size: {repo.size} KB | Last updated: {repo.updated_at}")
                        print(f"    Description: {repo.description or 'No description'}")
                else:
                    print("\nℹ️ No private repositories found")
                
                # Print public repositories
                if public_repos:
                    print("\n🌍 PUBLIC REPOSITORIES:")
                    for repo in public_repos:
                        print(f"  - {repo.name}")
                        print(f"    URL: {repo.html_url}")
                        print(f"    Size: {repo.size} KB | Last updated: {repo.updated_at}")
                        print(f"    Description: {repo.description or 'No description'}")
                else:
                    print("\nℹ️ No public repositories found")
                    
                # Summary statistics
                print(f"\n📊 Summary: {len(private_repos)} private, {len(public_repos)} public, {len(private_repos) + len(public_repos)} total repositories")
                
            except GithubException as e:
                print(f"❌ Error listing repositories: {e.data.get('message', str(e))}")
                
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
                
        elif operation == "set_actions_permissions" and repo_name and actions_enabled is not None:
            try:
                repo = target.get_repo(repo_name)
                enabled = actions_enabled.lower() == "true"
                
                # Use the correct API endpoint to enable/disable actions
                url = f"https://api.github.com/repos/{repo.owner.login}/{repo.name}/actions/permissions"
                headers = {
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json"
                }
                data = {"enabled": enabled}
                
                response = requests.put(url, headers=headers, json=data)
                
                if response.status_code == 204:
                    status = "🟢 ENABLED" if enabled else "🔴 DISABLED"
                    print(f"✅ GitHub Actions: {status}")
                    print(f"   - Repository: {repo_name}")
                else:
                    print(f"❌ Failed to set Actions permissions (HTTP {response.status_code})")
                    print(f"   - {response.json().get('message', 'Unknown error')}")
                
            except GithubException as e:
                print(f"❌ Error setting Actions permissions: {e.data.get('message', str(e))}")
            except Exception as e:
                print(f"❌ Unexpected error: {str(e)}")
                
        elif operation == "run_workflow" and repo_name:
            try:
                repo = target.get_repo(repo_name)
                
                # Get all workflows in the repository
                workflows = list(repo.get_workflows())
                
                if not workflows:
                    print("❌ No workflows found in repository")
                    print("   Please create a workflow in .github/workflows/ directory")
                    return
                
                # Find active or inactive workflows
                workflow_to_run = None
                inactive_workflow = None
                
                for wf in workflows:
                    if wf.state == "active":
                        workflow_to_run = wf
                        break
                    elif wf.state in ["disabled_inactivity", "disabled_manually"]:
                        inactive_workflow = wf
                
                # If no active workflow found but there's an inactive one, try to enable it
                if not workflow_to_run and inactive_workflow:
                    print(f"⚠️ Workflow is disabled ({inactive_workflow.state}). Attempting to enable...")
                    try:
                        # GitHub API endpoint to enable workflow
                        url = f"https://api.github.com/repos/{repo.owner.login}/{repo.name}/actions/workflows/{inactive_workflow.id}/enable"
                        headers = {
                            "Authorization": f"token {token}",
                            "Accept": "application/vnd.github.v3+json",
                            "X-GitHub-Api-Version": "2022-11-28"
                        }
                        response = requests.put(url, headers=headers)
                        
                        if response.status_code == 204:
                            print(f"✅ Enabled workflow: {inactive_workflow.name}")
                            workflow_to_run = inactive_workflow
                            # Wait for workflow to become active
                            time.sleep(2)
                        else:
                            print(f"❌ Failed to enable workflow (HTTP {response.status_code})")
                            print(f"   - {response.json().get('message', 'Unknown error')}")
                            return
                    except Exception as e:
                        print(f"❌ Error enabling workflow: {str(e)}")
                        return
                
                if not workflow_to_run:
                    # If no workflow to run, show available workflows
                    print("❌ No active workflows found. Available workflows:")
                    for i, wf in enumerate(workflows, 1):
                        state_emoji = "🟢" if wf.state == "active" else "🔴"
                        print(f"   {i}. {state_emoji} {wf.name} (state: {wf.state})")
                    print("\n💡 To activate a workflow, go to repository Actions tab")
                    return
                
                # Use repository's default branch
                ref = repo.default_branch
                
                # Trigger workflow dispatch
                workflow_to_run.create_dispatch(ref=ref)
                
                print(f"✅ Triggered workflow: {workflow_to_run.name}")
                print(f"   - Repository: {repo_name}")
                print(f"   - Using default branch: {ref}")
                print(f"   - Workflow file: {workflow_to_run.path}")
                print(f"   - Workflow URL: https://github.com/{repo.full_name}/actions/workflows/{os.path.basename(workflow_to_run.path)}")
                
                # Monitor workflow start
                print("\n⏳ Waiting for workflow to start...")
                time.sleep(3)
                
                # Get latest runs
                runs = workflow_to_run.get_runs()
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
                
        elif operation == "clone_repo" and source_url:
            try:
                # Generate repo name if not provided
                if not repo_name:
                    # Extract repo name from URL
                    repo_name = source_url.rstrip('/').split('/')[-1]
                    if repo_name.endswith('.git'):
                        repo_name = repo_name[:-4]
                    # Clean up special characters
                    repo_name = re.sub(r'[^a-zA-Z0-9_-]', '', repo_name)
                    if not repo_name:
                        repo_name = "cloned-repo"
                
                # Create new repository
                if is_org:
                    new_repo = target.create_repo(
                        name=repo_name,
                        private=True,
                        auto_init=False
                    )
                else:
                    if target.login.lower() != current_user.login.lower():
                        raise ValueError(f"Cannot create repo in another user's account: {target.login}")
                    
                    new_repo = current_user.create_repo(
                        name=repo_name,
                        private=True,
                        auto_init=False
                    )
                
                # Create temp directory for cloning
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Clone the source repository as a mirror
                    print(f"⬇️ Cloning repository: {source_url}")
                    subprocess.run(
                        ['git', 'clone', '--mirror', source_url, temp_dir],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    # Remove pull request refs to avoid "deny updating a hidden ref" errors
                    print("🧹 Cleaning up pull request references...")
                    pull_refs = subprocess.run(
                        ['git', '-C', temp_dir, 'for-each-ref', '--format=%(refname)', 'refs/pull/'],
                        capture_output=True,
                        text=True
                    ).stdout.splitlines()
                    
                    for ref in pull_refs:
                        if ref:  # Ensure ref is not empty
                            subprocess.run(
                                ['git', '-C', temp_dir, 'update-ref', '-d', ref],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE
                            )
                    
                    # Get source repository's default branch
                    print("🔍 Determining source default branch...")
                    head_ref = subprocess.check_output(
                        ['git', 'symbolic-ref', 'HEAD'],
                        cwd=temp_dir,
                        text=True
                    ).strip()
                    default_branch = head_ref.split('/')[-1]
                    print(f"   - Source default branch: {default_branch}")
                    
                    # Push to new repository
                    print(f"⬆️ Pushing to new repository: {new_repo.html_url}")
                    # Add token to URL for authentication
                    push_url = new_repo.clone_url.replace(
                        'https://', 
                        f'https://{token}@'
                    )
                    
                    subprocess.run(
                        ['git', '-C', temp_dir, 'push', '--mirror', push_url],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    # Set default branch in the new repository
                    print("🔄 Setting default branch...")
                    try:
                        new_repo.edit(default_branch=default_branch)
                        print(f"   - Default branch set to: {default_branch}")
                    except GithubException as e:
                        print(f"⚠️ Could not set default branch: {e.data.get('message', str(e))}")
                        print(f"   - Using fallback branch: main")
                        try:
                            # Try to set to 'main' as fallback
                            new_repo.edit(default_branch='main')
                        except:
                            print("   - Could not set any default branch")
                
                print(f"✅ Successfully cloned repository")
                print(f"   - Source: {source_url}")
                print(f"   - Destination: {new_repo.html_url}")
                print(f"   - Repository name: {repo_name}")
                print(f"   - Default branch: {default_branch}")
                
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr.decode().strip() if e.stderr else str(e)
                print(f"❌ Git operation failed: {error_msg}")
            except Exception as e:
                print(f"❌ Error cloning repository: {str(e)}")
                
        else:
            supported_ops = [
                "list_repos", 
                "create_repo", 
                "delete_repo",
                "toggle_visibility",
                "create_release",
                "set_actions_permissions",
                "run_workflow",
                "cancel_workflows",
                "clone_repo"
            ]
            print(f"❌ Unsupported operation: {operation}")
            print(f"   Supported operations: {', '.join(supported_ops)}")
            
    except GithubException as e:
        print(f"⚠️ GitHub API error: {e.data.get('message', str(e))}")
    except Exception as e:
        print(f"⚠️ Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
