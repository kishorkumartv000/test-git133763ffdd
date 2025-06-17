import os
import requests
import tempfile
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
    
    try:
        # Get target user/org
        try:
            target = g.get_organization(target_account)
        except GithubException:
            target = g.get_user(target_account)
        
        # Perform operations
        if operation == "list_repos":
            print(f"Repositories for {target.login}:")
            for repo in target.get_repos():
                visibility = "🔒 PRIVATE" if repo.private else "🌍 PUBLIC"
                print(f"- {visibility}: {repo.name} (URL: {repo.html_url})")
                
        elif operation == "create_repo" and repo_name:
            repo = target.create_repo(
                name=repo_name,
                private=True,
                auto_init=True
            )
            print(f"✅ Created repository: {repo.html_url}")
            print(f"   - Visibility: {'Private' if repo.private else 'Public'}")
            
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
                current = repo.get_actions_permissions()
                
                # Build new permissions object
                new_permissions = {}
                
                # Actions enabled/disabled
                if actions_enabled is not None:
                    enabled = actions_enabled.lower() == "true"
                    new_permissions["enabled"] = enabled
                    status = "🟢 ENABLED" if enabled else "🔴 DISABLED"
                    print(f"Set Actions: {status}")
                
                # All actions configuration
                if allow_all_actions is not None:
                    allow_all = allow_all_actions.lower() == "true"
                    new_permissions["allowed_actions"] = "all" if allow_all else "selected"
                    status = "✅ ALLOWED" if allow_all else "🚫 RESTRICTED"
                    print(f"All Actions: {status}")
                
                # Reusable workflows configuration
                if allow_reusable_workflows is not None:
                    allow_reusable = allow_reusable_workflows.lower() == "true"
                    new_permissions["allowed_actions"] = "selected"  # Required for reusable workflows
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
                updated = repo.get_actions_permissions()
                print("\nCurrent Actions Settings:")
                print(f"- Enabled: {'🟢 YES' if updated.enabled else '🔴 NO'}")
                print(f"- All Actions: {'✅ ALLOWED' if updated.allowed_actions == 'all' else '🚫 RESTRICTED'}")
                print(f"- Reusable Workflows: {'✅ ALLOWED' if updated.enabled_repositories == 'all' else '🚫 BLOCKED'}")
                
            except GithubException as e:
                print(f"❌ Error setting Actions permissions: {e.data.get('message', str(e))}")
                
        else:
            supported_ops = [
                "list_repos", 
                "create_repo", 
                "delete_repo",
                "toggle_visibility",
                "create_release",
                "set_actions_permissions"
            ]
            print(f"❌ Unsupported operation: {operation}")
            print(f"   Supported operations: {', '.join(supported_ops)}")
            
    except GithubException as e:
        print(f"⚠️ GitHub API error: {e.data.get('message', str(e))}")
    except Exception as e:
        print(f"⚠️ Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
