Lab 1 - Git/DVC and Data Preparation

Question 1

What files are created by uv init, and what are they for?

The uv init command creates the basic structure of a Python project.

The main files are:

pyproject.toml: stores project information, Python requirements, and dependencies.

README.md: used to document the project.

src/: contains the Python source code.

uv.lock: records the exact versions of installed dependencies so the environment can be reproduced consistently.

For example, when Pillow was installed with:

uv add pillow

the dependency was added to the project configuration and lock file.

Question 2

What does dvc init create, what are these files used for, and what should be tracked by Git?

Running:

dvc init

initializes DVC inside the Git repository.

It creates files and folders such as:

.dvc/config: stores the DVC project configuration, including the remote storage configuration.

.dvcignore: tells DVC which files or directories should be ignored.

.dvc/cache: keeps locally cached versions of data objects.

.dvc/tmp: contains temporary files used by DVC.

The configuration files such as .dvc/config and .dvcignore should be committed to Git.

The cache and temporary files should not be pushed to Git because they are managed internally by DVC and may contain large files.

Question 3

Where are the credentials stored? What can be used instead of --global? Should credentials be pushed to GitHub?

When credentials are configured with:

dvc remote modify origin --global ...

they are saved in the user's global DVC configuration instead of inside the repository.

Another useful option is:

--local

which stores sensitive configuration in .dvc/config.local.

The normal repository configuration is stored in .dvc/config.

Credentials such as passwords and access tokens should never be committed or pushed to GitHub.

For this lab, DagsHub authentication can be configured using the DagsHub username and an access token.

Question 4

What happened to .gitignore after running dvc add data?

After running:

dvc add data

DVC updated .gitignore so that Git does not directly track the data directory.

This is important because the dataset contains many large image files.

Instead of storing the images in Git:

Git tracks the DVC metadata file.

DVC manages the actual dataset.

This keeps the Git repository small while still allowing the dataset to be versioned.

Question 5

What is data.dvc and what does it contain?

After tracking the dataset with DVC, a file named:

data.dvc

is created.

This file does not contain the dataset itself.

It stores metadata about the tracked data, including information such as:

the path of the tracked folder,

the hash used to identify the dataset version,

the size of the data,

and the number of files.

A simplified example looks like this:

outs:
- md5: <hash>.dir
  size: <size>
  nfiles: <number>
  path: data

The hash is what allows DVC to identify and restore a specific version of the dataset.

data.dvc should be committed to Git.

Question 6

What is stored on GitHub and what is stored on DagsHub?

GitHub contains the project files that are tracked by Git, such as:

the Python code,

pyproject.toml,

.gitignore,

.dvc/config,

and data.dvc.

The real Food-11 image dataset is not stored directly in the GitHub repository.

The data.dvc file acts as the reference for the data version.

The actual data is uploaded to the DVC remote on DagsHub using:

dvc push

So the responsibilities are separated as follows:

GitHub:
    code + DVC metadata

DagsHub:
    actual dataset files

After the upload was completed, running dvc push again returned:

Everything is up to date.

which confirms that the local DVC data and the DagsHub remote are synchronized.

Question 7

What happens when the GitHub repository is cloned into a new folder? How do we get the data?

When the GitHub repository is cloned into a fresh directory, the Git-tracked files are downloaded.

The actual dataset is not included in the clone because the data directory is managed by DVC.

The repository still contains:

data.dvc

which describes which version of the dataset is required.

To download the actual data from the DVC remote, the command is:

dvc pull

Therefore:

git clone
    -> gets the code and DVC metadata

dvc pull
    -> retrieves the dataset from DagsHub

Question 8

What happens when we checkout an older Git commit and then run dvc checkout?

First, the commits that modified data.dvc were listed with:

git log --oneline -- data.dvc

The relevant commits were:

996c55f Add food11_processed and food11_processed_mini
2de77ac Track data folder with dvc

The older commit was then checked out:

git checkout 2de77ac

After that, running:

dvc checkout

restored the data version associated with that older Git commit.

At that point, only:

food11_raw

was present.

The following folders disappeared:

food11_processed
food11_processed_mini

After switching back to the main branch and running dvc checkout again, the latest data version was restored and all three folders were present again.

This demonstrates the relationship between Git and DVC:

Git versions the code and DVC pointer files.

DVC versions the actual data.

Checking out a Git commit and then running dvc checkout restores the corresponding dataset version.