import os
from github import Github, GithubException
from dotenv import load_dotenv

load_dotenv()

def main():
    # Load configuration
    token = os.getenv('GITHUB_TOKEN')
    target_account = os.getenv('TARGET_ACCOUNT')
    operation = os.getenv('OPERATION')
    repo_name = os.getenv('REPO_NAME')
    
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
                print(f"- {repo.name}")
                
        elif operation == "create_repo" and repo_name:
            repo = target.create_repo(
                name=repo_name,
                private=True,
                auto_init=True
            )
            print(f"Created repository: {repo.html_url}")
            
        elif operation == "delete_repo" and repo_name:
            try:
                repo = target.get_repo(repo_name)
                repo.delete()
                print(f"Deleted repository: {repo_name}")
            except GithubException as e:
                print(f"Error deleting repo: {e.data['message']}")
                
        else:
            print(f"Unsupported operation: {operation}")
            
    except GithubException as e:
        print(f"GitHub API error: {e.data['message']}")

if __name__ == "__main__":
    main()
