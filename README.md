# BASTION - Containers on IncusOS

## Ansible project

### Project Structure

```code
ansible/
├── inventories/
│   └── lab/
│       ├── hosts.ini
│       └── group_vars/
│           └── all.yml
├── roles/
│   ├── common/
│   │   └── tasks/
│   │       └── main.yml
│   ├── hardening/
│   │   └── tasks/
│   │       └── main.yml
│   └── incus/
│       ├── tasks/
│       │   ├── main.yml
│       │   ├── containers.yml
│       │   ├── storage.yml
│       │   └── network.yml
│       └── handlers/
│           └── main.yml
├── playbooks/
│   ├── deploy_incus_bastion.yml
│   ├── update_incus_bastion.yml
│   ├── backup_incus_containers.yml
│   └── restore_incus_containers.yml
└── ansible.cfg
```

### Exécution des playbooks

```bash
# Déploiement initial
ansible-playbook -i inventories/production/hosts.ini playbooks/deploy_incus_bastion.yml

# Mise à jour des containers
ansible-playbook -i inventories/production/hosts.ini playbooks/deploy_incus_bastion.yml --tags "update"

# Sauvegarde des containers
ansible-playbook -i inventories/production/hosts.ini playbooks/backup_incus_containers.yml
```

## Create LAB



### Deploy IncusOS VM for Hyper-V

Voir: le document ==> 

[note incus-os]: docs/note_install_incus-os.md	"how to install IncusOS VM on Hyper-V"



## Notes

Les paragraphes ci-dessous sont des notes techniques prises lors de précédents projets ou tests qui facilitent la mise en oeuvre des systèmes d'exploitation, des middlewares et de applications.

### Note Repository 'rhel.repo' Red Hat Enterprise Linux

En l'absence de contrat de support Red Hat, il est cependant possible de créer son fichier 'redhat.repo' dans le répertoire '/etc/yum.repos.d/' pour utiliser les ISO que vous avez téléchargées précédemment.

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

Puis monter le fichier ISO sur le point de montage '/mnt/iso' et mettez à jour la liste des packages disponibles.

```bash
sudo mount /dev/sr0 /mnt/iso -o ro -t iso9660
sudo dnf update
ou 
sudo yum update
```

