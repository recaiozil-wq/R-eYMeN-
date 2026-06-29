
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Homelab Wireguard Vpn |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: homelab-wireguard-vpn
description: WireGuard VPN server setup, peer configuration, key generation, split tunneling vs full tunnel routing, and remote access to a home network from mobile and laptop clients.
title: "Homelab Wireguard VPN"
origin: community

audience: contributor
tags: [ai, automation, development, vpn]
category: ecc---

# Homelab Wireguard Vpn

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Homelab WireGuard VPN | `references/homelab-wireguard-vpn.md` |
| When to Use | `references/when-to-use.md` |
| How WireGuard Works | `references/how-wireguard-works.md` |
| Server Setup (Linux) | `references/server-setup-linux.md` |
| Install WireGuard | `references/install-wireguard.md` |
| Generate server keypair — create files with private permissions from the start | `references/generate-server-keypair-create-files-with-private-permission.md` |
| Do not store private keys in version control or share them | `references/do-not-store-private-keys-in-version-control-or-share-them.md` |
| Scoped forwarding rules: allow VPN traffic in/out, not a blanket FORWARD ACCEPT | `references/scoped-forwarding-rules-allow-vpn-traffic-in-out-not-a-blank.md` |
| Phone — replace with the actual phone public key | `references/phone-replace-with-the-actual-phone-public-key.md` |
| Laptop — replace with the actual laptop public key | `references/laptop-replace-with-the-actual-laptop-public-key.md` |
| Enable IP forwarding (required for routing traffic through the server) | `references/enable-ip-forwarding-required-for-routing-traffic-through-th.md` |
| Start WireGuard and enable on boot | `references/start-wireguard-and-enable-on-boot.md` |
| Client Configuration | `references/client-configuration.md` |
| Run on the client, or on the server and transfer the private key securely — never in plaintext | `references/run-on-the-client-or-on-the-server-and-transfer-the-private-.md` |
| Client config file (phone_wg0.conf): | `references/client-config-file-phone_wg0-conf.md` |
| AllowedIPs = 0.0.0.0/0, ::/0        Full tunnel: all traffic through VPN | `references/allowedips-0-0-0-0-0-0-full-tunnel-all-traffic-through-vpn.md` |
| Split Tunnel vs Full Tunnel | `references/split-tunnel-vs-full-tunnel.md` |
| Split tunnel: AllowedIPs = 192.168.1.0/24 | `references/split-tunnel-allowedips-192-168-1-0-24.md` |
| Full tunnel: AllowedIPs = 0.0.0.0/0, ::/0 | `references/full-tunnel-allowedips-0-0-0-0-0-0.md` |
| Multi-subnet split tunnel (most common homelab use case): | `references/multi-subnet-split-tunnel-most-common-homelab-use-case.md` |
| Key Generation and Peer Management | `references/key-generation-and-peer-management.md` |
| pfSense / OPNsense WireGuard | `references/pfsense-opnsense-wireguard.md` |
| pfSense: VPN → WireGuard → Add Tunnel | `references/pfsense-vpn-wireguard-add-tunnel.md` |
| Add Peer (one per client): | `references/add-peer-one-per-client.md` |
| Assign the WireGuard interface: | `references/assign-the-wireguard-interface.md` |
| Firewall rules: | `references/firewall-rules.md` |
| DDNS (Dynamic DNS) for Home Servers | `references/ddns-dynamic-dns-for-home-servers.md` |
| docker-compose entry using an env file: | `references/docker-compose-entry-using-an-env-file.md` |
| Option 2: DuckDNS (free, simple) | `references/option-2-duckdns-free-simple.md` |
| /usr/local/bin/update-duckdns | `references/usr-local-bin-update-duckdns.md` |
| Cron job: | `references/cron-job.md` |
| Troubleshooting | `references/troubleshooting.md` |
| Check WireGuard status and last handshake | `references/check-wireguard-status-and-last-handshake.md` |
| 1. Is UDP port 51820 open on the router/firewall? | `references/1-is-udp-port-51820-open-on-the-router-firewall.md` |
| 2. Is the server public key in the client config correct? | `references/2-is-the-server-public-key-in-the-client-config-correct.md` |
| 3. Is IP forwarding enabled on the server? | `references/3-is-ip-forwarding-enabled-on-the-server.md` |
| Check kernel logs for WireGuard errors | `references/check-kernel-logs-for-wireguard-errors.md` |
| Restart WireGuard | `references/restart-wireguard.md` |
| Anti-Patterns | `references/anti-patterns.md` |
| Scope forwarding rules to the wg0 interface and direction only | `references/scope-forwarding-rules-to-the-wg0-interface-and-direction-on.md` |
| Best Practices | `references/best-practices.md` |
| Related Skills | `references/related-skills.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
