#!/bin/bash

set -e

run_action() {
    case $1 in
    help) ## displays help
        fn=$(basename "$0")
        echo "## Available targets:"
        grep -E '\)\s*##' $fn | sed "s|^[[:space:]]*\(.*\)) #\{2\} \(.*\)|\1: \2|g"
    ;;

    run) ## runs test test scripts
        run_action setup
        run_action create-cloudiso
        run_action boot-with-installer
        run_action wait
        run_action install
        run_action shutdown
        run_action boot
        #run_action wait
        #run_action init
    ;;

    setup) ## removes old test env end inits the new one
        mkdir -p test/qemu/state
        rm -f \
            test/qemu/state/disk.raw \
            test/qemu/state/OVMF_VARS.4m.fd
        truncate -s 64G test/qemu/state/disk.raw
        cp \
            /usr/share/edk2/x64/OVMF_VARS.4m.fd \
            test/qemu/state/OVMF_VARS.4m.fd
    ;;

    boot) ## boots the qemu machine
        qemu-system-x86_64 \
            -name gaea-test \
            -machine q35,accel=kvm \
            -cpu host \
            -smp 4 \
            -m 4096 \
            -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/x64/OVMF_CODE.4m.fd \
            -drive if=pflash,format=raw,file=test/qemu/state/OVMF_VARS.4m.fd \
            -drive if=none,id=osdisk,format=raw,file=test/qemu/state/disk.raw \
            -device nvme,drive=osdisk,serial=gaea-test \
            -nic user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:2222-:22 \
            -monitor unix:test/qemu/state/monitor.sock,server=on,wait=off \
            -pidfile test/qemu/state/qemu.pid \
            -daemonize \
            "${@:2}"
    ;;

    boot-with-installer) ## boots the qemu machine with the archiso mounted
        run_action boot \
            -drive file=test/qemu/iso/archlinux-x86_64.iso,if=ide,index=2,media=cdrom,readonly=on,id=archiso \
            -drive file=test/qemu/iso/cloud-init.iso,if=ide,index=3,media=cdrom,readonly=on,id=cloudinit \
            -boot once=d
    ;;

    create-cloudiso) ## configures and creates the cloud iso for unattended installation (test only)
       run_action create-cloudiso-data
       run_action create-cloudiso-image
    ;;
    create-cloudiso-image) ## create the cloud iso
        xorriso \
            -as genisoimage \
            -output test/qemu/iso/cloud-init.iso \
            -volid CIDATA \
            -joliet \
            -rock \
            test/qemu/cloud-init/user-data \
            test/qemu/cloud-init/meta-data
    ;;

    create-cloudiso-data) ## configures the cloud iso
      PUBKEY="$(cat ~/.ssh/id_rsa.pub)"
      cat > test/qemu/cloud-init/user-data <<EOF
#cloud-config
disable_root: false
users:
    - name: root
      ssh_authorized_keys:
        - $PUBKEY
EOF
    ;;

    wait) ## wait for ssh to be available
        timeout=300
        start=$SECONDS

        until ssh \
            -p 2222 \
            -o BatchMode=yes \
            -o ConnectTimeout=1 \
            -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            root@127.0.0.1 \
            true \
            >/dev/null 2>&1
        do
            if (( SECONDS - start >= timeout )); then
                echo "ERROR: SSH did not become available within 5 minutes" >&2
                exit 1
            fi
            printf "."
            sleep 0.25
        done

        echo "SSH is available now"
    ;;

    install) ## runs the arch installation
        uv run phs --config-dir=./test/hostconfig  install --userpassword=test hojo
    ;;

    init)
        ./run.sh copy hojo
        #todo: run init script
    ;;

    shutdown) ## shuts down the machine via ssh
        ssh -p 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null 127.0.0.1 shutdown now
        sleep 2
    ;;

    *)
        run_action help
    ;;
    esac
}

run_action "$@"
