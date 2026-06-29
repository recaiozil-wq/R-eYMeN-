
> **Kategori:** devops

---

## 📋 5N1K

| Soru | Cevap |
|:-----|:------|
| **Kim?** | Tüm ajanlar |
| **Ne?** | Devops_Virtualbox |
| **Nerede?** | devops/ |
| **Ne Zaman?** | İhtiyaç duyulduğunda |
| **Neden?** | Otomatik kategorilendirme |
| **Nasıl?** | Skill referansı ile |

---

---

name: virtualbox
description: Manage VirtualBox VMs from Windows host via Hermes. Use for VM status, start/stop, networking, and remote access.
title: "Virtualbox"
triggers:
  - virtualbox
  - vboxmanage
  - kali linux vm
  - vm management
  - ssh to vm
  - connect to vm

audience: maintainer
tags: [automation, devops, system]
category: devops---

# Virtualbox

Bu skill modüler bir yönlendiricidir. İhtiyacınız olan bölümü seçin ve ilgili reference dosyasını yükleyin.

## 📂 Bölümler

| Bölüm | Reference Dosyası |
|-------|------------------|
| When to Use | `references/when-to-use.md` |
| Quick Paths | `references/quick-paths.md` |
| Read VMState= line | `references/read-vmstate-line.md` |
| Headless (no window): | `references/headless-no-window.md` |
| GUI (windowed): | `references/gui-windowed.md` |
| List host-only adapters | `references/list-host-only-adapters.md` |
| Check VM NICs | `references/check-vm-nics.md` |
| Pitfalls | `references/pitfalls.md` |
| WRONG — gets truncated or merged | `references/wrong-gets-truncated-or-merged.md` |
| RIGHT — separate calls with sleep | `references/right-separate-calls-with-sleep.md` |
| Type a command and press Enter | `references/type-a-command-and-press-enter.md` |
| Chain multiple commands with delays | `references/chain-multiple-commands-with-delays.md` |
| Ctrl+Alt+T (open terminal on Kali/GNOME) | `references/ctrl-alt-t-open-terminal-on-kali-gnome.md` |
| Alt+F4 (close active window) | `references/alt-f4-close-active-window.md` |
| Ctrl+Alt+F1 (switch to TTY1) | `references/ctrl-alt-f1-switch-to-tty1.md` |
| Clear screen first | `references/clear-screen-first.md` |
| Echo a separator | `references/echo-a-separator.md` |
| Run a scan command | `references/run-a-scan-command.md` |
| Wait for nmap to finish (adjust based on subnet size) | `references/wait-for-nmap-to-finish-adjust-based-on-subnet-size.md` |
| Kali'de hangi terminal var? | `references/kali-de-hangi-terminal-var.md` |
| Kali'de qterminal başlat (GUI) | `references/kali-de-qterminal-ba-lat-gui.md` |
| Alternatif: x-terminal-emulator (sembolik link) | `references/alternatif-x-terminal-emulator-sembolik-link.md` |
| Çıktı: kali | `references/kt-kali.md` |
| Çıktı: kal | `references/kt-kal.md` |
| Python ile güvenilir yol dönüşümü | `references/python-ile-g-venilir-yol-d-n-m.md` |
| GUI uygulaması başlat (start) | `references/gui-uygulamas-ba-lat-start.md` |
| Komut çalıştır + çıktı al (run) | `references/komut-al-t-r-kt-al-run.md` |
| Kullanıcı Çalışma Stili (ÖNEMLİ) | `references/kullan-c-al-ma-stili-nemli.md` |
| Find by USB VID/PID | `references/find-by-usb-vid-pid.md` |
| Find by network class | `references/find-by-network-class.md` |
| Check filter exists | `references/check-filter-exists.md` |
| Check attachment in boot log (after VM started) | `references/check-attachment-in-boot-log-after-vm-started.md` |
| Recommended Workflow | `references/recommended-workflow.md` |
| Scripts | `references/scripts.md` |
| References | `references/references.md` |

## Kullanım

1. İhtiyacın olan bölümü belirle
2. `skill_view(name="...", file_path="references/...")` ile yükle
