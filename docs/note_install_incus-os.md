# LinuxContainers

https://linuxcontainers.org/incus-os/docs/main/getting-started/installation/virtual-hyperv/

## Get USB Incus-OS for Hyperv

https://linuxcontainers.org/incus-os/docs/main/getting-started/download/

1. Get Client Certificate

   ```bash
   incus remote get-client-certificate
   -----BEGIN CERTIFICATE-----
   MIIB3DCCAWOgAwIBAgIRAPUh9Xe/V6BLnLXtWxEhWjQwCgYIKoZIzj0EAwMwNjEZ
   MBcGA1UEChMQTGludXggQ29udGFpbmVyczEZMBcGA1UEAwwQcGVycmVhdUBhdXRv
   bWF0YTAeFw0yNjAxMjgxNzMzMjJaFw0zNjAxMjYxNzMzMjJaMDYxGTAXBgNVBAoT
   EExpbnV4IENvbnRhaW5lcnMxGTAXBgNVBAMMEHBlcnJlYXVAYXV0b21hdGEwdjAQ
   BgcqhkjOPQIBBgUrgQQAIgNiAAS0PH3AV85cAH65gMKKYTmifeJucyCfACWbknu7
   C9kJeTYOGeulk9qaRtbg6jlI+Lr6kkAaJymTDAf+HAjI9AA8nMKL4yWGXes4+WxF
   31/IIB0w0BHWf4JEkVD6IE9PWS6jNTAzMA4GA1UdDwEB/wQEAwIFoDATBgNVHSUE
   DDAKBggrBgEFBQcDAjAMBgNVHRMBAf8EAjAAMAoGCCqGSM49BAMDA2cAMGQCMDOy
   uDJNUU7rNcY61Ner7NVuINqtSChUAKZV0uWGIzRCypiEbhtZTJla8S515JJXywIw
   d1toZVOLYs9W5iU3fvDTAWDhvlrUJjQfzxwUg+/KTVHiFO8PB9qTwjZW8YHiPKry
   -----END CERTIFICATE-----
   ```

2. Degraded boot security (no Secure Boot)

   ![Hyper-V VM configuring advanced install options](img/hyperv-vm-download-advanced.png)
3. Download USB image
4. Convert USB image

   ```bash
   qemu-img convert IncusOS_202607011621.img -O vhdx -o subformat=dynamic IncusOS_202607011621.vhdx
   ```


## Create Incus-OS Hyper-V VM

Create a new virtual machine and when asked to make an installation option, select “Install an operating system later”.

![Hyper-V VM configuring virtual machine](img/hyperv-vm-configure-vm.png)

Once the virtual machine is created, open its settings and add the `.vhdx` image as a second virtual hard disk.

![Hyper-V VM configuring install disk](img/hyperv-vm-configure-install-disk.png)

#### Secure Boot and TPM configuration

Incus-OS depends on a v2.0 TPM; as mentioned above we must disable  Secure Boot when running in a Hyper-V virtual machine. When configuring  the virtual machine, make the following selections under “Security”:

- Uncheck “Enable Secure Boot”
- Check “Enable Trusted Platform Module”

![Hyper-V VM configuring Secure Boot and TPM](img/hyperv-vm-configure-secure-boot-tpm.png)

#### CPU, memory, network, and local storage

Configure the CPU and memory for the virtual machine as desired and add at least one network interface. Remember that the main system drive must be at least 50GiB or larger.

## Incus-OS installation

Start the virtual machine; when Incus-OS starts you will see a boot warning about Secure Boot being disabled.

![Hyper-V VM boot warning](img/hyperv-vm-boot-warning.png)

Before the install commences, a warning message will be displayed for 30 seconds.

![Hyper-V VM install warning](img/hyperv-vm-install-warning.png)

Finally, Incus-OS will begin its installation.

![Hyper-V VM installing IncusOS](img/hyperv-vm-install.png)

Finally, IncusOS will begin its installation.

![Hyper-V VM installing IncusOS](img/hyperv-vm-install-1783002122792-13.png)

Upon completion of the install, stop the virtual machine and remove the second hard disk.

![Hyper-V VM installation complete](img/hyperv-vm-install-complete.png)

## Incus-OS is ready for use

Start the virtual machine, and IncusOS will perform its first boot configuration. Once complete, follow the instructions for [accessing the system](https://linuxcontainers.org/incus-os/docs/main/getting-started/access/).

Because Secure Boot is disabled, a prominent header will display a warning about the degraded security state of the system.

![Hyper-V VM running IncusOS](img/hyperv-vm-incusos-running.png)



