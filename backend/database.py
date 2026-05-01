import oracledb
import os

# Ensure Oracle uses UTF-8
os.environ["NLS_LANG"] = ".AL32UTF8"

# Create database connection
connection = oracledb.connect(
    user="hospital",
    password="hospital123",
    dsn="localhost/XEPDB1"
)

# Function to return a new cursor
def get_cursor():
    try:
        connection.ping()  # check if connection is alive
    except:
        reconnect()

    return connection.cursor()


# Function to reconnect if connection drops
def reconnect():
    global connection
    connection = oracledb.connect(
        user="hospital",
        password="hospital123",
        dsn="localhost/XEPDB1"
    )