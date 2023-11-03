import os.path
import sqlite3
import argparse
import json
import subprocess


class Changes(object):
    def __init__(self):
        self.adlist_added = False

def configure_parser():
    # Configure parser
    parser = argparse.ArgumentParser(
        prog="PiHole v5.x Gravity Syncer",
        description="Export/Import database Adlist, Whitelist and Blocklist"
    )
    parser.add_argument('-d','--database', default="etc-pihole/gravity.db")
    parser.add_argument('-f','--file', default="gravity_changes.json")
    parser.add_argument('-a','--action', required=True, help="import/export", choices=["import","export"])
    parser.add_argument('-ug','--upgrade-gravity', help="Execute force upgrade IOC after adding adlist", choices=["y","n"], default="n")
    parser.add_argument('-cn','--container-name', default="pihole")
    args = parser.parse_args()
    return args

def execute_gravity_update(printShell=False):

    cmd = f"docker exec {args.container_name} pihole updateGravity"
    try:
        print(f"\tExecuting {cmd}")
        result = subprocess.run(cmd, shell=printShell)
        if result.returncode == 0:
            print("\tExecution of gravityUpdate succes!")
    except:
        print(f"Problems executing command\n\t{cmd}")

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

def apply_clients(cursor,clients,groups_hash):
    # Extracting clients we want preserve
    where = "','".join([ x["ip"] for x in clients ])

    # Delete existent database clients that we dont want preserv (deleted on master)
    cursor.execute(f"DELETE FROM client WHERE ip NOT IN ('{where}')")
    print(f"\tDeleted {str(cursor.rowcount)} clients")

    # Creamos si no existen, updateamos si ya existen
    for item in clients:
        is_new = False
        query = "SELECT id FROM client WHERE ip=?"
        cursor.execute(query, (item['ip'],))
        data = cursor.fetchone()
        if data is None:
            # Creamos el registro
            query = "INSERT INTO client (ip, date_added,comment) VALUES (?,?,?)"
            cursor.execute(query, (item["ip"], item["date_added"], item["comment"]))
            print(f"\tAdded \"{item['ip']}\"")
            client_id = cursor.lastrowid
            apply_gravity_upgrade_after_changes = True
            is_new = True
        else:
            client_id = data[0]
            # Actualizamos el registro
            query = "UPDATE client SET date_added=?, comment=? WHERE ip=?"
            cursor.execute(query, (item["date_added"], item["comment"], item["ip"]))
            print(f"\tUpdated \"{item['ip']}\"")

        # Let's add / update groups
        for group in item["groups"]:
            cursor.execute("SELECT * FROM client_by_group WHERE client_id=? AND group_id=?",
                           (client_id, groups_hash[group]))
            row = cursor.fetchone()
            if row is None:
                cursor.execute("INSERT INTO client_by_group (client_id, group_id) VALUES (?,?)",
                               (client_id, groups_hash[group]))
                print(f"\t\t\tAdded adlist \"{item['ip']}\" to group \"{group}\"")

            # Let's delete unused groups for domain
            groups_id_not_delete = [str(groups_hash[group]) for group in item["groups"]]
            where = str(",".join(groups_id_not_delete))
            cursor.execute(f"DELETE FROM client_by_group WHERE client_id=? AND group_id NOT IN ({where})", (client_id,))
            if cursor.rowcount > 0 and not is_new:
                print(f"\t\t\tDeleted {cursor.rowcount} unused groups")

def apply_adlist(cursor,adlist,groups_hash,changes_applied):
    # Extracting adlist we want preserve
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
        is_new = False
        query = "SELECT id FROM adlist WHERE address=?"
        cursor.execute(query, (item['address'],))
        data = cursor.fetchone()
        #print(f"Checking if adlist {item['address']} is already in database")
        if data is None:
            # Creamos el registro
            query = "INSERT INTO adlist (address,enabled,comment) VALUES (?,?,?)"
            cursor.execute(query,(item["address"],item["enabled"],item["comment"]))
            print(f"\tAdded \"{item['address']}\"")
            adlist_id = cursor.lastrowid
            changes_applied.adlist_added = True
            is_new = True
        else:
            adlist_id = data[0]
            # Actualizamos el registro
            query = "UPDATE adlist SET enabled=?, comment=? WHERE address=?"
            cursor.execute(query, (item["enabled"],item["comment"],item["address"]))
            print(f"\tUpdated \"{item['address']}\"")

        # Let's add / update groups
        for group in item["groups"]:
            cursor.execute("SELECT * FROM adlist_by_group WHERE adlist_id=? AND group_id=?",
                           (adlist_id, groups_hash[group]))
            row = cursor.fetchone()
            if row is None:
                cursor.execute("INSERT INTO adlist_by_group (adlist_id, group_id) VALUES (?,?)",
                               (adlist_id, groups_hash[group]))
                print(f"\t\t\tAdded adlist \"{item['address']}\" to group \"{group}\"")

            # Let's delete unused groups for domain
            groups_id_not_delete = [str(groups_hash[group]) for group in item["groups"]]
            where = str(",".join(groups_id_not_delete))
            cursor.execute(f"DELETE FROM adlist_by_group WHERE adlist_id=? AND group_id NOT IN ({where})", (adlist_id,))
            if cursor.rowcount > 0 and not is_new:
                print(f"\t\t\tDeleted {cursor.rowcount} unused groups")

def apply_domainlist(cursor,domainlist,groups_hash):
    # Extraemos las listas que si queremos guardar
    where = "','".join([ x["domain"] for x in domainlist ])
    # print(where)

    query = f"DELETE FROM domainlist_by_group WHERE domainlist_id NOT IN (SELECT id FROM domainlist WHERE domain IN ('{where}'))"
    cursor.execute(query)
    query = f"DELETE FROM domainlist WHERE domain NOT IN ('{where}')"
    cursor.execute(query)

    print(f"\tDeleted {cursor.rowcount} domainlist" )
    for item in domainlist:
        is_new = False
        query = "SELECT id FROM domainlist WHERE domain=?"
        cursor.execute(query, (item['domain'],))
        data = cursor.fetchone()
        # print(f"Checking if domain {item['domain']} is already in database")
        if data is None:
            # Creamos el registro
            query = "INSERT INTO domainlist (domain,enabled,type,date_added,comment) VALUES (?,?,?,?,?)"
            cursor.execute(query,(item["domain"],item["enabled"],item["type"],item["date_added"],item["comment"]))
            print(f"\tAdded \"{item['domain']}\"")
            domainlist_id = cursor.lastrowid
            is_new = True
        else:
            domainlist_id = data[0]
            # Actualizamos el registro
            query = "UPDATE domainlist SET enabled=?, type=?, date_added=?, comment=? WHERE domain=?"
            cursor.execute(query,(item["enabled"],item["type"],item["date_added"],item["comment"],item["domain"]))
            print(f"\tUpdated \"{item['domain']}\"")


        # Let's add / update groups
        for group in item["groups"]:

            cursor.execute("SELECT * FROM domainlist_by_group WHERE domainlist_id=? AND group_id=?", (domainlist_id, groups_hash[group]))
            row = cursor.fetchone()
            if row is None:
                cursor.execute("INSERT INTO domainlist_by_group (domainlist_id, group_id) VALUES (?,?)",(domainlist_id, groups_hash[group]))
                print(f"\t\t\tAdded domainlist \"{item['domain']}\" to group \"{group}\"")

        # Let's delete unused groups for domain
        groups_id_not_delete = [str(groups_hash[group]) for group in item["groups"]]
        where = str(",".join(groups_id_not_delete))
        cursor.execute(f"DELETE FROM domainlist_by_group WHERE domainlist_id=? AND group_id NOT IN ({where})",(domainlist_id,))
        if cursor.rowcount > 0 and not is_new:
            print(f"\t\t\tDeleted {cursor.rowcount} unused groups ")

def apply_groups(cursor, data):
    """
    This function doesn't remove old groups, just create and update, because if we delete a group
    that has an existent adlist, client but this adlist, client has a new group, we got some errors (foreign keys)
    after update adlist and clients, we call function delete_unexistent_groups_in_file.
    :param cursor:
    :param data:
    :return:
    """


    # Hashmap using key as group name and database id as a value
    group_hash = {}

    # Now let's iterate over all groups and get IDs, if not exist -> set value None on dict
    for group in data["grouplist"]:
        cursor.execute("SELECT * FROM 'group' WHERE name=?", (group["name"],))
        row = cursor.fetchone()
        if row is None:
            cursor.execute(
                "INSERT INTO 'group' (enabled, description, date_added, name ) VALUES (?,?,?,?)",
                (group["enabled"],group["description"],group["date_added"],group["name"])
            )
            group_hash.update({group["name"]: cursor.lastrowid})
            print(f"\tAdded new group \"{group['name']}\" ")
        else:
            cursor.execute(
                "UPDATE 'group' SET enabled=?, description=?, date_added=? WHERE name=?",
                (group["enabled"],group["description"],group["date_added"],group["name"])
            )
            group_hash.update({group["name"]:row[0]})
            print(f"\tUpdated group \"{group['name']}\" ")
    return group_hash

def delete_unexistent_groups_in_file(cursor,data,groups_hash):
    """
    This function deletes all groups that not exists in JSON file.
    :param cursor:
    :param data:
    :param groups_hash:
    :return:
    """
    existent_groups_id = ','.join(map(str,list(groups_hash.values())))
    cursor.execute(f"DELETE FROM 'group' WHERE id NOT in ({existent_groups_id})")
    print(f"\tDeleted {cursor.rowcount} groups that not exist on JSON file ")

def apply_changes(cursor, data,changes_applied):
    """
    Calls groups, adlist, domainlist, clients update functions
    :param cursor:
    :param data:
    :return:
    """
    print("\n######################################\n# GROUPS\n######################################")
    groups_hash = apply_groups(cursor,data)
    print("\n######################################\n# ADLIST\n######################################")
    apply_adlist(cursor,data["adlist"],groups_hash,changes_applied)
    print("\n######################################\n# DOMAINLIST (ALLOW & BLOCK LIST) \n######################################")
    apply_domainlist(cursor,data["domainlist"],groups_hash)
    print("\n######################################\n# CLIENTS \n######################################")
    apply_clients(cursor,data["clientlist"],groups_hash)

    print("\n######################################\n# CLEANING STUFF \n######################################")
    delete_unexistent_groups_in_file(cursor,data,groups_hash)



def main_import(arguments,changes_applied):
    data = load_changes_file(arguments.file)
    dbcon = sqlite3.connect(arguments.database)
    cursor = dbcon.cursor()
    apply_changes(cursor, data,changes_applied)
    cursor.close()
    dbcon.commit()
    dbcon.close()

#####################################################################
## EXPORT FUNCTIONS
#####################################################################
def get_adlist(dbconnection):
    cursor = dbconnection.cursor()
    data = query_to_dict(cursor, "SELECT id, address, enabled, comment FROM adlist ")
    for adlist in data:
        cursor.execute("SELECT 'group'.name FROM 'group' INNER JOIN adlist_by_group ON 'group'.id=group_id AND adlist_id=?", (adlist["id"],))
        rows = cursor.fetchall()
        groups = [group[0] for group in rows]
        adlist.update({"groups":groups})
        adlist.pop("id")
    cursor.close()
    return data

def get_allowblocklist(dbconnection):
    # Get rows of domainlist table
    cursor = dbconnection.cursor()
    data = query_to_dict( cursor, "SELECT id, domain, enabled, type, comment, date_added FROM domainlist")
    for domainlist in data:
        cursor.execute("SELECT 'group'.name FROM 'group' INNER JOIN domainlist_by_group ON 'group'.id=group_id AND domainlist_id=?", (domainlist["id"],))
        rows = cursor.fetchall()
        groups = [group[0] for group in rows]
        domainlist.update({"groups":groups})
        domainlist.pop("id")


    cursor.close()
    return data


def get_grouplist(dbconnection):
    # Get rows of grouplist table
    cursor = dbconnection.cursor()
    data = query_to_dict( cursor, "SELECT name, enabled, date_added, description FROM 'group'")
    cursor.close()
    return data

def get_clientlist(dbconnection):
    # Get rows of clientlist table
    cursor = dbconnection.cursor()
    data = query_to_dict( cursor, "SELECT id, ip, date_added, comment FROM 'client'")
    for clientlist in data:
        cursor.execute("SELECT 'group'.name FROM 'group' INNER JOIN client_by_group ON 'group'.id=group_id AND client_id=?", (clientlist["id"],))
        rows = cursor.fetchall()
        groups = [group[0] for group in rows]
        clientlist.update({"groups":groups})
        clientlist.pop("id")
    cursor.close()
    return data


def main_export(arguments):
    dbcon = sqlite3.connect(args.database)
    adlist = get_adlist(dbcon)
    domainlist = get_allowblocklist(dbcon)
    grouplist = get_grouplist(dbcon)
    clientlist = get_clientlist(dbcon)

    data = {
        "adlist":adlist,
        "domainlist":domainlist,
        "grouplist": grouplist,
        "clientlist": clientlist,
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
    args = configure_parser()

    changes_applied = Changes()

    if not os.path.isfile(args.database):
        print(f'El fichero {args.database} no existe o no es un fichero')
        exit(-1)

    if args.action == "export":
        main_export(args)
    else:
        if not os.path.isfile(args.file):
            print(f"The file {args.file} does not exist (or not readable)")
            exit(-1)

        main_import(args, changes_applied)

    if args.action == "import" and args.upgrade_gravity == "y" and changes_applied.adlist_added:
        print("\n######################################\n# CLEANING STUFF \n######################################")
        execute_gravity_update(printShell=True)





