
> **Kategori:** ecc

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Ecc_Homelab Vlan Segmentation |
| **Nerede?** | ecc/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: homelab-vlan-segmentation
description: Segmenting home networks into VLANs for IoT, guest, trusted, and server traffic using UniFi, pfSense/OPNsense, and MikroTik — including switch trunk config, firewall rules, and wireless SSID mapping.
title: "Homelab Vlan Segmentation"
origin: community

audience: contributor
tags: [ai, automation, development]
category: ecc---

# Homelab Vlan Segmentation

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| Homelab VLAN Segmentation | `references/homelab-vlan-segmentation.md` |
| When to Use | `references/when-to-use.md` |
| How It Works | `references/how-it-works.md` |
| VLAN Design Template | `references/vlan-design-template.md` |
| Examples | `references/examples.md` |
| UniFi Configuration | `references/unifi-configuration.md` |
| All devices connecting to this SSID land in VLAN 20 | `references/all-devices-connecting-to-this-ssid-land-in-vlan-20.md` |
| Block IoT from reaching Trusted VLAN | `references/block-iot-from-reaching-trusted-vlan.md` |
| Allow IoT to reach internet only | `references/allow-iot-to-reach-internet-only.md` |
| Block Guest from all local networks | `references/block-guest-from-all-local-networks.md` |
| pfSense / OPNsense Configuration | `references/pfsense-opnsense-configuration.md` |
| Repeat for each VLAN, then assign each VLAN to an interface: | `references/repeat-for-each-vlan-then-assign-each-vlan-to-an-interface.md` |
| On the IoT interface (VLAN 20): | `references/on-the-iot-interface-vlan-20.md` |
| On the Trusted interface (VLAN 10): | `references/on-the-trusted-interface-vlan-10.md` |
| Additional exceptions for IoT devices that need specific local services: | `references/additional-exceptions-for-iot-devices-that-need-specific-loc.md` |
| MikroTik Configuration | `references/mikrotik-configuration.md` |
| Step 1: Create a bridge with VLAN filtering enabled | `references/step-1-create-a-bridge-with-vlan-filtering-enabled.md` |
| Trunk port to router/uplink (tagged for all VLANs) | `references/trunk-port-to-router-uplink-tagged-for-all-vlans.md` |
| Access port for trusted devices (untagged VLAN 10) | `references/access-port-for-trusted-devices-untagged-vlan-10.md` |
| Access port for IoT devices (untagged VLAN 20) | `references/access-port-for-iot-devices-untagged-vlan-20.md` |
| Step 3: Define which VLANs are allowed on which ports | `references/step-3-define-which-vlans-are-allowed-on-which-ports.md` |
| Step 4: Create VLAN interfaces on the bridge (gateway IPs) | `references/step-4-create-vlan-interfaces-on-the-bridge-gateway-ips.md` |
| Step 5: Assign gateway IPs | `references/step-5-assign-gateway-ips.md` |
| Step 6: DHCP pools and servers | `references/step-6-dhcp-pools-and-servers.md` |
| Step 7: Firewall — block IoT from reaching trusted VLAN | `references/step-7-firewall-block-iot-from-reaching-trusted-vlan.md` |
| Switch Trunk vs Access Ports | `references/switch-trunk-vs-access-ports.md` |
| A managed switch port connected to your router should be a trunk: | `references/a-managed-switch-port-connected-to-your-router-should-be-a-t.md` |
| A port connecting to a PC should be an access port: | `references/a-port-connecting-to-a-pc-should-be-an-access-port.md` |
| A port connecting to an AP must be a trunk: | `references/a-port-connecting-to-an-ap-must-be-a-trunk.md` |
| Anti-Patterns | `references/anti-patterns.md` |
| Anyone who learns the password can connect IoT devices to the wrong segment | `references/anyone-who-learns-the-password-can-connect-iot-devices-to-th.md` |
| Best Practices | `references/best-practices.md` |
| Related Skills | `references/related-skills.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
