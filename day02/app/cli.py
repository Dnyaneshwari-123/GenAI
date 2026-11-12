
from app.records import load_records, search, count_by, get_by_id

records = load_records()

while True:

    print("\n===== FRAUD RECORDS MENU =====")
    print("1. Print all records")
    print("2. Search fraud")
    print("3. Count by category")
    print("4. Search by ID")
    print("5. Exit")

    choice = input("Enter your choice: ")

    if choice == "1":

        for record in records:
            print(record)

    elif choice == "2":

        keyword = input("Enter fraud name: ")

        result = search(records, keyword)

        for record in result:
            print(record)

        if len(result) == 0:
            print("No records found")

    elif choice == "3":

        counts = count_by(records)

        for category in counts:
            print(category, ":", counts[category])

    elif choice == "4":

        record_id = int(input("Enter ID: "))

        record = get_by_id(records, record_id)

        if record:
            print(record)
        else:
            print("Record not found")

    elif choice == "5":

        print("Thank you!")
        break

    else:
        print("Invalid choice")
