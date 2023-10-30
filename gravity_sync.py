import os.path
import sqlite3
import argparse
import json
import subprocess


def configure_parser():
    # Configure parser
    parser = argparse.ArgumentParser(
        prog="PiHole Gravity Syncer",
        description="Export/Import database Adlist, Whitelist and Blocklist"
    )
    parser.add_argument('-d','--database', default="etc-pihole/gravity.db")
    parser.add_argument('-f','--file', default="gravity_changes.json")
    parser.add_argument('-a','--action', required=True, help="import/export", choices=["import","export"])
    args = parser.parse_args()
    return args


def query_to_dict(cursor,query):
    cursor.execute(query)
    return cursor_to_dict(cursor)

def cursor_to_dict(cursor):
    desc = cursor.description
    column_names = [col[0] for col in desc]
    data = [dict(zip(column_names, row))
            for row in cursor]
    return data



#####################################################################
## IMPORT FUNCTIONS
#####################################################################
def load_changes_file(file):
    f = open(file)
    return json.load(f)

def apply_adlist(cursor,adlist):
    # Extraemos las listas que si queremos guardar
    where = "','".join([ x["address"] for x in adlist ])

    # Borramos las existentes que no estan en dicha lista
    query = f"DELETE FROM gravity WHERE adlist_id NOT IN (SELECT id FROM adlist WHERE address IN ('{where}'))"
    cursor.execute(query)
    gravity_deletes = cursor.rowcount
    query = f"DELETE FROM adlist_by_group WHERE adlist_id NOT IN (SELECT id FROM adlist WHERE address IN ('{where}'))"
    cursor.execute(query)
    query = f"DELETE FROM adlist WHERE address NOT IN ('{where}')"
    cursor.execute(query)

    print(f"\tDeleted {str(cursor.rowcount)} adlist from table")
    if cursor.rowcount > 0:
        print(f"\t\tDeleted {str(gravity_deletes)} gravity blocks")

    # Creamos si no existen, updateamos si ya existen
    for item in adlist:
        query = "SELECT id FROM adlist WHERE address=?"
        cursor.execute(query, (item['address'],))
        data = cursor.fetchone()
        #print(f"Checking if adlist {item['address']} is already in database")
        if data is None:
            # Creamos el registro
            query = "INSERT INTO adlist (address,enabled,comment) VALUES (?,?,?)"
            cursor.execute(query,(item["address"],item["enabled"],item["comment"]))
            print(f"\tAdding {item['address']}")
            apply_gravity_upgrade_after_changes = True
        else:
            # Actualizamos el registro
            query = "UPDATE adlist SET enabled=?, comment=? WHERE address=?"
            cursor.execute(query, (item["enabled"],item["comment"],item["address"]))
            print(f"\tUpdating fields enabled & comment for {item['address']}")

def apply_domainlist(cursor,domainlist):
    # Extraemos las listas que si queremos guardar
    where = "','".join([ x["domain"] for x in domainlist ])
    # print(where)

    query = f"DELETE FROM domainlist_by_group WHERE domainlist_id NOT IN (SELECT id FROM domainlist WHERE domain IN ('{where}'))"
    cursor.execute(query)
    query = f"DELETE FROM domainlist WHERE domain NOT IN ('{where}')"
    cursor.execute(query)

    print(f"\tDeleted {cursor.rowcount} domainlist" )
    for item in domainlist:
        query = "SELECT id FROM domainlist WHERE domain=?"
        cursor.execute(query, (item['domain'],))
        data = cursor.fetchone()
        # print(f"Checking if domain {item['domain']} is already in database")
        if data is None:
            # Creamos el registro
            query = "INSERT INTO domainlist (domain,enabled,type,date_added,comment) VALUES (?,?,?,?,?)"
            cursor.execute(query,(item["domain"],item["enabled"],item["type"],item["date_added"],item["comment"]))
            print(f"\tAdding {item['domain']}")
        else:
            # Actualizamos el registro
            query = "UPDATE domainlist SET enabled=?, type=?, date_added=?, comment=? WHERE domain=?"
            cursor.execute(query,(item["enabled"],item["type"],item["date_added"],item["comment"],item["domain"]))
            print(f"\tUpdating  {item['domain']}")


def apply_changes(cursor, data):
    print(f"\n##############################\n# ADLIST\n##############################")
    apply_adlist(cursor,data["adlist"])
    print(f"\n##############################\n# ALLOW & BLOCK LIST\n##############################")
    apply_domainlist(cursor,data["domainlist"])

def main_import(arguments):
    data = load_changes_file(arguments.file)
    dbcon = sqlite3.connect(arguments.database)
    cursor = dbcon.cursor()
    apply_changes(cursor, data)
    cursor.close()
    dbcon.commit()
    dbcon.close()

#####################################################################
## EXPORT FUNCTIONS
#####################################################################
def get_adlist(dbconnection):
    cursor = dbconnection.cursor()
    data = query_to_dict(cursor, "SELECT address, enabled, comment FROM adlist")
    cursor.close()
    return data

def get_allowblocklist(dbconnection):
    # Get rows of domainlist table
    cursor = dbconnection.cursor()
    data = query_to_dict( cursor, "SELECT domain, enabled, type, comment, date_added FROM domainlist")
    cursor.close()
    return data


def main_export(arguments):
    dbcon = sqlite3.connect(args.database)
    adlist = get_adlist(dbcon)
    domainlist = get_allowblocklist(dbcon)

    data = {
        "adlist":adlist,
        "domainlist":domainlist,
    }
    with open(arguments.file,"w") as of:
        json.dump(data,of)

    # Cerramos conexion
    dbcon.close()
    print(f"Export adlist, whitelist & blocklist to {arguments.file} file")



#####################################################################
## MAIN
#####################################################################
if __name__ == '__main__':
    apply_gravity_upgrade_after_changes = False
    args = configure_parser()

    if not os.path.isfile(args.database):
        print(f'El fichero {args.database} no existe o no es un fichero')
        exit(-1)

    if args.action == "export":
        main_export(args)
    else:
        if not os.path.isfile(args.file):
            print(f"The file {args.file} does not exist (or not readable)")
            exit(-1)

        main_import(args)
