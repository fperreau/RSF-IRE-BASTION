# ============================================
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

