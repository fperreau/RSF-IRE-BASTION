# Ansible project over a Bastion or Jump Host

## Notes

### Use Ansible vault

```bash
# Creation d'un vault Ansible 
ansible-vault create secrets.yml

# Content example
ansible_password: "mon_mot_de_passe_super_secret"

# Playbook use
---
- name: Exemple avec Vault
  hosts: all_servers
  vars_files:
    - secrets.yml
  tasks:
    - name: Utiliser un secret
      debug:
        msg: "Le mot de passe est {{ ansible_password }}"
 
 # Use playbook
 ansible-playbook playbooks/example.yml --ask-vault-pass
 
```



### Prepare Ansible Bastion ou Jump Host

```bash
ansible-playbook playbooks/test.yml --callback yaml

sudo tail -f /var/log/auth.log  # Ubuntu/Debian
sudo tail -f /var/log/secure    # CentOS/RHEL

sudo ufw allow from <TON_IP_LOCALE> to any port 22
sudo ufw enable

sudo apt install fail2ban
sudo systemctl enable fail2ban


```

### AWS example

```code
[defaults]
inventory = inventory/hosts.ini
remote_user = ubuntu  # Utilisateur par défaut pour AWS
private_key_file = ~/.ssh/aws_bastion_key.pem

[ssh_connection]
ssh_args = -o ProxyCommand=ssh -W %h:%p -i ~/.ssh/aws_bastion_key.pem ubuntu@<IP_PUBLIQUE_BASTION>
```



### Commands and Tools


| Commande                                  | Description                                   |
| ----------------------------------------- | --------------------------------------------- |
| `ssh -J ansible-user@ ansible-user@`      | Connexion directe via le bastion (SSH 7.3+).  |
| `ansible all -m ping`                     | Teste la connectivité avec tous les serveurs. |
| `ansible-playbook playbooks/deploy.yml`   | Exécute un playbook.                          |
| `ansible-vault edit secrets.yml`          | Édite un fichier chiffré.                     |
| `ssh-copy-id -i ~/.ssh/key.pub user@host` | Copie une clé SSH sur un serveur.             |



| Outil          | Utilité                                                      |
| -------------- | ------------------------------------------------------------ |
| **`sshuttle`** | Crée un VPN SSH pour rediriger tout le trafic via le bastion. |
| **`mosh`**     | Alternative à SSH pour les connexions instables (ex: mobile). |
| **`tmux`**     | Permet de maintenir des sessions SSH persistantes sur le bastion. |
| **`awx`**      | Version open-source de Ansible Tower pour gérer les playbooks via une interface web. |



| Pratique                         | Description                                                  |
| -------------------------------- | ------------------------------------------------------------ |
| **Clés SSH dédiées**             | Utilise des clés différentes pour le bastion et les serveurs cibles. |
| **Rotation des clés**            | Change régulièrement les clés SSH et les mots de passe.      |
| **Principle of Least Privilege** | Donne à Ansible uniquement les droits nécessaires (évite `sudo` si possible). |
| **Sauvegardes**                  | Sauvegarde la configuration du bastion et des serveurs cibles. |
| **Monitoring**                   | Surveille les connexions SSH et les exécutions Ansible (ex: avec `auditd`). |
| **Mises à jour**                 | Maintiens le bastion et les serveurs cibles à jour (sécurité). |