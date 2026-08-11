# ============================================
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

# ============================================
# Réseaux Incus
# ============================================

# --- Réseau physique: vmbr0 ---
# Géré par l'hôte, pas de ressource Terraform nécessaire
# Parent: enp101s1

# --- Réseau: incusbr0 ---
# resource "incus_network" "incusbr0" {
#  name = "incusbr0"
#  type = "bridge"
#  config = {
#    "ipv4.address" = "10.0.10.1/24"
#    "ipv4.nat" = "True"
#  }
# }

# ============================================
# Conteneurs Incus
# ============================================

# --- Conteneur: the-bastion ---
resource "incus_instance" "the-bastion" {
  name  = "the-bastion"
  type  = "container"
  image = "images:debian/13"

  # Configuration et limites de ressources
  config = {
    "boot.autostart" = true
    "limits.cpu" = "2"
    "limits.memory" = "4GB"
    "user.network-hostname" = "the-bastion.incus"
  }

  # Volumes (stockage persistant)
  # Volume root (système)
  device {
    name = "root"
    type = "disk"
    properties = {
      pool = "zvol1"
      size = "20GB"
    }
  }

  # Services (mappage de ports)
}

# # --- Conteneur: the-vault ---
# resource "incus_instance" "the-vault" {
#   name  = "the-vault"
#   type  = "container"
#   image = "docker.io/hashicorp/vault:latest"

#   # Configuration et limites de ressources
#   config = {
#     "boot.autostart" = true
#     "limits.cpu" = "1"
#     "limits.memory" = "4G"
#     "user.network-hostname" = "the-vault.incus"
#   }

#   # Volumes (stockage persistant)
#   # Volume vault-config (montage depuis zvol0/vault-config)
#   device {
#     name = "vault-config"
#     type = "disk"
#     properties = {
#       pool = "zvol0"
#       source = "vault-config"
#       path = "/vault/config.d"
#     }
#   }

#   # Volume vault-file (montage depuis zvol0/vault-file)
#   device {
#     name = "vault-file"
#     type = "disk"
#     properties = {
#       pool = "zvol0"
#       source = "vault-file"
#       path = "/vault/file"
#     }
#   }

#   # Volume vault-logs (montage depuis zvol0/vault-logs)
#   device {
#     name = "vault-logs"
#     type = "disk"
#     properties = {
#       pool = "zvol0"
#       source = "vault-logs"
#       path = "/vault/logs"
#     }
#   }

#   # Services (mappage de ports)
#   # Mappage du port vault-ssh: 8200 -> 8200
#   device {
#     name = "vault-ssh"
#     type = "proxy"
#     properties = {
#       listen = "0.0.0.0:8200"
#       connect = "127.0.0.1:8200"
#       type = "tcp"
#     }
#   }

# }

# --- Conteneur: the-media ---
# resource "incus_instance" "the-media" {
#   name  = "the-media"
#   type  = "container"
#   image = "images:alpine/latest"

#   # Configuration et limites de ressources
#   config = {
#     "boot.autostart" = true
#     "limits.cpu" = "1"
#     "limits.memory" = "4G"
#     "user.network-hostname" = "the-media.incus"
#   }

#   # Volumes (stockage persistant)
#   # Volume media-input (montage depuis zvol0/media-input)
#   device {
#     name = "media-input"
#     type = "disk"
#     properties = {
#       pool = "zvol0"
#       source = "media-input"
#       path = "/input"
#     }
#   }

#   # Volume media-output (montage depuis zvol0/media-output)
#   device {
#     name = "media-output"
#     type = "disk"
#     properties = {
#       pool = "zvol0"
#       source = "media-output"
#       path = "/output"
#     }
#   }

#   # Services (mappage de ports)
# }

