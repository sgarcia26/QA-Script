# Sergio Garcia
# 10/31/2024

import argparse
from sys import argv
import pandas as pd
import pymongo
from difflib import SequenceMatcher

######################################################################################################################################

# This function covers all parser arguments 

def parse_args():
    parser = argparse.ArgumentParser(description='Insert excel or csv files into a mongDB database')
    parser.add_argument('--qa_excel', type=str, help='Path to the QA Excel file')
    parser.add_argument('--collection', type=str, choices=['collection1', 'collection2'], help='collection to insert data')
    parser.add_argument('--list_owner', type=str, help='Owner of data for listing')
    parser.add_argument('--repeatable_yes', action='store_true', help='List repeatable data')
    parser.add_argument('--blocker_yes', action='store_true', help='List blocker data')
    parser.add_argument('--build_10_8', action='store_true', help='List out data with Build # 10/8')
    parser.add_argument('--print_first_test', action='store_true', help='Print first test case from Collection 2')
    parser.add_argument('--print_middle_test', action='store_true', help='Print middle test case from Collection 2')
    parser.add_argument('--print_last_test', action='store_true', help='Print last test case from Collection 2')
    parser.add_argument('--export_owner_csv', type=str, help='Name of the owner to export data as CSV with their data')
    parser.add_argument('--owner', type=str, help='Owner name for data')
    
    return parser.parse_args()

######################################################################################################################################

# These functions cover reading the excel and connecting to mongdb

def read_excel(file_path):
    try:
        df = pd.read_excel(file_path)
        return df
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return None

def connect_to_mongodb():
    try:
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client["the_reckoning"]
        collection1 = db["collection1"]
        collection2 = db["collection2"]
        return collection1, collection2
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return None, None

######################################################################################################################################

# These fucntions are responsible for inserting the data from the excel file into the mongdb 
# as well as ensuring that no duplicate data are inserted
# "duplicate" data are any Test Case descriptions that are more than 70% similar

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def check_duplicate(test_case, unique_list):
    return test_case in unique_list

def insert_into_collection(collection, data, collection_name):
    try:
        existing_data = pd.DataFrame(list(collection.find()))
        existing_descriptions = existing_data['Test Case'].tolist() if not existing_data.empty else []

        print(f"Initial data in collection {collection_name}: {len(existing_data)}")
        print(f"Initial number of rows to insert: {len(data)}")

        duplicates_count = 0
        to_insert = []

        # Check for duplicates based on the "Test Case" column
        for index, row in data.iterrows():
            current_description = str(row['Test Case']) 
            if not any(similar(current_description, existing) > 0.7 for existing in existing_descriptions):
                to_insert.append(row.to_dict())
            else:
                duplicates_count += 1

        print(f"Duplicates #: {duplicates_count}")

        # Check for empty cells
        empty_rows_count = data.isnull().any(axis=1).sum()
        print(f"Rows with empty cells: {empty_rows_count}")

        # Count 'Repeatable?' = 'Yes'
        repeatable_count = data['Repeatable?'].str.strip().str.lower().eq('yes').sum()
        print(f"Repeatable? #: {repeatable_count}")

        # Count 'Blocker?' = 'Yes'
        blocker_count = data['Blocker?'].str.strip().str.lower().eq('yes').sum()
        print(f"Blocker? #: {blocker_count}")

        # Directly insert records into the collection
        if to_insert:
            result = collection.insert_many(to_insert)
            print(f"Data inserted #: {len(result.inserted_ids)} into {collection_name}.")
            print("Data inserted into MongoDB collection successfully.")
        else:
            print("No valid data to insert into MongoDB collection.")
    except Exception as e:
        print(f"Error inserting data into MongoDB collection: {e}")

######################################################################################################################################

# List all work done by Your user - from both collections(No duplicates)
# This function lists all work done by a specific user from both collections, avoiding any duplicates.

def list_rows_by_owner(owner_name, collection1, collection2):
    """List rows based on the specified owner's name from both collections while avoiding duplicates."""
    try:
        results_collection1 = list(collection1.find({"Test Owner": owner_name}))
        results_collection2 = list(collection2.find({"Test Owner": owner_name}))

        # Combine results from both collections and track unique test cases
        combined_results = results_collection1 + results_collection2
        unique_results = []
        seen_test_cases = set()
        duplicate_count = 0 

        # Check for exact duplicates between collections and remove if found.
        for result in combined_results:
            test_case_description = result['Test Case']
            if test_case_description not in seen_test_cases:
                unique_results.append(result)
                seen_test_cases.add(test_case_description)
            else:
                duplicate_count += 1 

        print(f"Total rows found for owner '{owner_name}': {len(unique_results)}")
        print(f"Number of duplicates found: {duplicate_count}\n") 

        for row in unique_results:
            for key, value in row.items():
                print(f"{key}: {value}")
            print()
            
    except Exception as e:
        print(f"Error listing rows by owner: {e}")

######################################################################################################################################

# All repeatable bugs- from both collections(No duplicates)
# This function lists all repeatable bugs, aka if "yes" is found under the repeatable column, between both collections.
# duplicates are discarded

def list_repeatable_data(collection1, collection2):
    """List rows where 'Repeatable?' is 'Yes' from both collections while avoiding duplicates."""
    try:
        results_collection1 = list(collection1.find({"Repeatable?": {'$regex': '^yes$', '$options': 'i'}}))
        results_collection2 = list(collection2.find({"Repeatable?": {'$regex': '^yes$', '$options': 'i'}}))

        combined_results = results_collection1 + results_collection2
        unique_results = []
        seen_test_cases = set()
        duplicate_count = 0  

        # Check for exact duplicates between collections and remove if found.
        for result in combined_results:
            test_case_description = result['Test Case']
            if test_case_description not in seen_test_cases:
                unique_results.append(result)
                seen_test_cases.add(test_case_description)
            else:
                duplicate_count += 1 
                
        for row in unique_results:
            for key, value in row.items():
                print(f"{key}: {value}") 
            print()  
            
        print(f"Total repeatable rows found: {len(unique_results)}")
        print(f"Number of duplicates found: {duplicate_count}\n")

    except Exception as e:
        print(f"Error listing repeatable data: {e}")

######################################################################################################################################

# All blocker bugs- from both collections(No duplicates)
# This function lists all blocker bugs, aka if "yes" is found under the blocker column, between both collections.
# duplicates are discarded

def list_blocker_yes_data(collection1, collection2):
    """List rows where 'Blocker?' is 'Yes' from both collections while avoiding duplicates."""
    try:
        results_collection1 = list(collection1.find({"Blocker?": {'$regex': '^yes$', '$options': 'i'}}))
        results_collection2 = list(collection2.find({"Blocker?": {'$regex': '^yes$', '$options': 'i'}}))

        combined_results = results_collection1 + results_collection2
        unique_results = []
        seen_test_cases = set()
        duplicate_count = 0 

        # Check for exact duplicates between collections and remove if found.
        for result in combined_results:
            test_case_description = result['Test Case']
            if test_case_description not in seen_test_cases:
                unique_results.append(result)
                seen_test_cases.add(test_case_description)
            else:
                duplicate_count += 1 
                
        for row in unique_results:
            for key, value in row.items():
                print(f"{key}: {value}") 
            print() 
            
        print(f"Total blocker rows found: {len(unique_results)}")
        print(f"Number of duplicates found: {duplicate_count}\n")

    except Exception as e:
        print(f"Error listing blocker data: {e}")

######################################################################################################################################

# All reports on build 10/8/2024- from both collections(No duplicates)
# This function lists all data from 10/8/2024 between both collections.
# duplicates are discarded

def list_build_10_8_data(collection1, collection2):
    """List rows where the 'Build #' contains '10' and '8' from both collections while avoiding duplicates."""
    try:
        collection1_data = pd.DataFrame(list(collection1.find()))
        collection2_data = pd.DataFrame(list(collection2.find()))

        collection1_data['Match'] = collection1_data['Build #'].apply(
            lambda x: '10' in str(x) and '8' in str(x)
        )
        
        collection2_data['Match'] = collection2_data['Build #'].apply(
            lambda x: '10' in str(x) and '8' in str(x)
        )

        matched_collection1 = collection1_data[collection1_data['Match']]
        matched_collection2 = collection2_data[collection2_data['Match']]

        combined_results = pd.concat([matched_collection1, matched_collection2])

        combined_results.drop(columns=['Match'], inplace=True)

         # Check for exact duplicates between collections and remove if found.
        unique_results = []
        seen_test_cases = set()
        duplicate_count = 0

        for index, row in combined_results.iterrows():
            test_case_description = row['Test Case']
            if test_case_description not in seen_test_cases:
                unique_results.append(row)
                seen_test_cases.add(test_case_description)
            else:
                duplicate_count += 1 

        for row in unique_results:
            for key, value in row.items():
                print(f"{key}: {value}") 
            print() 

        print(f"Total build rows found with '10' and '8': {len(unique_results)}")
        print(f"Number of duplicates found: {duplicate_count}\n")  # Print duplicate count

    except Exception as e:
        print(f"Error listing build data: {e}")

######################################################################################################################################

# These functions helps find a sepcific test case (first, middle last) of a given user
# The user's data is put into a list and the respective index is returned.

def print_test_case(case, case_type, user_name):
    """Helper function to print details of a test case."""
    print(f"{case_type} Test Case for {user_name}:")
    print(f"  Test #: {case['Test #']}")
    print(f"  Build #: {case['Build #']}")
    print(f"  Category: {case['Category']}")
    print(f"  Test Case: {case['Test Case']}")
    print(f"  Expected Result: {case['Expected Result']}")
    print(f"  Actual Result: {case['Actual Result']}")
    print(f"  Repeatable?: {case['Repeatable?']}")
    print(f"  Blocker?: {case['Blocker?']}")
    print(f"  Test Owner: {case['Test Owner']}")

def print_first_case_by_user(collection2, user_name):
    """Print the first test case for a specific user in Collection 2."""
    try:
        user_cases = list(collection2.find({"Test Owner": user_name}))

        if not user_cases:
            print(f"No test cases found for user: {user_name}.")
            return

        first_case = user_cases[0]
        print_test_case(first_case, "Last", user_name)

    except Exception as e:
        print(f"Error printing last test case for user {user_name}: {e}")

        
def print_middle_case_by_user(collection2, user_name):
    """Print the middle test case for a specific user in Collection 2."""
    try:
        user_cases = list(collection2.find({"Test Owner": user_name}))

        if not user_cases:
            print(f"No test cases found for user: {user_name}.")
            return

        middle_index = len(user_cases) // 2
        middle_case = user_cases[middle_index]
        print_test_case(middle_case, "Middle", user_name)

    except Exception as e:
        print(f"Error printing middle test case for user {user_name}: {e}")

def print_last_case_by_user(collection2, user_name):
    """Print the last test case for a specific user in Collection 2."""
    try:
        user_cases = list(collection2.find({"Test Owner": user_name}))

        if not user_cases:
            print(f"No test cases found for user: {user_name}.")
            return

        last_case = user_cases[-1]
        print_test_case(last_case, "Last", user_name)

    except Exception as e:
        print(f"Error printing last test case for user {user_name}: {e}")

######################################################################################################################################

# This function exports a CSV file of a specific user, only containing their data from collection 2.

def export_user_data_to_csv(collection2, user_name):
    """Export data for a specific user from both collections to a CSV file."""
    try:
        user_cases_collection2 = list(collection2.find({"Test Owner": user_name}))

        # Create a DataFrame
        df = pd.DataFrame(user_cases_collection2)

        # Define the directory where you want to save the CSV
        export_directory = r"C:\Users\garci\ProTest2"

        # Define the CSV file name with the desired directory
        csv_file_name = f"{export_directory}\\{user_name.replace(' ', '_')}_export.csv"

        print(f"Exporting to: {csv_file_name}")

        df.to_csv(csv_file_name, index=False)

        print(f"Data exported successfully to {csv_file_name}.")
        
    except Exception as e:
        print(f"Error exporting data for user {user_name}: {e}")

######################################################################################################################################

def main():
    args = parse_args()
    collection1, collection2 = connect_to_mongodb()

    if collection1 is None or collection2 is None:
        return

    qa_data = None
    if args.qa_excel:
        qa_data = read_excel(args.qa_excel)

    if qa_data is None and args.collection:
        print("QA data is required for the specified collection operation.")
        return

    if args.collection and qa_data is not None:
        if args.collection == 'collection1':
            insert_into_collection(collection1, qa_data, "Collection 1")
        elif args.collection == 'collection2':
            insert_into_collection(collection2, qa_data, "Collection 2")

    if args.list_owner:
        list_rows_by_owner(args.list_owner, collection1, collection2)
        
    if args.repeatable_yes:
        list_repeatable_data(collection1, collection2)

    if args.blocker_yes:
        list_blocker_yes_data(collection1, collection2)

    if args.build_10_8:
        list_build_10_8_data(collection1, collection2)

    if args.print_first_test:
        print_first_case_by_user(collection2,args.owner)
        
    if args.print_middle_test:
        print_middle_case_by_user(collection2,args.owner)
        
    if args.print_last_test:
        print_last_case_by_user(collection2,args.owner)

    if args.export_owner_csv:
        export_user_data_to_csv( collection2, args.export_owner_csv)

if __name__ == "__main__":
    main()