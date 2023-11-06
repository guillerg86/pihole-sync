# pihole-sync
A gitops way to sync two or many PiHoles without having connection between them.

[![](https://docs.driverlandia.com/uploads/images/gallery/2023-10/scaled-1680-/YzZcEwjAOPOvwIHo-image-1697823619387.png)](https://docs.driverlandia.com/uploads/images/gallery/2023-10/YzZcEwjAOPOvwIHo-image-1697823619387.png)

## What is synchronized?

This script synchronizes the following data

- Configuration (web password, dns upstream)
- Local DNS 
  - DNS Records
  - CName Records
- Groups
- Clients 
- Adlist
- Domains List (Allow list & Block list)


**Does not sync:**

- DHCP


## How to install

Follow steps: https://docs.driverlandia.com/books/pihole/page/sincronizacion-de-varios-pihole

## Command for export data from "master" PiHole

Inside pihole folder (same level that etc-pihole, etc-dnsmasq.d, var-log-pihole) execute this Command


```
python3 gravity_sync.py -a export
```

This command will generate the `gravity_changes.json` (see the example file). You can specify the name of this file.
Commit this file to git repository (git commit & push), make a pull on the second or third (or N PiHole) and then execute

```
python3 gravity_sync.py -a import
```

Execution result of git pull & import command on second PiHole

[![](https://docs.driverlandia.com/uploads/images/gallery/2023-10/scaled-1680-/xZyFuURATx1sQGcK-image-1698661376076.png)](https://docs.driverlandia.com/uploads/images/gallery/2023-10/xZyFuURATx1sQGcK-image-1698661376076.png)

## Parameters

|Arg|Long Argument|Values|Default|Description|
|-|-|-|-|-|
|`-d`|`--database`||`etc-pihole/gravity.db`|Path and name of gravity database|
|`-f`|`--file`||`gravity_changes.json`|Path of file where write/read export/import changes|
|`-a`|`--action`|`import`<br>`export`|You need to specify|Action you want to perform|
|`-ug`|`--upgrade-gravity`|`y`</br>`n`|`n`|Execute force upgrade IOC after adding adlist|
|`-cn`|`--container-name`||`pihole`|Container name of pihole|


## Automatization


For export changes from master to git, you can add this line to cron 

```
*/15 * * * * cd /docker/pihole/ && python3 gravity_sync.py -a export && git add -A && git commit -m "Autoupdate" && git push 
```

For import to secondary PiHoles add this line in cron. Command restartdns reload is for reload DNS if file of local DNS has been updated

```
*/15 * * * * cd /docker/pihole/ && git pull && docker exec pihole pihole restartdns reload && python3 gravity_sync.py -a import
```

Import and if there's a new adlist added, then force gravity update. Be careful, if you check many times at day some list they will ban you for a few days.

```
*/15 * * * * cd /docker/pihole/ && git pull && docker exec pihole pihole restartdns reload && python3 gravity_sync.py -a import -ug y
```


# Password for PiHole 

If you use this setupvars.conf the password of PiHole web is `admin`. 
**Please change this password!! DON'T USE IN PRODUCTION!**


# Misc

If this project has been useful to you, you can give me a coffee at [Paypal](https://paypal.me/guillerg86?country.x=ES&locale.x=es_ES)


