import os
import shutil
from pathlib import Path

def create_directory_structure():
    """Create the required directory structure for the application."""
    directories = [
        'data/content',
        'data/questions',
        'data/distributions',
        'data/user_data/progress',
        'data/user_data/performance'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")

def move_files():
    """Move existing files to their new locations."""
    # Define file mappings (source -> destination)
    file_mappings = {
        'data/math.mmd': 'data/content/math.mmd',
        'data/physics.mmd': 'data/content/physics.mmd',
        'data/chemistry.mmd': 'data/content/chemistry.mmd',
        'data/original_questions.json': 'data/questions/original_questions.json',
        'data/dist_topic.json': 'data/distributions/dist_topic.json'
    }
    
    for source, destination in file_mappings.items():
        if os.path.exists(source):
            # Create destination directory if it doesn't exist
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            
            # Move the file
            shutil.move(source, destination)
            print(f"Moved {source} to {destination}")
        else:
            print(f"Warning: Source file {source} not found")

def create_gitignore():
    """Create .gitignore file to exclude user data."""
    gitignore_content = """# User data
data/user_data/

# Generated questions
data/questions/generated_questions_*.json

# Environment variables
.env

# Python
__pycache__/
*.py[cod]
*$py.class
"""
    
    with open('.gitignore', 'w') as f:
        f.write(gitignore_content)
    print("Created .gitignore file")

def main():
    print("Setting up data structure for JEE-Gurukul...")
    
    # Create directory structure
    create_directory_structure()
    
    # Move existing files
    move_files()
    
    # Create .gitignore
    create_gitignore()
    
    print("\nSetup complete! Your data structure is now organized as follows:")
    print("""
data/
├── content/                  # Static content files
│   ├── math.mmd
│   ├── physics.mmd
│   └── chemistry.mmd
│
├── questions/               # Question database
│   └── original_questions.json
│
├── distributions/          # Topic distributions
│   └── dist_topic.json
│
└── user_data/             # User-specific data (created dynamically)
    ├── progress/          # User progress tracking
    └── performance/       # User performance metrics
    """)

if __name__ == "__main__":
    main() 