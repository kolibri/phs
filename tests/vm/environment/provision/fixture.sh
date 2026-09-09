#!/usr/bin/env bash

set -euo pipefail

die() {
    echo "ERROR: $*" >&2
    exit 1
}

if [[ $EUID -ne 0 ]]; then
    die "must be run as root"
fi

if (( $# != 8 )); then
    die "usage: fixture.sh DISK HOSTNAME WAN_MAC TESTNET_MAC TESTNET_CIDR TESTNET_NETWORK PRINTER_PORT SSH_PUBLIC_KEY"
fi

DISK="$1"
HOSTNAME="$2"
WAN_MAC="$3"
TESTNET_MAC="$4"
TESTNET_CIDR="$5"
TESTNET_NETWORK="$6"
PRINTER_PORT="$7"
SSH_PUBLIC_KEY="$8"

[[ -b "$DISK" ]] || die "'$DISK' is not a block device"
[[ -d /sys/firmware/efi/efivars ]] || die "system was not booted in UEFI mode"

if [[ "$DISK" =~ [0-9]$ ]]; then
    BOOT_PART="${DISK}p1"
    ROOT_PART="${DISK}p2"
else
    BOOT_PART="${DISK}1"
    ROOT_PART="${DISK}2"
fi

echo "Installing PHS network fixture"
echo "Disk:            $DISK"
echo "Hostname:        $HOSTNAME"
echo "Testnet address: $TESTNET_CIDR"
echo "NFS clients:     $TESTNET_NETWORK"
echo "IPP port:        $PRINTER_PORT"

timedatectl set-ntp true

umount -R /mnt 2>/dev/null || true
sgdisk --zap-all "$DISK"
sgdisk --new=1:0:+512M "$DISK"
sgdisk --new=2:0:0 "$DISK"
sgdisk --change-name=1:boot "$DISK"
sgdisk --change-name=2:root "$DISK"
sgdisk --typecode=1:ef00 "$DISK"
sgdisk --typecode=2:8300 "$DISK"
udevadm settle

for _ in {1..50}; do
    if [[ -b "$BOOT_PART" && -b "$ROOT_PART" ]]; then
        break
    fi
    sleep 0.1
done

[[ -b "$BOOT_PART" ]] || die "boot partition did not appear"
[[ -b "$ROOT_PART" ]] || die "root partition did not appear"

mkfs.fat -F32 "$BOOT_PART"
mkfs.ext4 -F "$ROOT_PART"
mount "$ROOT_PART" /mnt
mkdir -p /mnt/boot
mount "$BOOT_PART" /mnt/boot

pacstrap -K /mnt \
    base \
    linux \
    linux-firmware \
    openssh \
    nfs-utils \
    cups

genfstab -U /mnt > /mnt/etc/fstab

ln -sf /usr/share/zoneinfo/Europe/Berlin /mnt/etc/localtime
arch-chroot /mnt hwclock --systohc
printf '%s\n' 'en_US.UTF-8 UTF-8' > /mnt/etc/locale.gen
printf '%s\n' 'LANG=en_US.UTF-8' > /mnt/etc/locale.conf
arch-chroot /mnt locale-gen

printf '%s\n' "$HOSTNAME" > /mnt/etc/hostname
cat > /mnt/etc/hosts <<EOF
127.0.0.1 localhost
::1       localhost
127.0.1.1 $HOSTNAME
EOF

mkdir -p /mnt/etc/systemd/network
cat > /mnt/etc/systemd/network/10-wan.network <<EOF
[Match]
MACAddress=$WAN_MAC

[Network]
DHCP=yes
EOF

cat > /mnt/etc/systemd/network/20-testnet.network <<EOF
[Match]
MACAddress=$TESTNET_MAC

[Network]
Address=$TESTNET_CIDR
IPv6AcceptRA=no
LinkLocalAddressing=no
EOF

arch-chroot /mnt systemctl enable systemd-networkd.service
arch-chroot /mnt systemctl enable systemd-resolved.service
ln -sf /run/systemd/resolve/stub-resolv.conf /mnt/etc/resolv.conf

install -d -m 700 /mnt/root/.ssh
printf '%s\n' "$SSH_PUBLIC_KEY" > /mnt/root/.ssh/authorized_keys
chmod 600 /mnt/root/.ssh/authorized_keys
mkdir -p /mnt/etc/ssh/sshd_config.d
cat > /mnt/etc/ssh/sshd_config.d/10-phs-vm-test.conf <<'EOF'
PermitRootLogin prohibit-password
PasswordAuthentication no
KbdInteractiveAuthentication no
EOF
arch-chroot /mnt systemctl enable sshd.service

# NFS fixture
mkdir -p /mnt/srv/phs-test
chmod 0777 /mnt/srv/phs-test
cat > /mnt/etc/exports <<EOF
/srv/phs-test $TESTNET_NETWORK(rw,sync,no_subtree_check,no_root_squash)
EOF
arch-chroot /mnt systemctl enable nfs-server.service

# IPP Everywhere printer fixture. ippeveprinter is provided by cups.
mkdir -p /mnt/var/spool/phs-test-printer
cat > /mnt/etc/systemd/system/phs-test-printer.service <<EOF
[Unit]
Description=PHS IPP Everywhere test printer
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/ippeveprinter -p $PRINTER_PORT -r off -d /var/spool/phs-test-printer -k -f application/pdf,image/pwg-raster,image/urf,text/plain "PHS Test Printer"
Restart=on-failure
RestartSec=1

[Install]
WantedBy=multi-user.target
EOF
arch-chroot /mnt systemctl enable phs-test-printer.service

arch-chroot /mnt mkinitcpio -P
arch-chroot -S /mnt bootctl install

ROOT_PARTUUID="$(blkid -s PARTUUID -o value "$ROOT_PART")"
cat > /mnt/boot/loader/loader.conf <<'EOF'
default arch
timeout 1
editor 0
EOF
cat > /mnt/boot/loader/entries/arch.conf <<EOF
title   Arch Linux
linux   /vmlinuz-linux
initrd  /initramfs-linux.img
options root=PARTUUID=$ROOT_PARTUUID rw console=tty0 console=ttyS0,115200 loglevel=7
EOF


arch-chroot -S /mnt bootctl status


sync
umount -R /mnt

echo "Fixture installation complete"
