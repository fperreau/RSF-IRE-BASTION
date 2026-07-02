# BASTION - Containers on IncusOS

## Bastion -  The-Bastion app.Container

## Ansible JumpHost - OpenSSH sys.Container

## Depot packages - Nginx app.Container

## Depot images - Registry appContainer

____

### IncusOS usb image for Hyper-V

### Rappel rhel.repo

```bash
#
# Repository ISO RHEL9
#
[rhel9-baseos]
name=RHEL 9 BaseOS
baseurl=file:///mnt/iso/BaseOS/
enabled=1
gpgcheck=0

[rhel9-appstream]
name=RHEL 9 AppStream
baseurl=file:///mnt/iso/AppStream/
enabled=1
gpgcheck=0

#
# Mount ISO && upgrade
#
sudo mkdir -p /mnt/iso
sudo mount /dev/sr0 /mnt/iso -t iso9660
sudo yum update && sudo yum -y upgrade

#
# Install EPEL
#
sudo yum install https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm
sudo yum update
sudo yum install nmap byobu 

#
# Install NET-SNMP
#
https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpms
sudo yum install -y net-snmp net-snmp-utils

```
