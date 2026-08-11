resource "incus_instance" "hello" {
  name  = "hello"
  image = "images:ubuntu/26.04"

  config = {
    "boot.autostart" = false
    "limits.cpu"     = 1
  }
}
