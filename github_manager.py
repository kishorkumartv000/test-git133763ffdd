import os
from github import Github, GithubException

def main():
    # Load configuration from environment variables
    token = os.getenv('GITHUB_TOKEN')
    target_account = os.getenv('TARGET_ACCOUNT')
    operation = os.getenv('OPERATION')
    repo_name = os.getenv('REPO_NAME')
    
    # Validate required inputs
    if not token:
        raise ValueError("Missing GITHUB_TOKEN in environment variables")
    if not target_account:
        raise ValueError("Missing TARGET_ACCOUNT in environment variables")
    
    # Initialize GitHub API client
    g = Github(token)
    
    try:
        # Get target (user or organization)
        try:
            target = g.get_organization(target_account)
        except GithubException:
            target = g.get_user(target_account)
        
        # Execute operations
        if operation == "list_repos":
            print(f"Repositories for {target.login}:")
            for repo in target.get_repos():
                print(f"- {repo.name} ({'private' if repo.private else 'public'})")
                
        elif operation == "create_repo":
            if not repo_name:
                raise ValueError("repo_name is required for create_repo operation")
            repo = target.create_repo(
                name=repo_name,
                private=True,
                auto_init=True
            )
            print(f"✅ Created repository: {repo.html_url}")
            
        elif operation == "delete_repo":
            if not repo_name:
                raise ValueError("repo_name is required for delete_repo operation")
            try:
                repo = target.get_repo(repo_name)
                repo.delete()
                print(f"✅ Deleted repository: {repo_name}")
            except GithubException as e:
                error_msg = e.data.get('message', str(e))
                print(f"❌ Error deleting repo: {error_msg}")
                
        else:
            supported_ops = ["list_repos", "create_repo", "delete_repo"]
            print(f"❌ Unsupported operation: {operation}. Supported operations: {', '.join(supported_ops)}")
            
    except GithubException as e:
        error_msg = e.data.get('message', str(e))
        print(f"⚠️ GitHub API error: {error_msg}")
    except Exception as e:
        print(f"⚠️ Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
