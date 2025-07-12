import os
import datetime


BASE_PATH = os.path.dirname(os.path.abspath(__file__))
JOURNALS_PATH = os.path.join(BASE_PATH, "journals")



def read_entry(journal_name, entry_name):
    """Read and display a specific entry"""
    entry_path = os.path.join(JOURNALS_PATH, journal_name, entry_name)
    try:
        with open(entry_path, 'r') as file:
            content = file.read()
            print(f"\n--- {entry_name.replace('.txt', '')} ---")
            print(content)
            print("-" * 40)
        return True
    except FileNotFoundError:
        print(f"\nEntry not found: {entry_name}")
        return False
    except Exception as e:
        print(f"\nError reading entry: {str(e)}")
        return False

def read_all_entries(journal_name):
    """Read and display all entries in a journal"""
    entries = list_entries(journal_name)
    if not entries:
        print("\nNo entries found in this journal")
        return False
    
    print(f"\n--- All Entries in '{journal_name}' ---")
    for entry in entries:
        read_entry(journal_name, entry)
    return True


def edit_entry(journal_name, entry_name):
    """Edit an existing journal entry"""
    entry_path = os.path.join(JOURNALS_PATH, journal_name, entry_name)
    
    # Read existing content
    try:
        with open(entry_path, 'r') as file:
            content = file.read()
    except FileNotFoundError:
        print(f"\nEntry not found: {entry_name}")
        return False
    except Exception as e:
        print(f"\nError reading entry: {str(e)}")
        return False
    
    # Extract header and content
    header, _, old_content = content.partition('\n\n')
    
    # Get new content from user
    print(f"\nEditing Entry: {entry_name}")
    print("Current content:\n")
    print(old_content)
    print("\nEnter new content (type 'END' on a new line to finish):")
    
    content_lines = []
    while True:
        line = input()
        if line.strip().upper() == 'END':
            break
        content_lines.append(line)
    new_content = "\n".join(content_lines)
    
    # Add edit timestamp to header
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updated_header = f"{header} | Edited: {timestamp}"
    
    # Save updated entry
    try:
        with open(entry_path, 'w') as file:
            file.write(f"{updated_header}\n\n{new_content}")
        print("\nEntry updated successfully!")
        return True
    except Exception as e:
        print(f"\nError updating entry: {str(e)}")
        return False


def delete_entry(journal_name, entry_name):
    """Delete a specific journal entry"""
    entry_path = os.path.join(JOURNALS_PATH, journal_name, entry_name)
    try:
        os.remove(entry_path)
        print(f"\nEntry '{entry_name}' deleted successfully!")
        
        # Rename subsequent entries to maintain numbering
        entries = list_entries(journal_name)
        for idx, filename in enumerate(entries, 1):
            old_path = os.path.join(JOURNALS_PATH, journal_name, filename)
            new_name = f"entry_{idx}.txt"
            new_path = os.path.join(JOURNALS_PATH, journal_name, new_name)
            os.rename(old_path, new_path)
        
        return True
    except FileNotFoundError:
        print(f"\nEntry not found: {entry_name}")
        return False
    except Exception as e:
        print(f"\nError deleting entry: {str(e)}")
        return False

def delete_journal(journal_name):
    """Delete an entire journal with all its entries"""
    journal_path = os.path.join(JOURNALS_PATH, journal_name)
    if not os.path.exists(journal_path):
        print(f"\nJournal not found: {journal_name}")
        return False
    
    try:
        # Remove all entries first
        for entry in list_entries(journal_name):
            os.remove(os.path.join(journal_path, entry))
        
        # Remove journal folder
        os.rmdir(journal_path)
        print(f"\nJournal '{journal_name}' and all its entries deleted successfully!")
        return True
    except Exception as e:
        print(f"\nError deleting journal: {str(e)}")
        return False

def list_journals():
    """Return sorted list of journals"""

    global JOURNALS_PATH
    list_of_journals = []
    for item in os.listdir(JOURNALS_PATH):
        if os.path.isdir(os.path.join(JOURNALS_PATH, item)):
            list_of_journals.append(item)
    if len(list_of_journals) > 0:        
        return list_of_journals
    else:
        return None
    

def list_entries(journal_name):
    """Return sorted list of entry files in a journal"""
    journal_path = os.path.join(JOURNALS_PATH, journal_name)
    if not os.path.exists(journal_path):
        return []
    
    entries = [entry for entry in os.listdir(journal_path) 
               if entry.startswith("entry_") and entry.endswith(".txt")]
    entries.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))
    return entries


def create_journal(journal_name):
    """Create a new journal folder"""
    journal_path = os.path.join(JOURNALS_PATH, journal_name)
    if not os.path.exists(journal_path):
        os.makedirs(journal_path)
        return True
    return False

def create_entry(journal_name):
    """Create a new journal entry"""
    entries = list_entries(journal_name)
    next_num = len(entries) + 1
    
    # Get content from user
    print("\nEnter your journal entry (type 'END' on a new line to finish):")
    content_lines = []
    while True:
        line = input()
        if line.strip().upper() == 'END':
            break
        content_lines.append(line)
    content = "\n".join(content_lines)
    
    # Add header with timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"Entry {next_num} - Created: {timestamp}"
    full_content = f"{header}\n\n{content}"
    
    # Save entry
    entry_filename = f"entry_{next_num}.txt"
    journal_path = os.path.join(JOURNALS_PATH, journal_name)
    entry_path = os.path.join(journal_path, entry_filename)
    
    try:
        with open(entry_path, 'w') as file:
            file.write(full_content)
        print(f"\nEntry created successfully in '{journal_name}' journal!")
        return True
    except Exception as e:
        print(f"\nError creating entry: {str(e)}")
        return False