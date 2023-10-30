# pihole-sync
A gitops way to sync two or many PiHoles without having connection between them.

[![](https://docs.driverlandia.com/uploads/images/gallery/2023-10/scaled-1680-/YzZcEwjAOPOvwIHo-image-1697823619387.png)](https://docs.driverlandia.com/uploads/images/gallery/2023-10/YzZcEwjAOPOvwIHo-image-1697823619387.png)

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

## Parameters

|Name|Values|Default|Description|
|-|-|-|-|
|-d||`etc-pihole/gravity.db`|Path and name of gravity database|
|-f||`gravity_changes.json`|Path of file where write/read export/import changes|
|-a|`import`<br>`export`|You need to specify|Action you want to perform|
