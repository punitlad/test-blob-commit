import os
from pathlib import Path

from github import Auth
from github import GitCommit
from github import Github
from github import InputGitTreeElement
from github import UnknownObjectException


class RepositoryService:
    def __init__(self, org_name, repo_name, auth_token):
        g = Github(auth=(Auth.Token(auth_token)))
        org_repo = '%s/%s' % (org_name, repo_name)
        print('Setting Github repository connectivity to {}'.format(org_repo))
        self.repo = g.get_repo(org_repo)

    def create_blob(self, file):
        updated_contents = Path(file).read_text()
        return self.repo.create_git_blob(updated_contents, 'utf-8')

    @staticmethod
    def create_tree_element(path, sha):
        print('Adding {} to tree with sha {}'.format(path, sha))
        return InputGitTreeElement(path, '100644', 'blob', sha=sha)

    def create_commit(self, updated_files, source_file_references, branch, message) -> GitCommit:
        blobs = []
        for index, filename in enumerate(updated_files):
            if self.is_diff(filename, source_file_references[index]):
                blobs.append({'blob': self.create_blob(filename), 'source_ref': source_file_references[index]})

        base_tree = self.repo.get_git_tree(branch, True)

        tree_elements = []
        if blobs:
            for blob in blobs:
                tree_element = self.create_tree_element(blob['source_ref'], blob['blob'].sha)
                tree_elements.append(tree_element)

            git_tree = self.repo.create_git_tree(tree_elements, base_tree)
            print('Creating git commit {} from tree on branch {}'.format(base_tree.sha, branch))
            return self.repo.create_git_commit(
                message, git_tree, [self.repo.get_git_commit(base_tree.sha)]
            )
        else:
            return None

    def publish_tree(self, commit, branch):
        git_ref = self.repo.get_git_ref('heads/{}'.format(branch))

        print('Committing to {} with sha {}'.format(git_ref.ref, commit.sha))
        git_ref.edit(commit.sha)

    def is_diff(self, filename, source_ref):
        print('Diffing {} against {}...'.format(filename, source_ref), end="")
        try:
            contents = self.repo.get_contents(source_ref, 'main')
            is_diff = Path(filename).read_text() != contents.decoded_content.decode('ascii')
            print('Changes found') if is_diff else print('No changes found')
            return is_diff
        except UnknownObjectException:
            print('New file')
            return True


if __name__ == '__main__':
    repository = RepositoryService(os.environ['ORG'], os.environ['REPO'], os.environ['GITHUB_TOKEN'])
    commit = repository.create_commit(
        os.environ['UPDATED_FILES'].split(','),
        os.environ['SOURCE_REFS'].split(','),
        'main',
        'push from %s build %s' % ((os.environ['CIRCLE_PROJECT_REPONAME']), (os.environ['CIRCLE_BUILD_NUM']))
    )

    if commit is not None:
        print('Committing changes...', end='')
        repository.publish_tree(commit, 'main')
        print('Committed')
    else:
        print('No changes. Skipping commit')