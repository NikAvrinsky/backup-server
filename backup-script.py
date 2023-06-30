#!/bin/python3
######################################################################################
# This script synchronises backups from remote servers to the local storage via rsync.
# Created by Nikita Avrinsky 2023
######################################################################################

import subprocess
import datetime
import time
import os
import yaml
import art
import requests

DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK')
SSH_USER = os.getenv('SSH_USER')
INVENTORY_FILE = os.getenv('INVENTORY_FILE')
LOCAL_BACKUP_FOLDER = os.getenv('LOCAL_BACKUP_FOLDER')
BACKUP_START_HOUR_UTC = os.getenv('BACKUP_START_HOUR_UTC')
BASIC_RETENTION = os.getenv('BASIC_RETENTION')


def yaml_parser(file=INVENTORY_FILE):
    """ Parses inventory file """
    with open(file, "r") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as err:
            print(err)


def rsync_host(host, folder, target_folder, port):
    """ Synchronizes host remote folders to local """
    command = f"rsync -av -e 'ssh -p {port} -o StrictHostKeyChecking=no -i ./id_rsa' {SSH_USER}@{host}:{folder} {target_folder}/"
    try:
        rsync_run = subprocess.run(command, shell=True, stderr=subprocess.PIPE)
        error = rsync_run.stderr.decode()
        if error:
            print(f"ERROR: {error}")
            discord_notify(host, folder, error)
        else:
            print("================ Done ================\n")
    except Exception as e:
        print("Something went wrong...")
        print(f"ERROR: {str(e.args)}")


def rotation(folder, prefix):
    """ Deletes old files due to retention settings """
    retention = BASIC_RETENTION
    today = datetime.datetime.today()
    if prefix:
        files = [f for f in os.listdir(folder) if prefix in f]
        print(f"Files with prefix '{prefix}': {len(files)}. min qtty: 7")
        if len(files) > 7:
            for file in files:
                file_mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(f'{folder}/{file}'))
                age = today - file_mod_time
                if age.days > 7:
                    os.remove(f'{folder}/{file}')
                    print(f"File: {file} has been deleted")
        else:
            print(f"Nothing to delete for prefix '{prefix}'")
    else:
        for prefix in retention:
            files = [f for f in os.listdir(folder) if prefix in f]
            print(f"Files with prefix '{prefix}': {len(files)}. min qtty: {retention[prefix]['qtty']}")
            if len(files) > retention[prefix]["qtty"]:
                for file in files:
                    file_mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(f'{folder}/{file}'))
                    age = today - file_mod_time
                    if age.days > retention[prefix]["age"]:
                        os.remove(f'{folder}/{file}')
                        print(f"File: {file} has been deleted")
            else:
                print(f"Nothing to delete for prefix '{prefix}'")


def sync_folders(inventory):
    """ Iterates by host list and runs rsync """
    for host in inventory:
        try:
            ssh_port = inventory[host]["ssh-port"]
        except KeyError as err:
            ssh_port = 22
        try:
            prefix = inventory[host]["prefix"]
        except KeyError as err:
            prefix = ''
        host_dir = f"{LOCAL_BACKUP_FOLDER}/{inventory[host]['url']}"
        if not os.path.exists(host_dir):
            os.makedirs(host_dir)
        for folder in inventory[host]["folders"]:
            bkup_dir = f"{host_dir}/{folder}"
            if not os.path.exists(bkup_dir):
                os.makedirs(bkup_dir)
            print(f"Backup rotation processing for host: {inventory[host]['url']}, folder: {folder}  ...")
            rotation(bkup_dir, prefix)
            print(f'Synchronizing backups for host: {inventory[host]["url"]} ...')
            rsync_host(inventory[host]["url"], inventory[host]["folders"][folder], bkup_dir, ssh_port)


def discord_notify(host, folder, error):
    """ Send error notification to discord """
    url = DISCORD_WEBHOOK
    data = {"content": f"Backup failed for host: {host}",
            "username": "Backup Server",
            "embeds": [
                {
                    "color": "15158332",
                    "description": f"ERROR: {error}",
                    "title": f"Backup failed for host: {host} \nTarget folder: {folder}"
                }
            ]}

    result = requests.post(url, json=data)
    try:
        result.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(err)
    else:
        print("Payload delivered successfully, code {}.".format(result.status_code))


def main():
    art.tprint("ELEMENT", space=10)
    art.tprint("BACKUP SERVER", font="small", space=3)
    inventory = yaml_parser()
    print("Found inventory file.")
    print(f"Hosts to backup: {len(inventory)}")
    for host in inventory:
        print(f"- {inventory[host]['url']}")
    print("Backup script has been started.")
    while True:
        time_now = datetime.datetime.now()
        hour = time_now.hour
        if hour == BACKUP_START_HOUR_UTC:
            print("Starting backup process...")
            sync_folders(inventory)
            time.sleep(3600)
        time.sleep(60)


if __name__ == '__main__':
    main()
