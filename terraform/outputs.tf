# ============================================
# Sorties utiles après déploiement
# ============================================

# Informations sur le conteneur the-bastion
output "the-bastion_instance_name" {
  description = "Nom de l'instance Incus pour the-bastion"
  value       = incus_instance.the-bastion.name
}

output "the-bastion_instance_status" {
  description = "Statut de l'instance the-bastion"
  value       = incus_instance.the-bastion.status
}

output "the-bastion_instance_ipv4" {
  description = "Adresse IPv4 de l'instance the-bastion"
  value       = incus_instance.the-bastion.ipv4_address
}

output "the-bastion_instance_ipv6" {
  description = "Adresse IPv6 de l'instance the-bastion"
  value       = incus_instance.the-bastion.ipv6_address
}

# Informations sur le conteneur the-vault
# output "the-vault_instance_name" {
#   description = "Nom de l'instance Incus pour the-vault"
#   value       = incus_instance.the-vault.name
# }

# output "the-vault_instance_status" {
#   description = "Statut de l'instance the-vault"
#   value       = incus_instance.the-vault.status
# }

# output "the-vault_instance_ipv4" {
#   description = "Adresse IPv4 de l'instance the-vault"
#   value       = incus_instance.the-vault.ipv4_address
# }

# output "the-vault_instance_ipv6" {
#   description = "Adresse IPv6 de l'instance the-vault"
#   value       = incus_instance.the-vault.ipv6_address
# }

# Informations sur le conteneur the-media
# output "the-media_instance_name" {
#   description = "Nom de l'instance Incus pour the-media"
#   value       = incus_instance.the-media.name
# }

# output "the-media_instance_status" {
#   description = "Statut de l'instance the-media"
#   value       = incus_instance.the-media.status
# }

# output "the-media_instance_ipv4" {
#   description = "Adresse IPv4 de l'instance the-media"
#   value       = incus_instance.the-media.ipv4_address
# }

# output "the-media_instance_ipv6" {
#   description = "Adresse IPv6 de l'instance the-media"
#   value       = incus_instance.the-media.ipv6_address
# }

