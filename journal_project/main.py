import os
import datetime
import util

# Base directory for storing journals
BASE_PATH = os.path.abspath(__file__)
BASE_DIR = "journals"

def initialize_journal_directory():
    """Create the base journal directory if it doesn't exist"""
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)

def list_journals():
    """Return a list of existing journals"""
    return [journal for journal in os.listdir(BASE_DIR) 
            if os.path.isdir(os.path.join(BASE_DIR, journal))]

def list_entries(journal_name):
    """Return sorted list of entry files in a journal"""
    journal_path = os.path.join(BASE_DIR, journal_name)
    if not os.path.exists(journal_path):
        return []
    
    entries = [entry for entry in os.listdir(journal_path) 
               if entry.startswith("entry_") and entry.endswith(".txt")]
    entries.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))
    return entries

def create_journal(journal_name):
    """Create a new journal folder"""
    journal_path = os.path.join(BASE_DIR, journal_name)
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
    journal_path = os.path.join(BASE_DIR, journal_name)
    entry_path = os.path.join(journal_path, entry_filename)
    
    try:
        with open(entry_path, 'w') as file:
            file.write(full_content)
        print(f"\nEntry created successfully in '{journal_name}' journal!")
        return True
    except Exception as e:
        print(f"\nError creating entry: {str(e)}")
        return False

def read_entry(journal_name, entry_name):
    """Read and display a specific entry"""
    entry_path = os.path.join(BASE_DIR, journal_name, entry_name)
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
    entry_path = os.path.join(BASE_DIR, journal_name, entry_name)
    
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
    entry_path = os.path.join(BASE_DIR, journal_name, entry_name)
    try:
        os.remove(entry_path)
        print(f"\nEntry '{entry_name}' deleted successfully!")
        
        # Rename subsequent entries to maintain numbering
        entries = list_entries(journal_name)
        for idx, filename in enumerate(entries, 1):
            old_path = os.path.join(BASE_DIR, journal_name, filename)
            new_name = f"entry_{idx}.txt"
            new_path = os.path.join(BASE_DIR, journal_name, new_name)
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
    journal_path = os.path.join(BASE_DIR, journal_name)
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

def main_menu():
    """Display main menu and handle user choices"""
    initialize_journal_directory()
    
    while True:
        print("\n" + "=" * 40)
        print("DIGITAL JOURNAL MANAGER")
        print("=" * 40)
        print("1. Create New Entry")
        print("2. Read Entries")
        print("3. Edit Entry")
        print("4. Delete Entry or Journal")
        print("5. Exit")
        
        choice = input("\nChoose an option (1-5): ")
        
        # Create New Entry
        if choice == '1':
            journals = list_journals()
            if journals:
                print("\nAvailable Journals:")
                for idx, journal in enumerate(journals, 1):
                    print(f"{idx}. {journal}")
                print(f"{len(journals)+1}. Create New Journal")
                
                journal_choice = input("\nSelect journal (number): ")
                try:
                    journal_idx = int(journal_choice) - 1
                    if journal_idx < len(journals):
                        journal_name = journals[journal_idx]
                    elif journal_idx == len(journals):
                        journal_name = input("\nEnter new journal name: ")
                        create_journal(journal_name)
                    else:
                        print("\nInvalid selection")
                        continue
                    create_entry(journal_name)
                except ValueError:
                    print("\nPlease enter a valid number")
            else:
                journal_name = input("\nNo journals found. Create new journal name: ")
                if create_journal(journal_name):
                    create_entry(journal_name)
        
        # Read Entries
        elif choice == '2':
            journals = list_journals()
            if not journals:
                print("\nNo journals available")
                continue
                
            print("\nAvailable Journals:")
            for idx, journal in enumerate(journals, 1):
                print(f"{idx}. {journal}")
                
            try:
                journal_idx = int(input("\nSelect journal (number): ")) - 1
                if 0 <= journal_idx < len(journals):
                    journal_name = journals[journal_idx]
                    entries = list_entries(journal_name)
                    
                    if not entries:
                        print("\nNo entries in this journal")
                        continue
                        
                    print("\nRead Options:")
                    print("1. Read specific entry")
                    print("2. Read all entries")
                    
                    read_choice = input("\nChoose option (1-2): ")
                    if read_choice == '1':
                        print("\nAvailable Entries:")
                        for idx, entry in enumerate(entries, 1):
                            print(f"{idx}. {entry}")
                        try:
                            entry_idx = int(input("\nSelect entry (number): ")) - 1
                            if 0 <= entry_idx < len(entries):
                                read_entry(journal_name, entries[entry_idx])
                        except ValueError:
                            print("\nInvalid entry selection")
                    elif read_choice == '2':
                        read_all_entries(journal_name)
                    else:
                        print("\nInvalid choice")
                else:
                    print("\nInvalid journal selection")
            except ValueError:
                print("\nPlease enter a valid number")
        
        # Edit Entry
        elif choice == '3':
            journals = list_journals()
            if not journals:
                print("\nNo journals available")
                continue
                
            print("\nAvailable Journals:")
            for idx, journal in enumerate(journals, 1):
                print(f"{idx}. {journal}")
                
            try:
                journal_idx = int(input("\nSelect journal (number): ")) - 1
                if 0 <= journal_idx < len(journals):
                    journal_name = journals[journal_idx]
                    entries = list_entries(journal_name)
                    
                    if not entries:
                        print("\nNo entries in this journal")
                        continue
                        
                    print("\nAvailable Entries:")
                    for idx, entry in enumerate(entries, 1):
                        print(f"{idx}. {entry}")
                        
                    try:
                        entry_idx = int(input("\nSelect entry to edit (number): ")) - 1
                        if 0 <= entry_idx < len(entries):
                            edit_entry(journal_name, entries[entry_idx])
                        else:
                            print("\nInvalid entry selection")
                    except ValueError:
                        print("\nInvalid entry selection")
                else:
                    print("\nInvalid journal selection")
            except ValueError:
                print("\nPlease enter a valid number")
        
        # Delete Entry or Journal
        elif choice == '4':
            journals = list_journals()
            if not journals:
                print("\nNo journals available")
                continue
                
            print("\nAvailable Journals:")
            for idx, journal in enumerate(journals, 1):
                print(f"{idx}. {journal}")
                
            try:
                journal_idx = int(input("\nSelect journal (number): ")) - 1
                if 0 <= journal_idx < len(journals):
                    journal_name = journals[journal_idx]
                    
                    print("\nDelete Options:")
                    print("1. Delete specific entry")
                    print("2. Delete entire journal")
                    
                    delete_choice = input("\nChoose option (1-2): ")
                    if delete_choice == '1':
                        entries = list_entries(journal_name)
                        if not entries:
                            print("\nNo entries in this journal")
                            continue
                            
                        print("\nAvailable Entries:")
                        for idx, entry in enumerate(entries, 1):
                            print(f"{idx}. {entry}")
                            
                        try:
                            entry_idx = int(input("\nSelect entry to delete (number): ")) - 1
                            if 0 <= entry_idx < len(entries):
                                delete_entry(journal_name, entries[entry_idx])
                            else:
                                print("\nInvalid entry selection")
                        except ValueError:
                            print("\nInvalid entry selection")
                    elif delete_choice == '2':
                        confirm = input(f"\nDelete entire journal '{journal_name}'? (y/n): ")
                        if confirm.lower() == 'y':
                            delete_journal(journal_name)
                        else:
                            print("\nDeletion canceled")
                    else:
                        print("\nInvalid choice")
                else:
                    print("\nInvalid journal selection")
            except ValueError:
                print("\nPlease enter a valid number")
        
        # Exit
        elif choice == '5':
            print("\nGoodbye!")
            break
        
        else:
            print("\nInvalid choice. Please select 1-5")

if __name__ == "__main__":
    main_menu()