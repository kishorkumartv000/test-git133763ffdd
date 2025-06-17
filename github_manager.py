import os
from github import Github, GithubException

def main():
    # Load configuration
    token = os.getenv('GITHUB_TOKEN')
    target_account = os.getenv('TARGET_ACCOUNT')
    operation = os.getenv('OPERATION')
    repo_name = os.getenv('REPO_NAME')
    
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
                
        else:
            supported_ops = [
                "list_repos", 
                "create_repo", 
                "delete_repo",
                "toggle_visibility"
            ]
            print(f"❌ Unsupported operation: {operation}")
            print(f"   Supported operations: {', '.join(supported_ops)}")
            
    except GithubException as e:
        print(f"⚠️ GitHub API error: {e.data.get('message', str(e))}")
    except Exception as e:
        print(f"⚠️ Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
