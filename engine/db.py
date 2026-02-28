import csv
import sqlite3
con = sqlite3.connect("nora.db")

cursor = con.cursor()

# query = "CREATE TABLE IF NOT EXISTS sys_command(id integer primary key, name VARCHAR(100), path VARCHAR(1000))"
# cursor.execute(query)

# query = "INSERT INTO sys_command VALUES (null,'WhatsApp', 'C:\\Prograthem Files\\WindowsApps\\5319275A.WhatsAppDesktop_2.2605.103.0_x64__cv1g1gvanyjgm\\WhatsApp.Root.exe')"
# cursor.execute(query)
# con.commit()


# cursor.execute("DELETE FROM sys_command WHERE id IN (?, ?)", (3, 4))
# con.commit()


# query = "CREATE TABLE IF NOT EXISTS web_command(id integer primary key, name VARCHAR(100), url VARCHAR(1000))"
# cursor.execute(query)

# query = "INSERT INTO web_command VALUES (null,'gmail', 'https://mail.google.com/mail/u/0/#inbox')"
# cursor.execute(query)
# con.commit()


# # testing module
# app_name = "android studio"
# cursor.execute('SELECT path FROM sys_command WHERE name IN (?)', (app_name,))
# results = cursor.fetchall()
# print(results[0][0])

# # Create a table with the desired columns
# cursor.execute('''CREATE TABLE IF NOT EXISTS contacts (id integer primary key, name VARCHAR(200), mobile_no VARCHAR(255), email VARCHAR(255) NULL, address VARCHAR(255) NULL)''')





# # # Commit changes and close connection


# query = "INSERT INTO contacts VALUES (null,'ritik', '1234567890', 'null')"
# cursor.execute(query)
# con.commit()

# query = 'ritik'
# query = query.strip().lower()

# # cursor.execute("SELECT mobile_no FROM contacts WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ?", ('%' + query + '%', query + '%'))
# results = cursor.fetchall()
# print(results[0][0])

# Adding personal info table
# query = "CREATE TABLE IF NOT EXISTS info(name VARCHAR(100), designation VARCHAR(50),mobileno VARCHAR(40), email VARCHAR(200), city VARCHAR(300))"
# cursor.execute(query)


# # Specify the column indices you want to import (0-based index)
# # Example: Importing the 1st and 3rd columns
# desired_columns_indices = [0, 18]
# # Read data from CSV and insert into SQLite table for the desired columns
# with open('contacts.csv', 'r', encoding='utf-8') as csvfile:
#     csvreader = csv.reader(csvfile)
#     for row in csvreader:
#         selected_data = [row[i] for i in desired_columns_indices]
#         cursor.execute(''' INSERT INTO contacts (id, 'name', 'mobile_no') VALUES (null, ?, ?);''', tuple(selected_data))

# # Add Column in contacts table
# cursor.execute("ALTER TABLE contacts ADD COLUMN address VARCHAR(255)")


# cursor.execute("SELECT COUNT(*) FROM web_command WHERE name = 'gmail'")
# if cursor.fetchone()[0] == 0:
#     cursor.execute("INSERT INTO web_command VALUES (null, 'gmail', 'https://mail.google.com/mail/u/0/#inbox')")
#     con.commit()

# con.commit()
# con.close()


con.commit()
con.close()