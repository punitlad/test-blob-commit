import os
from pathlib import Path
from pprint import pprint

from github import Auth
from github import GitCommit
from github import Github
from github import InputGitTreeElement
from github import UnknownObjectException


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
        for index, filename in enumerate(updated_files):
            if self.is_diff(filename, source_file_references[index]):
                blobs.append({"blob": self.create_blob(filename), "source_ref": source_file_references[index]})

        base_tree = self.repo.get_git_tree(branch, True)

        tree_elements = []
        if blobs:
            print("in here")
            for blob in blobs:
                tree_element = self.create_tree_element(blob["source_ref"], blob["blob"].sha)
                tree_elements.append(tree_element)

            git_tree = self.repo.create_git_tree(tree_elements, base_tree)
            print("Creating git commit {} from tree on branch {}".format(base_tree.sha, branch))
            return self.repo.create_git_commit(
                message, git_tree, [self.repo.get_git_commit(base_tree.sha)]
            )
        else:
            return None

    def publish_tree(self, commit, branch):
        git_ref = self.repo.get_git_ref("heads/{}".format(branch))

        print("Committing to {} with sha {}".format(git_ref.ref, commit.sha))
        git_ref.edit(commit.sha)

    def is_diff(self, filename, source_ref):
        print("Diffing {} against {}...".format(filename, source_ref), end="")
        try:
            contents = self.repo.get_contents(source_ref, "main")
            is_diff = Path(filename).read_text() != contents.decoded_content.decode('ascii')
            if is_diff:
                print("Changes found")
            else:
                print("No changes found")
            return is_diff
        except UnknownObjectException:
            print("New file")
            return True


if __name__ == '__main__':
    org = os.environ['ORG']
    repo = os.environ['REPO']
    token = os.environ['GITHUB_TOKEN']
    updated_files = os.environ['UPDATED_FILES']  # comma separated list
    source_refs = os.environ['SOURCE_REFS']  # comma separated list

    print('ORG: %s' % org)
    print('REPO: %s' % repo)
    print('UPDATED_FILES: %s' % updated_files)
    print('SOURCE_REF: %s' % source_refs)

    repository = RepositoryService(org, repo, token)
    commit = repository.create_commit(updated_files.split(","), source_refs.split(","), "main",
                                      "its me making another commit")
    if commit is not None:
        print("Committing changes.")
        repository.publish_tree(commit, "main")
    else:
        print("No changes. Skipping commit")
