import os
import datetime
import util


# Base directory for storing journals
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
JOURNALS_PATH = os.path.join(BASE_PATH, "journals")





def check_journals():
    if not os.path.exists(JOURNALS_PATH):
        os.mkdir(JOURNALS_PATH)

def print_menu():
    print("\n" + "=" * 40)
    print("DIGITAL JOURNAL MANAGER")
    print("=" * 40)
    print("1. Read Entries")
    print("2. Create New Entry")
    print("3. Edit Entry")
    print("4. Delete Entry or Journal")
    print("0. Exit")


        
   

def main():
    """Display main menu and handle user choices"""
    check_journals()
    
    while True:
        print_menu()        
        choice = input("\nPlease choose your action (0-4): ")
        match choice:
        # Read Entries
            case "1":
                journals = util.list_journals()
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
                        entries = util.list_entries(journal_name)
                        
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
                                    util.read_entry(journal_name, entries[entry_idx])
                            except ValueError:
                                print("\nInvalid entry selection")
                        elif read_choice == '2':
                            util.read_all_entries(journal_name)
                        else:
                            print("\nInvalid choice")
                    else:
                        print("\nInvalid journal selection")
                except ValueError:
                    print("\nPlease enter a valid number")
            

            case "2":
                journals = util.list_journals()
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
                            util.create_journal(journal_name)
                        else:
                            print("\nInvalid selection")
                            continue
                        util.create_entry(journal_name)
                    except ValueError:
                        print("\nPlease enter a valid number")
                else:
                    journal_name = input("\nNo journals found. Create new journal name: ")
                    if util.create_journal(journal_name):
                        util.create_entry(journal_name)    
                # Edit Entry
            case "3":
                journals = util.list_journals()
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
                        entries = util.list_entries(journal_name)
                        
                        if not entries:
                            print("\nNo entries in this journal")
                            continue
                            
                        print("\nAvailable Entries:")
                        for idx, entry in enumerate(entries, 1):
                            print(f"{idx}. {entry}")
                            
                        try:
                            entry_idx = int(input("\nSelect entry to edit (number): ")) - 1
                            if 0 <= entry_idx < len(entries):
                                util.edit_entry(journal_name, entries[entry_idx])
                            else:
                                print("\nInvalid entry selection")
                        except ValueError:
                            print("\nInvalid entry selection")
                    else:
                        print("\nInvalid journal selection")
                except ValueError:
                    print("\nPlease enter a valid number")
            
            # Delete Entry or Journal
            case "4":
                journals = util.list_journals()
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
                            entries = util.list_entries(journal_name)
                            if not entries:
                                print("\nNo entries in this journal")
                                continue
                                
                            print("\nAvailable Entries:")
                            for idx, entry in enumerate(entries, 1):
                                print(f"{idx}. {entry}")
                                
                            try:
                                entry_idx = int(input("\nSelect entry to delete (number): ")) - 1
                                if 0 <= entry_idx < len(entries):
                                    util.delete_entry(journal_name, entries[entry_idx])
                                else:
                                    print("\nInvalid entry selection")
                            except ValueError:
                                print("\nInvalid entry selection")
                        elif delete_choice == '2':
                            confirm = input(f"\nDelete entire journal '{journal_name}'? (y/n): ")
                            if confirm.lower() == 'y':
                                util.delete_journal(journal_name)
                            else:
                                print("\nDeletion canceled")
                        else:
                            print("\nInvalid choice")
                    else:
                        print("\nInvalid journal selection")
                except ValueError:
                    print("\nPlease enter a valid number")
            
            # Exit
            case "0":
                print("\nFinished, bye!")
                break
            
            case _:
                print("\nInvalid choice. Please select 0-4")
       

if __name__ == "__main__":
    main()