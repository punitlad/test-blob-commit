import os
from pathlib import Path

from github import Auth
from github import Github
from github import InputGitTreeElement
from github import GitCommit


class RepositoryService:
    def __init__(self, org, repo, token):
        self.org = org
        self.repo_name = repo
        g = Github(auth=(Auth.Token(token)))
        self.repo = g.get_repo('%s/%s' % (self.org, self.repo_name))

    def create_blob(self, file):
        updated_contents = Path(file).read_text()
        return self.repo.create_git_blob(updated_contents, "utf-8")

    @staticmethod
    def create_tree_element(path, sha):
        print("Adding {} to tree with sha {}".format(path, sha))
        return InputGitTreeElement(path, '100644', "blob", sha=sha)

    def create_commit(self, updated_files, source_file_references, branch, message) -> GitCommit:
        blobs = []
        for file in updated_files:
            blobs.append(self.create_blob(file))

        base_tree = self.repo.get_git_tree(branch, True)

        tree_elements = []
        for index, source_file_ref in enumerate(source_file_references):
            tree_element = self.create_tree_element(source_file_ref, blobs[index].sha)
            tree_elements.append(tree_element)

        git_tree = self.repo.create_git_tree(tree_elements, base_tree)
        print("Creating git commit {} from tree on branch {}".format(base_tree.sha, branch))
        return self.repo.create_git_commit(
            message, git_tree, [self.repo.get_git_commit(base_tree.sha)]
        )

    def publish_tree(self, commit, branch):
        git_ref = self.repo.get_git_ref("heads/{}".format(branch))

        print("Committing to {} with sha {}".format(git_ref.ref, commit.sha))
        git_ref.edit(commit.sha)


if __name__ == '__main__':
    org = os.environ['ORG']
    repo = os.environ['REPO']
    token = os.environ['GITHUB_TOKEN']

    print('debug')
    print('ORG: %s' % org)
    print('REPO: %s' % repo)

    repository = RepositoryService(org, repo, token)
    commit = repository.create_commit(["README.md", "some_file.txt"],
                                      ["README.md", "subfolder/some_file.txt"],
                                      "main",
                                      "its me making another commit")
    repository.publish_tree(commit, "main")
