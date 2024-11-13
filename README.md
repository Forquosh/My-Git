# My Git Implementation in Python

  This project is a simple Git implementation in Python, built from scratch to demonstrate core functionalities of Git, including cloning a repository, writing objects, creating commits, and more. It was written and tested throughout the "Build your own git" challenge on Codecrafters. The code supports several key Git commands and can be expanded upon for learning purposes.

## Features

  - **Initialize a Git Repository**: Manually create the `.git` folder and initialize the necessary directory structure.
  - **Create Objects**: Store blobs, commits, and trees in a way that mirrors how Git stores data.
  - **Commit Trees**: Simulate the creation of commit objects linked to tree objects.
  - **Clone Repositories**: Clone repositories by fetching data from remote servers.
  - **Read and Decompress Git Objects**: View the contents of Git objects stored in the `.git` folder.

## Supported Git Commands

  The project supports the following commands (executed through the Python script):
  
  1. **`init`**: Initialize a new Git repository.

     `./your_program.sh init`
  
  2. **`hash-object -w <file>`**: Write the contents of a file into the .git/objects folder as a blob.
     
     `./your_program.sh hash-object -w <file>`
  
  3. **`write-tree`**: Write a tree object representing the current directory structure.

     `./your_program.sh write-tree`
  
  4. **`commit-tree <tree_sha> -p <commit_sha> -m <message>`**: Create a commit object from a tree object, linking it to a parent commit and adding a message.
     
     `./your_program.sh commit-tree <tree_sha> -p <commit_sha> -m <message>`
     
  5. **`clone <repo_url> <directory>`**: Clone a remote Git repository into a specified directory.
     
     `./your_program.sh clone <repo_url> <directory>`

## How the Code Works

**Cloning a Repository**

  The clone command initiates by creating a .git folder and fetching refs from the remote repository. After retrieving the pack file, the script processes the objects, decompressing and creating them within the cloned directory.

**The steps include**:

  - Fetching refs from the remote URL.
  - Fetching the pack file containing repository objects.
  - Decompressing objects and creating corresponding tree, blob, and commit files.
  - Rendering the directory structure based on the tree object.
  - Creating and Storing Objects
  - When files are committed, they are stored as objects in the .git/objects folder using SHA-1 hashes. The create_object function handles creating these objects by compressing and writing data to the object store.

## Installation and Usage

  1. **Clone the project**:
     
     git clone https://github.com/Forquosh/My-Git <your_directory>

     `cd <your_directory>`
     
  3. **Run the script**: Use your_program.sh to run the different Git commands. For example, to initialize a repository:
     
     `./your_program.sh init`

## Requirements

  1. Python 3.10 or higher.
  2. zlib and hashlib libraries (standard in Python).
  3. An internet connection for cloning remote repositories.
     
## Future Improvements

  1. Add support for more Git commands.
  2. Optimize object handling and compression.
  3. Improve error handling and user feedback.
