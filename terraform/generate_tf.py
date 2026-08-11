#!/usr/bin/env python3
"""
Script pour générer des fichiers Terraform à partir de deploy.yml
pour un déploiement sur Incus.

Usage:
    python3 generate_tf.py

Génère:
    - main.tf          : Ressources Incus (réseaux, conteneurs, volumes)
    - variables.tf     : Variables configurables
    - outputs.tf       : Sorties utiles (IPs, noms, etc.)
"""

import yaml
import os
from pathlib import Path


# --- LECTURE DU FICHIER YAML ---
def load_deploy_yaml(file_path: str) -> dict:
    """Charge et parse le fichier deploy.yml"""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)


# --- GÉNÉRATION DU FICHIER MAIN.TF ---
def generate_main_tf(data: dict, output_dir: str = ".") -> None:
    """Génère le fichier main.tf avec les ressources Incus"""
    
    tf_content = """# ============================================
# Fichier généré automatiquement depuis deploy.yml
# Provider: Incus (lxc/incus)
# ============================================

terraform {
  required_providers {
    incus = {
      source = "lxc/incus"
      version = "1.1.1"
    }
  }
}

# Configuration du provider Incus
provider "incus" {
  # Pour cibler un serveur distant, configurez les variables :
  # address = var.incus_address
  # username = var.incus_username
  # password = var.incus_password
  # project  = var.incus_project
}

"""

    # --- Génération des réseaux ---
    # Les réseaux sont sous project.networks dans le nouveau format
    project_data = data.get("project", {})
    networks = project_data.get("networks", [])
    if networks:
        tf_content += "# ============================================\n# Réseaux Incus\n# ============================================\n\n"
        for net in networks:
            net_name = net["name"]
            net_type = net.get("type", "bridge")
            net_config = net.get("config", {})
            net_managed = net.get("managed", False)
            
            # Pour les réseaux de type 'bridge', on les crée dans Terraform
            if net_type == "bridge":
                tf_content += f'# --- Réseau: {net_name} ---\n'
                tf_content += f'resource "incus_network" "{net_name}" {{\n'
                tf_content += f'  name = "{net_name}"\n'
                tf_content += f'  type = "{net_type}"\n'
                
                # Ajouter la configuration
                if net_config:
                    tf_content += '  config = {\n'
                    for key, value in net_config.items():
                        # Corriger la typo 'addess' -> 'address'
                        corrected_key = key.replace("addess", "address")
                        tf_content += f'    "{corrected_key}" = "{value}"\n'
                    tf_content += '  }\n'
                
                if net_managed:
                    tf_content += '  managed = true\n'
                
                tf_content += '}\n\n'
            # Pour les réseaux physiques, on ne les crée pas (gérés par l'hôte)
            elif net_type == "physique":
                tf_content += f'# --- Réseau physique: {net_name} ---\n'
                tf_content += f'# Géré par l\'hôte, pas de ressource Terraform nécessaire\n'
                tf_content += f'# Parent: {net_config.get("parent", "N/A")}\n\n'

    # --- Génération des conteneurs (servers) ---
    # Les serveurs sont sous project.servers dans le nouveau format
    servers = project_data.get("servers", [])
    if servers:
        tf_content += "# ============================================\n# Conteneurs Incus\n# ============================================\n\n"
        
        for server in servers:
            name = server["name"]
            server_type = server.get("type", "lxc")
            image = server.get("image", "")
            fqdn = server.get("fqdn", "")
            cpu_limit = server.get("limits", {}).get("cpu", 1)
            memory_limit = server.get("limits", {}).get("memory", "1G")
            
            # Déterminer le type de conteneur pour Incus
            incus_type = "oci" if server_type == "oci" else "container"
            
            tf_content += f'# --- Conteneur: {name} ---\n'
            tf_content += f'resource "incus_instance" "{name}" {{\n'
            tf_content += f'  name  = "{name}"\n'
            tf_content += f'  type  = "{incus_type}"\n'
            tf_content += f'  image = "{image}"\n\n'

            # Configuration de base + limites (dans config pour Incus)
            tf_content += '  # Configuration et limites de ressources\n'
            tf_content += '  config = {\n'
            tf_content += '    "boot.autostart" = true\n'
            
            # Ajouter les limites CPU et mémoire dans config
            tf_content += f'    "limits.cpu" = "{cpu_limit}"\n'
            tf_content += f'    "limits.memory" = "{memory_limit}"\n'
            
            # Ajouter le FQDN si présent
            if fqdn:
                tf_content += f'    "user.network-hostname" = "{fqdn}"\n'
            
            tf_content += '  }\n\n'

            # --- Gestion des volumes ---
            volumes = server.get("volumes", [])
            if volumes:
                tf_content += '  # Volumes (stockage persistant)\n'
                for vol in volumes:
                    vol_name = vol["name"]
                    vol_size = vol.get("size", "1G")
                    vol_type = vol.get("type", "disk")
                    vol_pool = vol.get("pool", "local")
                    vol_mount = vol.get("mount", "")
                    
                    # Pour les volumes root
                    if vol_type == "root":
                        tf_content += f'  # Volume root (système)\n'
                        tf_content += '  device {\n'
                        tf_content += f'    name = "root"\n'
                        tf_content += '    type = "disk"\n'
                        tf_content += '    properties = {\n'
                        tf_content += f'      pool = "{vol_pool}"\n'
                        tf_content += f'      size = "{vol_size}"\n'
                        tf_content += '    }\n'
                        tf_content += '  }\n\n'
                    
                    # Pour les volumes de données (files)
                    elif vol_type == "files" and vol_mount:
                        parts = vol_mount.split(":")
                        if len(parts) == 2:
                            source_path, dest_path = parts
                            tf_content += f'  # Volume {vol_name} (montage depuis {vol_pool}/{source_path})\n'
                            tf_content += '  device {\n'
                            tf_content += f'    name = "{vol_name}"\n'
                            tf_content += '    type = "disk"\n'
                            tf_content += '    properties = {\n'
                            tf_content += f'      pool = "{vol_pool}"\n'
                            tf_content += f'      source = "{source_path}"\n'
                            tf_content += f'      path = "{dest_path}"\n'
                            tf_content += '    }\n'
                            tf_content += '  }\n\n'

            # --- Gestion des services (ports exposés) ---
            services = server.get("services", [])
            if services:
                tf_content += '  # Services (mappage de ports)\n'
                for svc in services:
                    svc_name = svc["name"]
                    svc_type = svc.get("type", "port")
                    svc_map = svc.get("map", "")
                    
                    # Nettoyer le mapping (supprimer /tcp ou /udp si présent)
                    # Convertir en str au cas où YAML l'a interprété comme un int
                    clean_map = str(svc_map).replace("/tcp", "").replace("/udp", "")
                    parts = clean_map.split(":")
                    if len(parts) == 2:
                        host_port, container_port = parts
                        
                        # Type de device : proxy pour les ports, nic pour les réseaux
                        device_type = "proxy" if svc_type in ["port", "proxy", "lxc"] else "nic"
                        
                        tf_content += f'  # Mappage du port {svc_name}: {host_port} -> {container_port}\n'
                        tf_content += '  device {\n'
                        tf_content += f'    name = "{svc_name}"\n'
                        tf_content += f'    type = "{device_type}"\n'
                        tf_content += '    properties = {\n'
                        if device_type == "proxy":
                            tf_content += f'      listen = "0.0.0.0:{host_port}"\n'
                            tf_content += f'      connect = "127.0.0.1:{container_port}"\n'
                            tf_content += '      type = "tcp"\n'
                        else:
                            tf_content += f'      # Configuration réseau pour {svc_name}\n'
                        
                        tf_content += '    }\n'
                        tf_content += '  }\n\n'

            tf_content += '}\n\n'

    # Écrire le fichier
    main_tf_path = Path(output_dir) / "main.tf"
    with open(main_tf_path, 'w') as f:
        f.write(tf_content)
    
    print(f"✅ Fichier généré: {main_tf_path}")


# --- GÉNÉRATION DU FICHIER VARIABLES.TF ---
def generate_variables_tf(output_dir: str = ".") -> None:
    """Génère le fichier variables.tf"""
    
    variables_content = """# ============================================
# Variables configurables pour le déploiement Incus
# ============================================

# --- Configuration du serveur Incus ---
variable "incus_address" {
  description = "Adresse du serveur Incus (ex: https://192.168.1.100:8443)"
  type        = string
  default     = "unix://"
}

variable "incus_username" {
  description = "Nom d'utilisateur pour se connecter au serveur Incus"
  type        = string
  default     = ""
}

variable "incus_password" {
  description = "Mot de passe pour se connecter au serveur Incus"
  type        = string
  default     = ""
  sensitive   = true
}

variable "incus_project" {
  description = "Nom du projet Incus où déployer les conteneurs"
  type        = string
  default     = "default"
}

# --- Configuration du stockage ---
variable "storage_pool" {
  description = "Pool de stockage par défaut à utiliser pour les volumes"
  type        = string
  default     = "local"
}

"""
    
    variables_path = Path(output_dir) / "variables.tf"
    with open(variables_path, 'w') as f:
        f.write(variables_content)
    
    print(f"✅ Fichier généré: {variables_path}")


# --- GÉNÉRATION DU FICHIER OUTPUTS.TF ---
def generate_outputs_tf(data: dict, output_dir: str = ".") -> None:
    """Génère le fichier outputs.tf"""
    
    project_data = data.get("project", {})
    servers = project_data.get("servers", [])
    
    outputs_content = """# ============================================
# Sorties utiles après déploiement
# ============================================

"""

    for server in servers:
        name = server["name"]
        outputs_content += f"""# Informations sur le conteneur {name}
output "{name}_instance_name" {{
  description = "Nom de l'instance Incus pour {name}"
  value       = incus_instance.{name}.name
}}

output "{name}_instance_status" {{
  description = "Statut de l'instance {name}"
  value       = incus_instance.{name}.status
}}

output "{name}_instance_ipv4" {{
  description = "Adresse IPv4 de l'instance {name}"
  value       = incus_instance.{name}.ipv4_address
}}

output "{name}_instance_ipv6" {{
  description = "Adresse IPv6 de l'instance {name}"
  value       = incus_instance.{name}.ipv6_address
}}

"""

    outputs_path = Path(output_dir) / "outputs.tf"
    with open(outputs_path, 'w') as f:
        f.write(outputs_content)
    
    print(f"✅ Fichier généré: {outputs_path}")


# --- FONCTION PRINCIPALE ---
def main():
    """Point d'entrée du script"""
    
    # Chemins
    deploy_yml_path = Path(__file__).parent.parent / "deploy.yml"
    output_dir = Path(__file__).parent
    
    # Vérifier que deploy.yml existe
    if not deploy_yml_path.exists():
        print(f"❌ Erreur: Le fichier {deploy_yml_path} n'existe pas !")
        print("   Assurez-vous qu'il est dans le répertoire parent de terraform/")
        return
    
    # Charger les données
    print("📖 Lecture du fichier deploy.yml...")
    data = load_deploy_yaml(deploy_yml_path)
    
    # Vérifier la structure
    project_data = data.get("project", {})
    print(f"   - Projet: {project_data.get('name', 'N/A')}")
    print(f"   - Serveurs: {len(project_data.get('servers', []))}")
    print(f"   - Réseaux: {len(project_data.get('networks', []))}")
    print(f"   - Stockages: {len(project_data.get('storages', []))}")
    
    # Générer les fichiers Terraform
    print("\n🔧 Génération des fichiers Terraform...")
    generate_main_tf(data, output_dir)
    generate_variables_tf(output_dir)
    generate_outputs_tf(data, output_dir)
    
    print("\n" + "="*50)
    print("✅ Tous les fichiers Terraform ont été générés !")
    print("="*50)
    print("\nPour déployer :")
    print("  1. cd terraform/")
    print("  2. terraform init")
    print("  3. terraform plan")
    print("  4. terraform apply")
    print("\nPour cibler un serveur Incus distant, utilisez les variables :")
    print("  export TF_VAR_incus_address='https://<IP>:8443'")
    print("  export TF_VAR_incus_username='admin'")
    print("  export TF_VAR_incus_password='votre_mot_de_passe'")
    print("  export TF_VAR_incus_project='bastion'")


if __name__ == "__main__":
    main()
