while True:
    print("\n--- CyberSuraksha Menu ---")
    print("1. About CyberSuraksha")
    print("2. Sample questions")
    print("3. Rule check")
    print("0. Exit")

    choice = input("Enter your choice: ")

    if choice == "1":
        print("CyberSuraksha helps people understand cyber law and what to do after online fraud.")
    elif choice == "2":
        print("1. What should I do if money is stolen through a fake link?")
        print("2. Where can I report online harassment?")
        print("3. Which law covers hacking?")
    elif choice == "3":
        hours = int(input("Hours since the fraud happened: "))
        if hours <= 24:
            print("Call 1930 and report on cybercrime.gov.in immediately.")
        elif hours <= 72:
            print("Report on cybercrime.gov.in and inform your bank.")
        else:
            print("Report on cybercrime.gov.in and visit the nearest police station.")
    elif choice == "0":
        print("Goodbye!")
        break
    else:
        print("Invalid choice, try again.")