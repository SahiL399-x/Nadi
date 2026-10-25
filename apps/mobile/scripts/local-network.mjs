import os from 'node:os';
import fs from 'node:fs';
import path from 'node:path';

const privateIpv4 = /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[0-1])\.)/;
// Adapters that carry a private IP but are NOT the LAN the phones are on.
// `vethernet` catches Hyper-V's "vEthernet (Default Switch)" / "vEthernet (WSL …)".
const virtualAdapter =
  /(docker|vethernet|veth|vmware|virtualbox|wsl|hyper-v|loopback|bluetooth|tailscale|zerotier|vpn|tap|tun|npcap)/i;
// Prefer the real Wi-Fi adapter when several physical candidates survive the filter.
const wirelessAdapter = /(wi-?fi|wlan|wireless)/i;

export function getLocalNetworkIp() {
  const candidates = [];

  for (const [name, addresses] of Object.entries(os.networkInterfaces())) {
    if (virtualAdapter.test(name)) continue;

    for (const address of addresses ?? []) {
      if (address.family === 'IPv4' && !address.internal && privateIpv4.test(address.address)) {
        candidates.push({ name, address: address.address });
      }
    }
  }

  if (candidates.length === 0) {
    throw new Error('Could not find an active private IPv4 address. Connect to Wi-Fi or Ethernet and try again.');
  }

  // Deterministic choice: a Wi-Fi adapter wins over anything else; otherwise the
  // first survivor (OS enumeration order) — rather than trusting that order blindly.
  const wifi = candidates.find((c) => wirelessAdapter.test(c.name));
  return (wifi ?? candidates[0]).address;
}

export function apiUrl() {
  return `http://${getLocalNetworkIp()}:8000`;
}

export function updateLocalEnv(url) {
  const envPath = path.join(process.cwd(), '.env');
  let contents = fs.existsSync(envPath) ? fs.readFileSync(envPath, 'utf8') : '';
  const line = `EXPO_PUBLIC_API_URL=${url}`;

  if (/^EXPO_PUBLIC_API_URL=.*$/m.test(contents)) {
    contents = contents.replace(/^EXPO_PUBLIC_API_URL=.*$/m, line);
  } else {
    contents = `${contents.replace(/\s*$/, '')}\n${line}\n`;
  }

  fs.writeFileSync(envPath, contents);
}
