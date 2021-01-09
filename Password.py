#!/usr/bin/env python3
import bcrypt
from getpass import getpass
salt = bcrypt.gensalt()

user_pw = str(raw_input("Enter password: "))

hashed = bcrypt.hashpw(user_pw, salt)

print (hashed)
